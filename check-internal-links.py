#!/usr/bin/env python3
"""Check internal anchor link integrity for the live DevToolbox site."""

from __future__ import annotations

import argparse
import http.client
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, Iterable, List, Tuple
from urllib.parse import urlparse


class AnchorParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        for key, value in attrs:
            if key.lower() == "href" and value:
                self.links.append(value)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check internal anchor links for 4xx/5xx responses.")
    parser.add_argument("--site-root", default="/var/www/web-ceo", help="Static site root to scan.")
    parser.add_argument("--base-url", default="http://localhost", help="Base URL to probe.")
    parser.add_argument("--timeout", type=float, default=5.0, help="HTTP timeout in seconds.")
    parser.add_argument("--max-items", type=int, default=20, help="Max report rows.")
    parser.add_argument("--json", help="Write JSON report to this path.")
    return parser.parse_args()


def iter_html_files(site_root: Path) -> Iterable[Path]:
    return sorted(site_root.rglob("*.html"))


def file_to_route(site_root: Path, file_path: Path) -> str:
    rel = file_path.relative_to(site_root)
    rel_str = rel.as_posix()
    if rel_str == "index.html":
        return "/"
    if rel.name == "index.html":
        prefix = rel.parent.as_posix().strip("/")
        return f"/{prefix}/"
    return f"/{rel_str[:-5]}"


def normalize_internal_path(raw_href: str) -> str | None:
    href = raw_href.strip()
    if not href or href.startswith("#"):
        return None

    lowered = href.lower()
    if lowered.startswith(("http://", "https://", "//", "mailto:", "tel:", "javascript:", "data:")):
        return None

    parsed = urlparse(href)
    path = parsed.path or "/"
    if not path.startswith("/"):
        return None

    path = re.sub(r"/{2,}", "/", path)
    if not path:
        return "/"
    return path


def probe_path(
    *,
    scheme: str,
    host: str,
    port: int,
    path: str,
    timeout: float,
) -> Tuple[int, str]:
    conn_cls = http.client.HTTPSConnection if scheme == "https" else http.client.HTTPConnection
    last_error = ""

    for method in ("HEAD", "GET"):
        conn = conn_cls(host, port, timeout=timeout)
        try:
            conn.request(method, path, headers={"User-Agent": "DevToolboxLinkChecker/1.0"})
            resp = conn.getresponse()
            status = int(resp.status)
            location = resp.getheader("Location") or ""
            if method == "GET":
                resp.read(1024)
            else:
                resp.read(0)
            if method == "HEAD" and status in (405, 501):
                continue
            return status, location
        except Exception as exc:
            last_error = str(exc)
        finally:
            conn.close()

    return 0, last_error


def main() -> int:
    args = parse_args()
    site_root = Path(args.site_root).resolve()
    if not site_root.exists():
        print(f"site root not found: {site_root}", file=sys.stderr)
        return 1

    parsed_base = urlparse(args.base_url)
    if parsed_base.scheme not in {"http", "https"} or not parsed_base.hostname:
        print(f"invalid base URL: {args.base_url}", file=sys.stderr)
        return 1

    scheme = parsed_base.scheme
    host = parsed_base.hostname
    port = parsed_base.port or (443 if scheme == "https" else 80)

    link_counts: Counter[str] = Counter()
    link_sources: Dict[str, List[str]] = defaultdict(list)
    scanned_files = 0
    scanned_links = 0

    for html_file in iter_html_files(site_root):
        scanned_files += 1
        parser = AnchorParser()
        try:
            parser.feed(html_file.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            continue
        source_route = file_to_route(site_root, html_file)
        for href in parser.links:
            normalized = normalize_internal_path(href)
            if not normalized:
                continue
            scanned_links += 1
            link_counts[normalized] += 1
            if len(link_sources[normalized]) < 8 and source_route not in link_sources[normalized]:
                link_sources[normalized].append(source_route)

    results: Dict[str, Dict[str, str | int]] = {}
    for path in sorted(link_counts):
        status, location_or_error = probe_path(
            scheme=scheme,
            host=host,
            port=port,
            path=path,
            timeout=max(0.2, float(args.timeout)),
        )
        results[path] = {
            "status": status,
            "location_or_error": location_or_error,
        }

    broken_targets: List[dict] = []
    redirect_targets: List[dict] = []
    ok_target_count = 0

    for path, count in link_counts.items():
        status = int(results[path]["status"])  # type: ignore[arg-type]
        location_or_error = str(results[path]["location_or_error"])
        item = {
            "path": path,
            "status": status,
            "count": int(count),
            "sources": link_sources[path],
        }
        if status == 0 or status >= 400:
            item["error"] = location_or_error
            broken_targets.append(item)
        elif 300 <= status < 400:
            item["location"] = location_or_error
            redirect_targets.append(item)
        else:
            ok_target_count += 1

    broken_targets.sort(key=lambda x: (-x["count"], x["path"]))  # type: ignore[index]
    redirect_targets.sort(key=lambda x: (-x["count"], x["path"]))  # type: ignore[index]

    broken_link_instances = sum(int(x["count"]) for x in broken_targets)
    redirect_link_instances = sum(int(x["count"]) for x in redirect_targets)
    unique_targets = len(link_counts)
    broken_target_count = len(broken_targets)
    redirect_target_count = len(redirect_targets)
    broken_ratio = 0.0
    if scanned_links > 0:
        broken_ratio = round((broken_link_instances / scanned_links) * 100, 4)

    report = {
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "site_root": str(site_root),
        "base_url": args.base_url,
        "scanned_html_files": scanned_files,
        "scanned_internal_link_instances": scanned_links,
        "unique_internal_targets": unique_targets,
        "ok_target_count": ok_target_count,
        "redirect_target_count": redirect_target_count,
        "broken_target_count": broken_target_count,
        "broken_link_instances": broken_link_instances,
        "redirect_link_instances": redirect_link_instances,
        "broken_link_ratio_pct": broken_ratio,
        "top_broken_targets": broken_targets[: max(1, int(args.max_items))],
        "top_redirect_targets": redirect_targets[: max(1, int(args.max_items))],
    }

    if args.json:
        Path(args.json).write_text(json.dumps(report, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")

    print(f"scanned_html_files: {scanned_files}")
    print(f"scanned_internal_link_instances: {scanned_links}")
    print(f"unique_internal_targets: {unique_targets}")
    print(f"broken_target_count: {broken_target_count}")
    print(f"broken_link_instances: {broken_link_instances}")
    print(f"broken_link_ratio_pct: {broken_ratio}")

    if broken_targets:
        print("top_broken_targets:")
        for item in broken_targets[: max(1, int(args.max_items))]:
            print(f"  {item['count']}  {item['status']}  {item['path']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
