#!/usr/bin/env python3
"""Generate index.html for the DevToolbox repository."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import html
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUTPUT_PATH = ROOT / "index.html"
SKIP_FILES = {"index.html", "google5ab7b13e25381f31.html"}

TITLE_RE = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)
DESCRIPTION_RE = re.compile(
    r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']\s*/?>',
    re.IGNORECASE | re.DOTALL,
)


@dataclass(frozen=True)
class Page:
    filename: str
    title: str
    description: str
    category: str


def cleanup_text(value: str) -> str:
    text = html.unescape(value)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_metadata(html_text: str, fallback_title: str) -> tuple[str, str]:
    title_match = TITLE_RE.search(html_text)
    description_match = DESCRIPTION_RE.search(html_text)

    raw_title = title_match.group(1) if title_match else fallback_title
    raw_description = (
        description_match.group(1)
        if description_match
        else "Practical developer resource from DevToolbox."
    )

    title = cleanup_text(raw_title)
    title = title.split("|")[0].strip()
    description = cleanup_text(raw_description)
    return title, description


def guess_category(filename: str) -> str:
    lower = filename.lower()
    if any(token in lower for token in ("formatter", "query-builder", "timer")):
        return "Tools"
    if any(token in lower for token in ("cheatsheet", "commands")):
        return "Cheat Sheets"
    return "Guides"


def load_pages() -> list[Page]:
    pages: list[Page] = []
    for html_file in sorted(ROOT.glob("*.html")):
        if html_file.name in SKIP_FILES:
            continue
        text = html_file.read_text(encoding="utf-8", errors="replace")
        fallback = html_file.stem.replace("-", " ").title()
        title, description = extract_metadata(text, fallback_title=fallback)
        pages.append(
            Page(
                filename=html_file.name,
                title=title,
                description=description,
                category=guess_category(html_file.name),
            )
        )
    return pages


def render_card(page: Page) -> str:
    safe_title = html.escape(page.title)
    safe_description = html.escape(page.description)
    safe_filename = html.escape(page.filename)
    search_blob = html.escape(
        f"{page.title} {page.description} {page.filename} {page.category}".lower()
    )
    return (
        f'<a class="resource-card" href="{safe_filename}" data-search="{search_blob}">'
        f'<span class="resource-type">{html.escape(page.category)}</span>'
        f"<h3>{safe_title}</h3>"
        f"<p>{safe_description}</p>"
        f'<code>{safe_filename}</code>'
        "</a>"
    )


def render_section(title: str, pages: list[Page]) -> str:
    cards = "\n".join(render_card(page) for page in pages)
    section_id = title.lower().replace(" ", "-")
    return (
        f'<section class="resource-section" data-section="{section_id}">'
        f'<div class="section-header"><h2>{html.escape(title)}</h2>'
        f'<span class="section-count">{len(pages)} items</span></div>'
        f'<div class="grid">{cards}</div>'
        "</section>"
    )


def render_index(pages: list[Page]) -> str:
    groups = {"Tools": [], "Cheat Sheets": [], "Guides": []}
    for page in pages:
        groups[page.category].append(page)

    for category_pages in groups.values():
        category_pages.sort(key=lambda p: p.title.lower())

    section_html = "\n".join(
        render_section(category, groups[category])
        for category in ("Tools", "Cheat Sheets", "Guides")
        if groups[category]
    )

    generated_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    total_count = len(pages)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DevToolbox - Practical Developer Tools, Guides, and Cheat Sheets</title>
    <meta name="description" content="Collection of practical developer tools, implementation guides, and cheat sheets. Fast to scan, actionable in production.">
    <meta property="og:title" content="DevToolbox">
    <meta property="og:description" content="Practical developer tools, guides, and cheat sheets.">
    <meta property="og:type" content="website">
    <meta name="twitter:card" content="summary">
    <meta name="theme-color" content="#0f172a">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-0: #0b1021;
            --bg-1: #151b35;
            --ink: #f5f7ff;
            --muted: #b8c2e6;
            --card: rgba(14, 20, 41, 0.72);
            --line: rgba(255, 255, 255, 0.12);
            --accent: #50e3c2;
            --accent-2: #ffd166;
            --shadow: 0 16px 40px rgba(0, 0, 0, 0.25);
        }}
        * {{
            box-sizing: border-box;
        }}
        body {{
            margin: 0;
            min-height: 100vh;
            color: var(--ink);
            background:
                radial-gradient(circle at 15% 15%, rgba(80, 227, 194, 0.24), transparent 32%),
                radial-gradient(circle at 85% 0%, rgba(255, 209, 102, 0.18), transparent 30%),
                linear-gradient(160deg, var(--bg-0), var(--bg-1));
            font-family: "Space Grotesk", "Segoe UI", sans-serif;
            line-height: 1.5;
        }}
        .shell {{
            max-width: 1100px;
            margin: 0 auto;
            padding: 32px 20px 56px;
        }}
        .hero {{
            border: 1px solid var(--line);
            background: linear-gradient(135deg, rgba(20, 28, 57, 0.92), rgba(10, 15, 35, 0.92));
            border-radius: 18px;
            box-shadow: var(--shadow);
            padding: 28px;
            margin-bottom: 20px;
        }}
        .hero h1 {{
            margin: 0 0 10px;
            font-size: clamp(2rem, 4vw, 2.8rem);
            letter-spacing: -0.02em;
        }}
        .hero p {{
            margin: 0;
            max-width: 70ch;
            color: var(--muted);
        }}
        .stats {{
            margin-top: 14px;
            font-family: "IBM Plex Mono", monospace;
            color: #dbe4ff;
            font-size: 0.92rem;
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
        }}
        .toolbar {{
            margin: 22px 0 18px;
        }}
        .toolbar input {{
            width: 100%;
            border: 1px solid var(--line);
            background: var(--card);
            color: var(--ink);
            border-radius: 12px;
            font: inherit;
            padding: 14px 16px;
            font-size: 1rem;
        }}
        .toolbar input:focus {{
            outline: 2px solid var(--accent);
            outline-offset: 2px;
        }}
        .resource-section {{
            margin-top: 20px;
        }}
        .section-header {{
            display: flex;
            justify-content: space-between;
            gap: 12px;
            align-items: baseline;
            margin: 0 2px 10px;
        }}
        .section-header h2 {{
            margin: 0;
            font-size: 1.32rem;
        }}
        .section-count {{
            color: var(--muted);
            font-size: 0.9rem;
            font-family: "IBM Plex Mono", monospace;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 14px;
        }}
        .resource-card {{
            display: block;
            border: 1px solid var(--line);
            border-radius: 14px;
            padding: 14px;
            background: var(--card);
            text-decoration: none;
            color: inherit;
            transition: transform 140ms ease, border-color 140ms ease, background-color 140ms ease;
        }}
        .resource-card:hover {{
            transform: translateY(-2px);
            border-color: rgba(80, 227, 194, 0.6);
            background: rgba(19, 28, 56, 0.88);
        }}
        .resource-card h3 {{
            margin: 8px 0;
            font-size: 1.02rem;
            line-height: 1.4;
        }}
        .resource-card p {{
            margin: 0 0 10px;
            color: var(--muted);
            font-size: 0.92rem;
        }}
        .resource-card code {{
            display: inline-block;
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 3px 7px;
            font-family: "IBM Plex Mono", monospace;
            font-size: 0.8rem;
            color: #dae6ff;
        }}
        .resource-type {{
            display: inline-block;
            font-family: "IBM Plex Mono", monospace;
            font-size: 0.76rem;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: #061225;
            background: linear-gradient(130deg, var(--accent), var(--accent-2));
            padding: 3px 7px;
            border-radius: 999px;
        }}
        .hidden {{
            display: none !important;
        }}
        footer {{
            margin-top: 30px;
            color: var(--muted);
            font-size: 0.86rem;
            text-align: center;
        }}
        @media (max-width: 640px) {{
            .hero {{
                padding: 22px;
            }}
            .stats {{
                gap: 8px;
            }}
        }}
    </style>
</head>
<body>
    <main class="shell">
        <header class="hero">
            <h1>DevToolbox</h1>
            <p>Direct, production-focused references for developers. Browse tools, cheat sheets, and deep guides without noise.</p>
            <div class="stats">
                <span>{total_count} resources indexed</span>
                <span>Generated from repo metadata</span>
                <span>{generated_at}</span>
            </div>
        </header>
        <div class="toolbar">
            <label for="search" class="hidden">Search resources</label>
            <input id="search" type="search" placeholder="Search by topic, stack, or filename...">
        </div>
        {section_html}
        <footer>Maintained in <code>autonomy414941/devtoolbox</code> · Run <code>./generate-index.py</code> after adding new pages.</footer>
    </main>
    <script>
        const searchInput = document.getElementById("search");
        const cards = Array.from(document.querySelectorAll(".resource-card"));
        const sections = Array.from(document.querySelectorAll(".resource-section"));

        function applyFilter() {{
            const term = searchInput.value.trim().toLowerCase();
            cards.forEach((card) => {{
                const haystack = card.dataset.search || "";
                card.classList.toggle("hidden", term.length > 0 && !haystack.includes(term));
            }});

            sections.forEach((section) => {{
                const visibleCards = section.querySelectorAll(".resource-card:not(.hidden)").length;
                section.classList.toggle("hidden", visibleCards === 0);
            }});
        }}

        searchInput.addEventListener("input", applyFilter);
    </script>
</body>
</html>
"""


def main() -> int:
    pages = load_pages()
    if not pages:
        raise SystemExit("No HTML pages found to index.")
    OUTPUT_PATH.write_text(render_index(pages), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH.name} with {len(pages)} entries.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
