#!/usr/bin/env python3
"""Inject cross-property promotion blocks into top blog pages."""

import argparse
import json
import os
import re
import subprocess
import tempfile
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ANALYZE_TRAFFIC_SCRIPT = os.path.join(BASE_DIR, "analyze_traffic.py")
BLOG_DIR = "/var/www/web-ceo/blog"
PROMO_MARKER = 'data-crossproperty-promo="true"'
PROMO_VERSION = "4"
PROMO_VERSION_MARKER = f'data-crossproperty-promo-version="{PROMO_VERSION}"'
PROMO_CAMPAIGN = "crosspromo-top-organic"
PROMO_BLOCK_PATTERN = re.compile(
    r'<aside class="crossproperty-promo"[^>]*data-crossproperty-promo="true"[^>]*>.*?</aside>\s*',
    re.DOTALL,
)
PROMO_PRIMARY_TARGET = ("focuskit", "FocusKit deep-work calculators")
PROMO_SECONDARY_TARGETS = (
    ("datekit", "DateKit"),
    ("budgetkit", "BudgetKit"),
    ("healthkit", "HealthKit"),
    ("sleepkit", "SleepKit"),
    ("opskit", "OpsKit"),
    ("studykit", "StudyKit"),
)


def parse_args():
    parser = argparse.ArgumentParser(description="Inject cross-property promotion blocks into top blog pages.")
    parser.add_argument("--hours", type=int, default=24, help="Lookback window for traffic ranking (default: 24)")
    parser.add_argument("--max-items", type=int, default=120, help="Max rows pulled from analytics report (default: 120)")
    parser.add_argument("--top", type=int, default=20, help="How many top blog pages to update (default: 20)")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing files")
    return parser.parse_args()


def load_traffic_report(hours: int, max_items: int) -> dict:
    with tempfile.NamedTemporaryFile("w+", suffix=".json", delete=True) as tmp:
        subprocess.check_call(
            [
                "python3",
                ANALYZE_TRAFFIC_SCRIPT,
                "--hours",
                str(hours),
                "--max-items",
                str(max_items),
                "--json",
                tmp.name,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        tmp.seek(0)
        return json.load(tmp)


def score_blog_paths(report: dict) -> list[str]:
    scores: dict[str, int] = defaultdict(int)

    for item in report.get("top_pages", []):
        path = item.get("path", "")
        count = int(item.get("count", 0))
        if path.startswith("/blog/"):
            scores[path] += count

    for item in report.get("top_organic_pages", []):
        path = item.get("path", "")
        count = int(item.get("count", 0))
        if path.startswith("/blog/"):
            scores[path] += count * 2

    return [path for path, _ in sorted(scores.items(), key=lambda x: x[1], reverse=True)]


def slug_from_blog_path(path: str) -> str:
    slug = path.removeprefix("/blog/").strip("/")
    return slug


def build_promo_html(slug: str) -> str:
    params = f"utm_source=devtoolbox&utm_medium=internal&utm_campaign={PROMO_CAMPAIGN}&utm_content={slug}"
    primary_target, primary_label = PROMO_PRIMARY_TARGET
    secondary_links = ", ".join(
        f'<a href="/{target}/?{params}" style="color: #bfdbfe; text-decoration: underline;">{label}</a>'
        for target, label in PROMO_SECONDARY_TARGETS
    )
    return (
        "\n"
        f'        <aside class="crossproperty-promo" {PROMO_MARKER} '
        f'{PROMO_VERSION_MARKER} '
        'style="margin: 1.25rem 0 1.5rem; padding: 1rem 1.1rem; border: 1px solid rgba(59,130,246,0.35); '
        'border-radius: 10px; background: rgba(59,130,246,0.08); line-height: 1.65;">\n'
        '            <strong style="color: #bfdbfe;">Plan execution before writing code:</strong>\n'
        f'            <p style="margin: 0.45rem 0 0;"><a href="/{primary_target}/?{params}" '
        'style="display: inline-block; color: #0f172a; text-decoration: none; background: #93c5fd; '
        'padding: 0.28rem 0.55rem; border-radius: 6px; font-weight: 700;">'
        f'{primary_label}</a> for focus sessions, time blocks, and meeting load checks.</p>\n'
        f'            <p style="margin: 0.45rem 0 0; color: #dbeafe;">Need other planning calculators for life, ops, or study workflows? {secondary_links}. '
        f'<a href="/kits/?{params}" style="color: #bfdbfe; text-decoration: underline; font-weight: 600;">All Kits</a>.</p>\n'
        "        </aside>\n"
    )


def upgrade_existing_promo_block(content: str, slug: str) -> str:
    match = PROMO_BLOCK_PATTERN.search(content)
    if not match:
        return content
    block = match.group(0)
    if PROMO_VERSION_MARKER in block:
        return content
    return content[: match.start()] + build_promo_html(slug) + content[match.end() :]


def find_insert_pos(content: str) -> int:
    main_pos = content.find("<main")
    if main_pos == -1:
        return -1

    h1_pos = content.find("<h1", main_pos)
    if h1_pos == -1:
        return -1

    h1_end = content.find("</h1>", h1_pos)
    if h1_end == -1:
        return -1

    search_pos = h1_end
    p_found = 0
    while p_found < 2:
        p_end = content.find("</p>", search_pos)
        if p_end == -1:
            break
        search_pos = p_end + len("</p>")
        p_found += 1

    if p_found == 0:
        return -1
    return search_pos


def patch_blog_file(path: str, dry_run: bool) -> str:
    slug = slug_from_blog_path(path)
    if not slug:
        return "skip:invalid-slug"

    file_path = os.path.join(BLOG_DIR, f"{slug}.html")
    if not os.path.exists(file_path):
        return "skip:not-found"

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError:
        return "skip:read-error"

    if PROMO_MARKER in content:
        upgraded = upgrade_existing_promo_block(content, slug)
        if upgraded == content:
            return "skip:already-patched"
        if not dry_run:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(upgraded)
            except OSError:
                return "skip:write-error"
        return "updated:upgraded-existing"

    has_campaign = f"utm_campaign={PROMO_CAMPAIGN}" in content
    has_all_campaign_targets = all(
        f"/{target}/?utm_source=devtoolbox&utm_medium=internal&utm_campaign={PROMO_CAMPAIGN}" in content
        for target, _ in (PROMO_PRIMARY_TARGET, *PROMO_SECONDARY_TARGETS)
    )
    if has_campaign and has_all_campaign_targets:
        return "skip:campaign-exists"

    insert_pos = find_insert_pos(content)
    if insert_pos == -1:
        return "skip:no-insert-point"

    updated = content[:insert_pos] + build_promo_html(slug) + content[insert_pos:]
    if not dry_run:
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(updated)
        except OSError:
            return "skip:write-error"
    if has_campaign:
        return "updated:campaign-upgrade"
    return "updated:new"


def main():
    args = parse_args()
    report = load_traffic_report(max(1, args.hours), max(10, args.max_items))
    candidates = score_blog_paths(report)[: max(1, args.top)]

    if not candidates:
        print("No candidate blog paths found.")
        return

    counts: dict[str, int] = defaultdict(int)
    for path in candidates:
        result = patch_blog_file(path, args.dry_run)
        counts[result] += 1
        print(f"{result:>22}  {path}")

    print("\nSummary:")
    for key in sorted(counts):
        print(f"  {key}: {counts[key]}")


if __name__ == "__main__":
    main()
