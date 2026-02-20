#!/usr/bin/env python3
"""Generate sitemap.xml for DevToolbox.

Goal: keep <lastmod> accurate without marking every URL as "today".

- Blog posts: prefer <meta property="article:published_time"> or JSON-LD dateModified.
- Tools/Cheatsheets/other pages: use file mtime (UTC date).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


SITE_ROOT = Path("/var/www/web-ceo")
BASE_URL = "https://devtoolbox.dedyn.io"
REQUIRED_ROOT_FILES = ("google5ab7b13e25381f31.html",)
DATEKIT_ROOT = Path("/var/www/datekit")
BUDGETKIT_ROOT = SITE_ROOT / "budgetkit"


@dataclass(frozen=True)
class SitemapEntry:
    loc: str
    lastmod: str
    changefreq: str
    priority: str


def utc_mtime_date(path: Path) -> str:
    ts = path.stat().st_mtime
    return datetime.fromtimestamp(ts, tz=UTC).date().isoformat()


_PUBLISHED_RE = re.compile(
    r'<meta\s+property="article:published_time"\s+content="(\d{4}-\d{2}-\d{2})"\s*/?>'
)
_MODIFIED_RE = re.compile(r'"dateModified"\s*:\s*"(\d{4}-\d{2}-\d{2})"')


def blog_lastmod(path: Path) -> str:
    """Return YYYY-MM-DD for a blog post."""
    try:
        html = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return utc_mtime_date(path)

    published = None
    modified = None

    published_match = _PUBLISHED_RE.search(html)
    if published_match:
        published = published_match.group(1)

    modified_match = _MODIFIED_RE.search(html)
    if modified_match:
        modified = modified_match.group(1)

    candidates = [d for d in (published, modified) if d]
    if candidates:
        return max(candidates)

    return utc_mtime_date(path)


def write_sitemap(entries: list[SitemapEntry], output_path: Path) -> None:
    lines: list[str] = [
        "<?xml version='1.0' encoding='utf-8'?>",
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]

    for entry in entries:
        lines.append(
            "  <url>"
            f"<loc>{entry.loc}</loc>"
            f"<lastmod>{entry.lastmod}</lastmod>"
            f"<changefreq>{entry.changefreq}</changefreq>"
            f"<priority>{entry.priority}</priority>"
            "</url>"
        )

    lines.append("</urlset>")
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def add_subsite_pages(
    entries: list[SitemapEntry],
    mount_path: str,
    source_dir: Path,
    root_priority: str = "0.8",
    page_priority: str = "0.7",
) -> None:
    if not source_dir.exists():
        return

    pages = sorted(source_dir.glob("*.html"), key=lambda p: p.name)
    for page in pages:
        if page.name == "index.html":
            loc_path = f"{mount_path}/"
            priority = root_priority
        else:
            loc_path = f"{mount_path}/{page.name}"
            priority = page_priority

        entries.append(
            SitemapEntry(
                loc=f"{BASE_URL}{loc_path}",
                lastmod=utc_mtime_date(page),
                changefreq="weekly",
                priority=priority,
            )
        )


def main() -> None:
    missing = [name for name in REQUIRED_ROOT_FILES if not (SITE_ROOT / name).exists()]
    if missing:
        names = ", ".join(missing)
        raise FileNotFoundError(
            f"Required root file(s) missing: {names}. Restore before publishing."
        )

    entries: list[SitemapEntry] = []

    def add(loc_path: str, file_path: Path, changefreq: str, priority: str) -> None:
        entries.append(
            SitemapEntry(
                loc=f"{BASE_URL}{loc_path}",
                lastmod=utc_mtime_date(file_path),
                changefreq=changefreq,
                priority=priority,
            )
        )

    add("/", SITE_ROOT / "index.html", "daily", "1.0")
    add("/about", SITE_ROOT / "about.html", "monthly", "0.6")
    add("/api", SITE_ROOT / "api.html", "monthly", "0.6")
    add("/changelog", SITE_ROOT / "changelog.html", "weekly", "0.6")
    add("/blog", SITE_ROOT / "blog" / "index.html", "weekly", "0.9")
    add("/tools", SITE_ROOT / "tools" / "index.html", "weekly", "0.8")
    add("/cheatsheets", SITE_ROOT / "cheatsheets" / "index.html", "weekly", "0.8")
    add_subsite_pages(entries, "/datekit", DATEKIT_ROOT)
    add_subsite_pages(entries, "/budgetkit", BUDGETKIT_ROOT)

    tools_dir = SITE_ROOT / "tools"
    tool_pages = sorted(
        [p for p in tools_dir.glob("*.html") if p.name != "index.html"],
        key=lambda p: p.name,
    )
    for page in tool_pages:
        entries.append(
            SitemapEntry(
                loc=f"{BASE_URL}/tools/{page.stem}",
                lastmod=utc_mtime_date(page),
                changefreq="monthly",
                priority="0.5",
            )
        )

    cheats_dir = SITE_ROOT / "cheatsheets"
    cheatsheet_pages = sorted(
        [p for p in cheats_dir.glob("*.html") if p.name != "index.html"],
        key=lambda p: p.name,
    )
    for page in cheatsheet_pages:
        entries.append(
            SitemapEntry(
                loc=f"{BASE_URL}/cheatsheets/{page.stem}",
                lastmod=utc_mtime_date(page),
                changefreq="monthly",
                priority="0.5",
            )
        )

    blog_dir = SITE_ROOT / "blog"
    blog_pages = sorted(
        [p for p in blog_dir.glob("*.html") if p.name != "index.html"],
        key=lambda p: p.name,
    )
    for page in blog_pages:
        entries.append(
            SitemapEntry(
                loc=f"{BASE_URL}/blog/{page.stem}",
                lastmod=blog_lastmod(page),
                changefreq="monthly",
                priority="0.6",
            )
        )

    feed_path = SITE_ROOT / "feed.xml"
    entries.append(
        SitemapEntry(
            loc=f"{BASE_URL}/feed.xml",
            lastmod=utc_mtime_date(feed_path),
            changefreq="daily",
            priority="0.4",
        )
    )

    write_sitemap(entries, SITE_ROOT / "sitemap.xml")
    print(f"Wrote {SITE_ROOT / 'sitemap.xml'} with {len(entries)} URLs")


if __name__ == "__main__":
    main()
