#!/usr/bin/env python3
"""Inject FocusKit discovery blocks into high-traffic hub pages."""

import argparse
import re
from pathlib import Path

SITE_ROOT = Path("/var/www/web-ceo")
MARKER = 'data-focuskit-discovery="true"'
BLOCK_PATTERN = re.compile(
    r"\n?\s*<section class=\"focuskit-discovery\" data-focuskit-discovery=\"true\"[^>]*>.*?</section>\s*",
    re.DOTALL,
)

HOME_ANCHOR_PATTERN = re.compile(r"(<section class=\"hero\">.*?</section>)", re.DOTALL)
H1_ANCHOR_PATTERN = re.compile(r"(<h1>.*?</h1>)", re.DOTALL)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inject FocusKit discovery blocks into hub pages.")
    parser.add_argument("--dry-run", action="store_true", help="Show planned changes without writing files")
    return parser.parse_args()


def build_block(heading: str, description: str) -> str:
    return (
        "\n"
        f'        <section class="focuskit-discovery" {MARKER} '
        'style="margin: 1.1rem 0 1.5rem; padding: 1rem 1.1rem; border: 1px solid rgba(59,130,246,0.35); '
        'border-radius: 10px; background: rgba(59,130,246,0.07); line-height: 1.6;">\n'
        f"            <h2 style=\"margin: 0 0 0.45rem; font-size: 1.1rem;\">{heading}</h2>\n"
        f"            <p style=\"margin: 0 0 0.55rem;\">{description}</p>\n"
        "            <ul style=\"margin: 0; padding-left: 1.1rem;\">\n"
        "                <li><a href=\"/focuskit/\">FocusKit productivity calculators</a></li>\n"
        "                <li><a href=\"/focuskit/focus-session-calculator.html\">Focus Session Calculator</a></li>\n"
        "                <li><a href=\"/focuskit/time-block-calculator.html\">Time Block Calculator</a></li>\n"
        "                <li><a href=\"/focuskit/meeting-load-calculator.html\">Meeting Load Calculator</a></li>\n"
        "            </ul>\n"
        "        </section>\n"
    )


TARGETS = (
    {
        "name": "home",
        "file": SITE_ROOT / "index.html",
        "anchor": HOME_ANCHOR_PATTERN,
        "block": build_block(
            "New: FocusKit for execution planning",
            "Before coding, map your focus windows, task blocks, and meeting load with fast calculators.",
        ),
    },
    {
        "name": "blog-index",
        "file": SITE_ROOT / "blog" / "index.html",
        "anchor": H1_ANCHOR_PATTERN,
        "block": build_block(
            "Planning sprint execution?",
            "Use FocusKit to turn tutorial ideas into realistic work blocks before implementation.",
        ),
    },
    {
        "name": "tools-index",
        "file": SITE_ROOT / "tools" / "index.html",
        "anchor": H1_ANCHOR_PATTERN,
        "block": build_block(
            "Pair your tools with focus planning",
            "Use FocusKit calculators to estimate timeline risk and preserve deep-work capacity.",
        ),
    },
    {
        "name": "cheatsheets-index",
        "file": SITE_ROOT / "cheatsheets" / "index.html",
        "anchor": H1_ANCHOR_PATTERN,
        "block": build_block(
            "From reference to execution",
            "After reviewing a cheat sheet, use FocusKit to plan a realistic focused implementation session.",
        ),
    },
)


def upsert_block(content: str, block: str, anchor_pattern: re.Pattern[str]) -> tuple[str, str]:
    if MARKER in content:
        replaced = BLOCK_PATTERN.sub(block, content, count=1)
        if replaced == content:
            return content, "skip:marker-found-no-match"
        return replaced, "updated:replaced"

    anchor_match = anchor_pattern.search(content)
    if not anchor_match:
        return content, "skip:no-anchor"

    insert_at = anchor_match.end()
    updated = content[:insert_at] + block + content[insert_at:]
    return updated, "updated:inserted"


def patch_target(target: dict, dry_run: bool) -> str:
    path: Path = target["file"]
    if not path.exists():
        return "skip:not-found"

    content = path.read_text(encoding="utf-8")
    updated, status = upsert_block(content, target["block"], target["anchor"])
    if updated == content:
        return status

    if not dry_run:
        path.write_text(updated, encoding="utf-8")
    return status


def main() -> None:
    args = parse_args()
    counts: dict[str, int] = {}

    for target in TARGETS:
        status = patch_target(target, args.dry_run)
        counts[status] = counts.get(status, 0) + 1
        print(f"{status:>26}  {target['name']}  {target['file']}")

    print("\nSummary:")
    for key in sorted(counts):
        print(f"  {key}: {counts[key]}")


if __name__ == "__main__":
    main()
