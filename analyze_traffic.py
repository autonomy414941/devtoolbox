#!/usr/bin/env python3
import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone

LOG_FILES = ["/var/log/nginx/web-ceo.access.log", "/var/log/nginx/web-ceo.access.log.1"]
LOG_PATTERN = re.compile(
    r'^(?P<ip>\S+) \S+ \S+ \[(?P<ts>[^\]]+)\] "(?P<req>[^"]*)" (?P<status>\d{3}) \S+ "(?P<ref>[^"]*)" "(?P<ua>[^"]*)"'
)
ASSET_PATTERN = re.compile(
    r"\.(css|js|mjs|ico|png|jpg|jpeg|gif|svg|webp|avif|woff|woff2|ttf|eot|map|txt|xml)$",
    re.IGNORECASE,
)
INTERNAL_REFERRER_PATTERN = re.compile(r"^https?://(www\.)?devtoolbox\.dedyn\.io/?", re.IGNORECASE)
ENGINE_PATTERNS = [
    (re.compile(r"google\.", re.IGNORECASE), "google"),
    (re.compile(r"bing\.", re.IGNORECASE), "bing"),
    (re.compile(r"duckduckgo\.", re.IGNORECASE), "duckduckgo"),
    (re.compile(r"yahoo\.", re.IGNORECASE), "yahoo"),
    (re.compile(r"ecosia\.", re.IGNORECASE), "ecosia"),
    (re.compile(r"qwant\.", re.IGNORECASE), "qwant"),
    (re.compile(r"aol\.", re.IGNORECASE), "aol"),
    (re.compile(r"search\.brave\.com", re.IGNORECASE), "brave"),
    (re.compile(r"yandex\.", re.IGNORECASE), "yandex"),
]
SUSPICIOUS_PATH_PATTERNS = [
    re.compile(r"^/(?:wp-admin(?:/|$)|wp-login\.php$|xmlrpc\.php$)", re.IGNORECASE),
    re.compile(r"/vendor/phpunit/", re.IGNORECASE),
    re.compile(r"^/(?:phpunit|lib/phpunit)/", re.IGNORECASE),
    re.compile(r"\.(?:php(?:\d+)?|phtml|phar)$", re.IGNORECASE),
    re.compile(r"/\.env(?:[._-][^/]*)?$", re.IGNORECASE),
    re.compile(r"^/wp-config", re.IGNORECASE),
    re.compile(
        r"(?:^|/)(?:phpinfo|phpsysinfo|php-info|php[_-]?details?|phpinformation|infophp|testphp(?:info)?|pinfo|php\.ini)(?:$|[/.])",
        re.IGNORECASE,
    ),
    re.compile(r"^/\.(?!well-known/)", re.IGNORECASE),
    re.compile(r"^/(?:wp-config\.php|web\.config|configuration\.php|config\.json|secrets\.json|credentials\.json)$", re.IGNORECASE),
    re.compile(r"^/(?:public/hot|public/storage|containers/json|storage/\*\.key)$", re.IGNORECASE),
    re.compile(r"^/(?:bin/sh|hello\.world|manager/html|shell|version|v1)$", re.IGNORECASE),
    re.compile(r"^/(?:boaform/|actuator/|geoserver/web/|developmentserver/metadatauploader)", re.IGNORECASE),
    re.compile(r"^/(?:\.emacs\.desktop(?:\.lock)?|eshell/(?:lastdir|history)|elpa/|auto/)$", re.IGNORECASE),
    re.compile(r"^/(?:webui/|admin(?:/config\.php)?$|login$|aaa9$|aab9$)", re.IGNORECASE),
    re.compile(r"^/(?:backup|dump|database)\.sql$", re.IGNORECASE),
    re.compile(r"^/(?:phpinfo\.php|composer\.json|docker-compose\.yml|bitbucket-pipelines\.yml)$", re.IGNORECASE),
    re.compile(r"^/wp-config\.php(?:\.(?:bak|old|save|orig))?$", re.IGNORECASE),
    re.compile(r"^/(?:var/log/|usr/bin/|path/to/|bins/)", re.IGNORECASE),
    re.compile(r"%7c_", re.IGNORECASE),
    re.compile(r"\|_", re.IGNORECASE),
    re.compile(r"/\.git/config$", re.IGNORECASE),
    re.compile(r"^/gponform/diag_form$", re.IGNORECASE),
]


def read_log_lines(path: str):
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.readlines()
    except PermissionError:
        output = subprocess.check_output(["sudo", "-n", "cat", path], text=True, stderr=subprocess.DEVNULL)
        return output.splitlines(keepends=True)


def parse_request_path(request: str) -> str:
    parts = request.split()
    if len(parts) < 2:
        return ""
    path = parts[1].split("?", 1)[0].strip()
    return path or "/"


def is_asset_path(path: str) -> bool:
    if not path:
        return True
    if path in {"/favicon.ico", "/robots.txt", "/sitemap.xml", "/feed.xml", "/sw.js"}:
        return True
    if path.startswith("/assets/") or path.startswith("/static/"):
        return True
    return bool(ASSET_PATTERN.search(path))


def detect_engine(referrer: str) -> str:
    for pattern, name in ENGINE_PATTERNS:
        if pattern.search(referrer):
            return name
    return ""


def is_suspicious_path(path: str) -> bool:
    if not path:
        return False
    for pattern in SUSPICIOUS_PATH_PATTERNS:
        if pattern.search(path):
            return True
    return False


def counter_to_sorted_list(counter: Counter, key_name: str):
    return [{key_name: key, "count": count} for key, count in counter.most_common()]


def parse_args():
    parser = argparse.ArgumentParser(description="Analyze web-ceo nginx access logs.")
    parser.add_argument("--hours", type=int, default=24, help="Rolling time window in hours (default: 24)")
    parser.add_argument("--max-items", type=int, default=20, help="Max rows per printed section (default: 20)")
    parser.add_argument("--json", type=str, default="", help="Write JSON output to this file")
    return parser.parse_args()


def main():
    args = parse_args()
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=max(1, args.hours))

    total_requests = 0
    clean_requests = 0
    content_requests = 0
    suspicious_requests = 0
    unique_ips = set()
    clean_unique_ips = set()
    content_unique_ips = set()
    suspicious_unique_ips = set()
    status_counts = Counter()
    page_counts = Counter()
    organic_engine_counts = Counter()
    organic_page_counts = Counter()
    external_referrers = Counter()
    not_found_pages = Counter()
    clean_not_found_pages = Counter()
    suspicious_paths = Counter()
    suspicious_not_found_pages = Counter()

    for logfile in LOG_FILES:
        try:
            lines = read_log_lines(logfile)
        except Exception as exc:
            print(f"Error reading {logfile}: {exc}", file=sys.stderr)
            continue

        for line in lines:
            match = LOG_PATTERN.match(line)
            if not match:
                continue

            try:
                ts = datetime.strptime(match.group("ts"), "%d/%b/%Y:%H:%M:%S %z").astimezone(timezone.utc)
            except ValueError:
                continue

            if ts < cutoff:
                continue

            ip = match.group("ip")
            status = match.group("status")
            referrer = match.group("ref").strip()
            path = parse_request_path(match.group("req"))
            asset = is_asset_path(path)
            suspicious_path = is_suspicious_path(path)

            total_requests += 1
            unique_ips.add(ip)
            status_counts[status] += 1
            if suspicious_path:
                suspicious_requests += 1
                suspicious_unique_ips.add(ip)
                if path:
                    suspicious_paths[path] += 1
            else:
                clean_requests += 1
                clean_unique_ips.add(ip)
                if not asset and path:
                    content_requests += 1
                    content_unique_ips.add(ip)

            if not asset and path:
                page_counts[path] += 1
                if status == "404":
                    not_found_pages[path] += 1
                    if suspicious_path:
                        suspicious_not_found_pages[path] += 1
                    else:
                        clean_not_found_pages[path] += 1

            if referrer and referrer != "-":
                if not INTERNAL_REFERRER_PATTERN.match(referrer):
                    external_referrers[referrer] += 1
                engine = detect_engine(referrer)
                if engine and not asset and path:
                    organic_engine_counts[engine] += 1
                    organic_page_counts[path] += 1

    organic_total = sum(organic_engine_counts.values())
    summary = {
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window_hours": max(1, args.hours),
        "total_requests": total_requests,
        "unique_ips": len(unique_ips),
        "clean_requests": clean_requests,
        "clean_unique_ips": len(clean_unique_ips),
        "content_requests": content_requests,
        "content_unique_ips": len(content_unique_ips),
        "suspicious_requests": suspicious_requests,
        "suspicious_unique_ips": len(suspicious_unique_ips),
        "suspicious_404": sum(suspicious_not_found_pages.values()),
        "clean_404": sum(clean_not_found_pages.values()),
        "organic_referrals": organic_total,
    }

    print(f"=== TRAFFIC SUMMARY (last {summary['window_hours']}h) ===")
    print(f"  total_requests: {summary['total_requests']}")
    print(f"  unique_ips: {summary['unique_ips']}")
    print(f"  clean_requests: {summary['clean_requests']}")
    print(f"  clean_unique_ips: {summary['clean_unique_ips']}")
    print(f"  content_requests: {summary['content_requests']}")
    print(f"  content_unique_ips: {summary['content_unique_ips']}")
    print(f"  suspicious_requests: {summary['suspicious_requests']}")
    print(f"  suspicious_404: {summary['suspicious_404']}")
    print(f"  organic_referrals: {summary['organic_referrals']}")
    print()

    print("=== STATUS CODES ===")
    for code, count in status_counts.most_common(args.max_items):
        print(f"  {code}: {count}")
    print()

    print("=== TOP PAGES (non-asset) ===")
    for path, count in page_counts.most_common(args.max_items):
        print(f"  {count:4d}  {path}")
    print()

    print("=== ORGANIC ENGINES ===")
    for engine, count in organic_engine_counts.most_common(args.max_items):
        print(f"  {engine}: {count}")
    print()

    print("=== TOP ORGANIC LANDING PAGES ===")
    for path, count in organic_page_counts.most_common(args.max_items):
        print(f"  {count:4d}  {path}")
    print()

    print("=== TOP EXTERNAL REFERRERS ===")
    for referrer, count in external_referrers.most_common(args.max_items):
        print(f"  {count:4d}  {referrer}")
    print()

    print("=== TOP 404 PAGES ===")
    for path, count in not_found_pages.most_common(args.max_items):
        print(f"  {count:4d}  {path}")
    print()

    print("=== TOP CLEAN 404 PAGES ===")
    for path, count in clean_not_found_pages.most_common(args.max_items):
        print(f"  {count:4d}  {path}")
    print()

    print("=== TOP SUSPICIOUS PATHS ===")
    for path, count in suspicious_paths.most_common(args.max_items):
        print(f"  {count:4d}  {path}")

    report = {
        "summary": summary,
        "status_codes": counter_to_sorted_list(status_counts, "code"),
        "top_pages": counter_to_sorted_list(page_counts, "path"),
        "organic_engines": counter_to_sorted_list(organic_engine_counts, "engine"),
        "top_organic_pages": counter_to_sorted_list(organic_page_counts, "path"),
        "top_external_referrers": counter_to_sorted_list(external_referrers, "referrer"),
        "top_404_pages": counter_to_sorted_list(not_found_pages, "path"),
        "top_clean_404_pages": counter_to_sorted_list(clean_not_found_pages, "path"),
        "top_suspicious_paths": counter_to_sorted_list(suspicious_paths, "path"),
    }

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            f.write("\n")


if __name__ == "__main__":
    main()
