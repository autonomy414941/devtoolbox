#!/usr/bin/env python3
import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs

LOG_FILES = ["/var/log/nginx/web-ceo.access.log", "/var/log/nginx/web-ceo.access.log.1"]
LOG_PATTERN = re.compile(
    r'^(?P<ip>\S+) \S+ \S+ \[(?P<ts>[^\]]+)\] "(?P<req>[^"]*)" (?P<status>\d{3}) \S+ "(?P<ref>[^"]*)" "(?P<ua>[^"]*)"'
)
ASSET_PATTERN = re.compile(
    r"\.(css|js|mjs|ico|png|jpg|jpeg|gif|svg|webp|avif|woff|woff2|ttf|eot|map|txt|xml)$",
    re.IGNORECASE,
)
EXACT_ASSET_PATHS = {
    "/favicon.ico",
    "/robots.txt",
    "/sitemap.xml",
    "/feed.xml",
    "/sw.js",
    "/manifest.json",
    "/site.webmanifest",
}
INTERNAL_REFERRER_PATTERN = re.compile(r"^https?://(www\.)?devtoolbox\.dedyn\.io/?", re.IGNORECASE)
CONTENT_SECTION_NAMES = ("homepage", "blog", "tools", "cheatsheets", "datekit", "budgetkit", "other")
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


def parse_request_path_query(request: str):
    parts = request.split()
    if len(parts) < 2:
        return "", ""
    target = parts[1].strip()
    path, _, query = target.partition("?")
    return (path or "/"), query


def is_asset_path(path: str) -> bool:
    if not path:
        return True
    if path in EXACT_ASSET_PATHS:
        return True
    if path.startswith("/assets/") or path.startswith("/static/"):
        return True
    return bool(ASSET_PATTERN.search(path))


def classify_content_section(path: str) -> str:
    if path == "/":
        return "homepage"
    if path == "/blog" or path.startswith("/blog/"):
        return "blog"
    if path == "/tools" or path.startswith("/tools/"):
        return "tools"
    if path == "/cheatsheets" or path.startswith("/cheatsheets/"):
        return "cheatsheets"
    if path == "/datekit" or path.startswith("/datekit/"):
        return "datekit"
    if path == "/budgetkit" or path.startswith("/budgetkit/"):
        return "budgetkit"
    return "other"


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


def counter_to_sorted_list(counter: Counter, key_name: str, max_items: int | None = None):
    if max_items is None or max_items < 0:
        items = counter.most_common()
    else:
        items = counter.most_common(max_items)
    return [{key_name: key, "count": count} for key, count in items]


def safe_ratio(part: int, whole: int) -> float:
    if whole <= 0:
        return 0.0
    return round((part / whole) * 100, 2)


def safe_pct_change(current: int, previous: int):
    if previous <= 0:
        return None
    return round(((current - previous) / previous) * 100, 2)


class WindowStats:
    def __init__(self):
        self.total_requests = 0
        self.clean_requests = 0
        self.content_requests = 0
        self.suspicious_requests = 0
        self.unique_ips = set()
        self.clean_unique_ips = set()
        self.content_unique_ips = set()
        self.suspicious_unique_ips = set()
        self.status_counts = Counter()
        self.page_counts = Counter()
        self.content_section_counts = Counter()
        self.organic_engine_counts = Counter()
        self.organic_page_counts = Counter()
        self.organic_section_counts = Counter()
        self.external_referrers = Counter()
        self.not_found_pages = Counter()
        self.clean_not_found_pages = Counter()
        self.suspicious_paths = Counter()
        self.suspicious_not_found_pages = Counter()
        self.crosspromo_campaign_hits = 0
        self.crosspromo_campaign_pages = Counter()
        self.crosspromo_campaign_sources = Counter()

    def record(self, ip: str, status: str, referrer: str, path: str, query: str):
        asset = is_asset_path(path)
        suspicious_path = is_suspicious_path(path)

        self.total_requests += 1
        self.unique_ips.add(ip)
        self.status_counts[status] += 1

        if suspicious_path:
            self.suspicious_requests += 1
            self.suspicious_unique_ips.add(ip)
            if path:
                self.suspicious_paths[path] += 1
        else:
            self.clean_requests += 1
            self.clean_unique_ips.add(ip)
            if not asset and path:
                self.content_requests += 1
                self.content_unique_ips.add(ip)
                section = classify_content_section(path)
                self.content_section_counts[section] += 1

        if not asset and path:
            self.page_counts[path] += 1
            if status == "404":
                self.not_found_pages[path] += 1
                if suspicious_path:
                    self.suspicious_not_found_pages[path] += 1
                else:
                    self.clean_not_found_pages[path] += 1
            if "utm_campaign=crosspromo-top-organic" in query:
                self.crosspromo_campaign_hits += 1
                self.crosspromo_campaign_pages[path] += 1
                params = parse_qs(query, keep_blank_values=False)
                for source in params.get("utm_content", []):
                    if source:
                        self.crosspromo_campaign_sources[source] += 1

        if referrer and referrer != "-":
            if not INTERNAL_REFERRER_PATTERN.match(referrer):
                self.external_referrers[referrer] += 1
            engine = detect_engine(referrer)
            if engine and not asset and path and not suspicious_path:
                self.organic_engine_counts[engine] += 1
                self.organic_page_counts[path] += 1
                section = classify_content_section(path)
                self.organic_section_counts[section] += 1

    def summary(self, generated_at: str, window_hours: int):
        organic_total = sum(self.organic_engine_counts.values())
        not_found_total = sum(self.not_found_pages.values())
        clean_404 = sum(self.clean_not_found_pages.values())
        suspicious_404 = sum(self.suspicious_not_found_pages.values())
        content_sections = {name: int(self.content_section_counts.get(name, 0)) for name in CONTENT_SECTION_NAMES}
        organic_sections = {name: int(self.organic_section_counts.get(name, 0)) for name in CONTENT_SECTION_NAMES}
        content_section_share = {name: safe_ratio(content_sections[name], self.content_requests) for name in CONTENT_SECTION_NAMES}
        organic_section_share = {name: safe_ratio(organic_sections[name], organic_total) for name in CONTENT_SECTION_NAMES}

        top_content_section = "other"
        top_content_section_requests = 0
        top_organic_section = "other"
        top_organic_section_referrals = 0
        if content_sections:
            top_content_section, top_content_section_requests = max(content_sections.items(), key=lambda item: item[1])
        if organic_sections:
            top_organic_section, top_organic_section_referrals = max(organic_sections.items(), key=lambda item: item[1])

        summary = {
            "generated_at": generated_at,
            "window_hours": window_hours,
            "total_requests": self.total_requests,
            "unique_ips": len(self.unique_ips),
            "clean_requests": self.clean_requests,
            "clean_unique_ips": len(self.clean_unique_ips),
            "content_requests": self.content_requests,
            "content_unique_ips": len(self.content_unique_ips),
            "suspicious_requests": self.suspicious_requests,
            "suspicious_unique_ips": len(self.suspicious_unique_ips),
            "not_found_requests": not_found_total,
            "suspicious_404": suspicious_404,
            "clean_404": clean_404,
            "organic_referrals": organic_total,
            "crosspromo_campaign_hits": self.crosspromo_campaign_hits,
            "clean_request_ratio": safe_ratio(self.clean_requests, self.total_requests),
            "content_request_ratio": safe_ratio(self.content_requests, self.total_requests),
            "suspicious_request_ratio": safe_ratio(self.suspicious_requests, self.total_requests),
            "organic_referral_ratio": safe_ratio(organic_total, self.total_requests),
            "not_found_ratio": safe_ratio(not_found_total, self.total_requests),
            "clean_404_ratio": safe_ratio(clean_404, not_found_total),
            "suspicious_404_ratio": safe_ratio(suspicious_404, not_found_total),
            "content_sections": content_sections,
            "organic_sections": organic_sections,
            "content_section_share_pct": content_section_share,
            "organic_section_share_pct": organic_section_share,
            "top_content_section": top_content_section,
            "top_content_section_requests": top_content_section_requests,
            "top_organic_section": top_organic_section,
            "top_organic_section_referrals": top_organic_section_referrals,
        }
        for section_name in CONTENT_SECTION_NAMES:
            summary[f"content_{section_name}_requests"] = content_sections[section_name]
            summary[f"organic_{section_name}_referrals"] = organic_sections[section_name]
        return summary


def build_window_comparison(
    current_summary: dict,
    previous_summary: dict,
    current_start: datetime,
    current_end: datetime,
    previous_start: datetime,
):
    metrics = [
        "total_requests",
        "unique_ips",
        "clean_requests",
        "content_requests",
        "suspicious_requests",
        "not_found_requests",
        "clean_404",
        "suspicious_404",
        "organic_referrals",
        "crosspromo_campaign_hits",
        "content_homepage_requests",
        "content_blog_requests",
        "content_tools_requests",
        "content_cheatsheets_requests",
        "content_datekit_requests",
        "content_budgetkit_requests",
        "content_other_requests",
        "organic_homepage_referrals",
        "organic_blog_referrals",
        "organic_tools_referrals",
        "organic_cheatsheets_referrals",
        "organic_datekit_referrals",
        "organic_budgetkit_referrals",
        "organic_other_referrals",
    ]
    deltas = {}
    for metric in metrics:
        current_value = int(current_summary.get(metric, 0))
        previous_value = int(previous_summary.get(metric, 0))
        deltas[metric] = current_value - previous_value
        deltas[f"{metric}_pct"] = safe_pct_change(current_value, previous_value)

    return {
        "current_window": {
            "start": current_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end": current_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "hours": int(current_summary.get("window_hours", 0)),
        },
        "previous_window": {
            "start": previous_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end": current_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "hours": int(previous_summary.get("window_hours", 0)),
            "summary": previous_summary,
        },
        "deltas": deltas,
    }


def parse_args():
    parser = argparse.ArgumentParser(description="Analyze web-ceo nginx access logs.")
    parser.add_argument("--hours", type=int, default=24, help="Rolling time window in hours (default: 24)")
    parser.add_argument("--max-items", type=int, default=20, help="Max rows per printed section (default: 20)")
    parser.add_argument(
        "--compare-previous",
        action="store_true",
        help="Compare current window with the previous window of the same duration",
    )
    parser.add_argument("--json", type=str, default="", help="Write JSON output to this file")
    return parser.parse_args()


def main():
    args = parse_args()
    now = datetime.now(timezone.utc)
    window_hours = max(1, args.hours)
    current_start = now - timedelta(hours=window_hours)
    previous_start = current_start - timedelta(hours=window_hours)

    current_window = WindowStats()
    previous_window = WindowStats() if args.compare_previous else None

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

            if args.compare_previous:
                if ts < previous_start:
                    continue
                target_window = current_window if ts >= current_start else previous_window
            else:
                if ts < current_start:
                    continue
                target_window = current_window

            if target_window is None:
                continue

            ip = match.group("ip")
            status = match.group("status")
            referrer = match.group("ref").strip()
            path, query = parse_request_path_query(match.group("req"))
            target_window.record(ip, status, referrer, path, query)

    generated_at = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    summary = current_window.summary(generated_at, window_hours)
    comparison = None
    if args.compare_previous and previous_window is not None:
        previous_summary = previous_window.summary(current_start.strftime("%Y-%m-%dT%H:%M:%SZ"), window_hours)
        comparison = build_window_comparison(summary, previous_summary, current_start, now, previous_start)

    print(f"=== TRAFFIC SUMMARY (last {summary['window_hours']}h) ===")
    print(f"  total_requests: {summary['total_requests']}")
    print(f"  unique_ips: {summary['unique_ips']}")
    print(f"  clean_requests: {summary['clean_requests']}")
    print(f"  clean_unique_ips: {summary['clean_unique_ips']}")
    print(f"  content_requests: {summary['content_requests']}")
    print(f"  content_unique_ips: {summary['content_unique_ips']}")
    print(f"  suspicious_requests: {summary['suspicious_requests']}")
    print(f"  not_found_requests: {summary['not_found_requests']}")
    print(f"  suspicious_404: {summary['suspicious_404']}")
    print(f"  organic_referrals: {summary['organic_referrals']}")
    print(f"  crosspromo_campaign_hits: {summary['crosspromo_campaign_hits']}")
    print(f"  clean_request_ratio: {summary['clean_request_ratio']}%")
    print(f"  suspicious_request_ratio: {summary['suspicious_request_ratio']}%")
    print(f"  organic_referral_ratio: {summary['organic_referral_ratio']}%")
    print()

    print("=== CONTENT SECTION BREAKDOWN (clean, non-asset) ===")
    for section_name in CONTENT_SECTION_NAMES:
        section_count = summary.get(f"content_{section_name}_requests", 0)
        section_share = summary.get("content_section_share_pct", {}).get(section_name, 0)
        print(f"  {section_name}: {section_count} ({section_share}%)")
    print()

    print("=== ORGANIC SECTION BREAKDOWN ===")
    for section_name in CONTENT_SECTION_NAMES:
        section_count = summary.get(f"organic_{section_name}_referrals", 0)
        section_share = summary.get("organic_section_share_pct", {}).get(section_name, 0)
        print(f"  {section_name}: {section_count} ({section_share}%)")
    print()

    if comparison:
        print("=== WINDOW COMPARISON (current vs previous same-duration window) ===")
        for metric in [
            "total_requests",
            "unique_ips",
            "content_requests",
            "content_blog_requests",
            "content_tools_requests",
            "content_cheatsheets_requests",
            "content_datekit_requests",
            "content_budgetkit_requests",
            "suspicious_requests",
            "not_found_requests",
            "organic_referrals",
            "organic_blog_referrals",
            "organic_tools_referrals",
            "organic_cheatsheets_referrals",
            "organic_datekit_referrals",
            "organic_budgetkit_referrals",
            "crosspromo_campaign_hits",
        ]:
            delta = comparison["deltas"][metric]
            delta_pct = comparison["deltas"][f"{metric}_pct"]
            delta_pct_label = "n/a" if delta_pct is None else f"{delta_pct:+.2f}%"
            print(f"  {metric}: {delta:+d} ({delta_pct_label})")
        print()

    print("=== STATUS CODES ===")
    for code, count in current_window.status_counts.most_common(args.max_items):
        print(f"  {code}: {count}")
    print()

    print("=== TOP PAGES (non-asset) ===")
    for path, count in current_window.page_counts.most_common(args.max_items):
        print(f"  {count:4d}  {path}")
    print()

    print("=== ORGANIC ENGINES ===")
    for engine, count in current_window.organic_engine_counts.most_common(args.max_items):
        print(f"  {engine}: {count}")
    print()

    print("=== TOP ORGANIC LANDING PAGES ===")
    for path, count in current_window.organic_page_counts.most_common(args.max_items):
        print(f"  {count:4d}  {path}")
    print()

    print("=== TOP EXTERNAL REFERRERS ===")
    for referrer, count in current_window.external_referrers.most_common(args.max_items):
        print(f"  {count:4d}  {referrer}")
    print()

    print("=== CROSSPROMO CAMPAIGN LANDINGS ===")
    for path, count in current_window.crosspromo_campaign_pages.most_common(args.max_items):
        print(f"  {count:4d}  {path}")
    print()

    print("=== CROSSPROMO CAMPAIGN SOURCES ===")
    for source, count in current_window.crosspromo_campaign_sources.most_common(args.max_items):
        print(f"  {count:4d}  {source}")
    print()

    print("=== TOP 404 PAGES ===")
    for path, count in current_window.not_found_pages.most_common(args.max_items):
        print(f"  {count:4d}  {path}")
    print()

    print("=== TOP CLEAN 404 PAGES ===")
    for path, count in current_window.clean_not_found_pages.most_common(args.max_items):
        print(f"  {count:4d}  {path}")
    print()

    print("=== TOP SUSPICIOUS PATHS ===")
    for path, count in current_window.suspicious_paths.most_common(args.max_items):
        print(f"  {count:4d}  {path}")

    report = {
        "summary": summary,
        "status_codes": counter_to_sorted_list(current_window.status_counts, "code", args.max_items),
        "content_sections": counter_to_sorted_list(current_window.content_section_counts, "section", args.max_items),
        "organic_sections": counter_to_sorted_list(current_window.organic_section_counts, "section", args.max_items),
        "top_pages": counter_to_sorted_list(current_window.page_counts, "path", args.max_items),
        "organic_engines": counter_to_sorted_list(current_window.organic_engine_counts, "engine", args.max_items),
        "top_organic_pages": counter_to_sorted_list(current_window.organic_page_counts, "path", args.max_items),
        "top_external_referrers": counter_to_sorted_list(current_window.external_referrers, "referrer", args.max_items),
        "crosspromo_campaign_pages": counter_to_sorted_list(current_window.crosspromo_campaign_pages, "path", args.max_items),
        "crosspromo_campaign_sources": counter_to_sorted_list(current_window.crosspromo_campaign_sources, "source", args.max_items),
        "top_404_pages": counter_to_sorted_list(current_window.not_found_pages, "path", args.max_items),
        "top_clean_404_pages": counter_to_sorted_list(current_window.clean_not_found_pages, "path", args.max_items),
        "top_suspicious_paths": counter_to_sorted_list(current_window.suspicious_paths, "path", args.max_items),
    }
    if comparison:
        report["comparison"] = comparison

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            f.write("\n")


if __name__ == "__main__":
    main()
