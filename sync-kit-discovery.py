#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

SITE_ROOT = Path("/var/www/web-ceo")
DATEKIT_ROOT = Path("/var/www/datekit")
HOMEPAGE_PATH = SITE_ROOT / "index.html"
KITS_DIR = SITE_ROOT / "kits"
KITS_PAGE_PATH = KITS_DIR / "index.html"

KITS = [
    {
        "slug": "datekit",
        "name": "DateKit",
        "url": "/datekit/",
        "icon": "&#x1f4c5;",
        "summary": "Date difference, date math, business-day, and Unix-time conversion calculators.",
    },
    {
        "slug": "budgetkit",
        "name": "BudgetKit",
        "url": "/budgetkit/",
        "icon": "&#x1f4b8;",
        "summary": "Budget planning, debt payoff, savings, and emergency fund calculators.",
    },
    {
        "slug": "healthkit",
        "name": "HealthKit",
        "url": "/healthkit/",
        "icon": "&#x1f9ee;",
        "summary": "BMI, calories, macro, and hydration planning calculators in one suite.",
    },
    {
        "slug": "sleepkit",
        "name": "SleepKit",
        "url": "/sleepkit/",
        "icon": "&#x1f634;",
        "summary": "Sleep cycles, bedtime, wake time, and sleep debt recovery planning tools.",
    },
    {
        "slug": "focuskit",
        "name": "FocusKit",
        "url": "/focuskit/",
        "icon": "&#x1f3af;",
        "summary": "Focus session, time block, and meeting load calculators for deep-work planning.",
    },
    {
        "slug": "opskit",
        "name": "OpsKit",
        "url": "/opskit/",
        "icon": "&#x1f6e0;",
        "summary": "SLA, error-budget, incident-cost, and on-call load calculators for reliability planning.",
    },
    {
        "slug": "studykit",
        "name": "StudyKit",
        "url": "/studykit/",
        "icon": "&#x1f393;",
        "summary": "GPA, final-grade, and study-time calculators for exam preparation.",
    },
    {
        "slug": "careerkit",
        "name": "CareerKit",
        "url": "/careerkit/",
        "icon": "&#x1f4bc;",
        "summary": "Salary, raise, overtime, and offer comparison calculators for career planning.",
    },
]

KIT_ROOTS = {
    "datekit": DATEKIT_ROOT,
    "budgetkit": SITE_ROOT / "budgetkit",
    "healthkit": SITE_ROOT / "healthkit",
    "sleepkit": SITE_ROOT / "sleepkit",
    "focuskit": SITE_ROOT / "focuskit",
    "opskit": SITE_ROOT / "opskit",
    "studykit": SITE_ROOT / "studykit",
    "careerkit": SITE_ROOT / "careerkit",
}

KIT_CARD_BLOCK = """
                <a href="/datekit/" class="tool-card" data-tags="date calculator date difference add subtract days unix time converter">
                    <div class="tool-icon">&#x1f4c5;</div>
                    <h3>DateKit</h3>
                    <p>Date difference, date math, and Unix converter in one focused app</p>
                </a>
                <a href="/budgetkit/" class="tool-card" data-tags="budget calculator savings calculator debt payoff calculator emergency fund planner">
                    <div class="tool-icon">&#x1f4b8;</div>
                    <h3>BudgetKit</h3>
                    <p>Budget, savings, and debt payoff calculators for practical money planning</p>
                </a>
                <a href="/healthkit/" class="tool-card" data-tags="health calculator bmi calculator calorie calculator tdee macro calculator">
                    <div class="tool-icon">&#x1f9ee;</div>
                    <h3>HealthKit</h3>
                    <p>BMI, calorie, and macro calculators in one focused app</p>
                </a>
                <a href="/sleepkit/" class="tool-card" data-tags="sleep cycle calculator bedtime calculator wake time calculator sleep planner">
                    <div class="tool-icon">&#x1f634;</div>
                    <h3>SleepKit</h3>
                    <p>Plan bedtime and wake-up windows around full sleep cycles</p>
                </a>
                <a href="/focuskit/" class="tool-card" data-tags="focus session calculator time block calculator meeting load calculator deep work planner">
                    <div class="tool-icon">&#x1f3af;</div>
                    <h3>FocusKit</h3>
                    <p>Plan deep-work sessions, schedule blocks, and reduce meeting drag</p>
                </a>
                <a href="/opskit/" class="tool-card" data-tags="ops calculator sla downtime error budget incident cost on-call load">
                    <div class="tool-icon">&#x1f6e0;</div>
                    <h3>OpsKit</h3>
                    <p>Model reliability targets, burn rate, and incident-response load</p>
                </a>
                <a href="/studykit/" class="tool-card" data-tags="gpa calculator final grade calculator study time calculator exam planner">
                    <div class="tool-icon">&#x1f393;</div>
                    <h3>StudyKit</h3>
                    <p>Track GPA, set exam targets, and plan study workload</p>
                </a>
                <a href="/careerkit/" class="tool-card" data-tags="salary calculator raise calculator overtime calculator offer comparison calculator">
                    <div class="tool-icon">&#x1f4bc;</div>
                    <h3>CareerKit</h3>
                    <p>Compare offers, project raises, and plan compensation decisions</p>
                </a>
"""


def calculator_count(root: Path) -> int:
    if not root.exists():
        return 0
    return sum(1 for page in root.glob("*.html") if page.name != "index.html")


def build_hub_cards(counts: dict[str, int]) -> str:
    cards: list[str] = []
    for item in KITS:
        cards.append(
            "            <a href=\"{url}\" class=\"tool-card\" data-tags=\"{slug} calculator suite planning tools\">"
            "<div class=\"tool-icon\">{icon}</div>"
            "<h2>{name}</h2>"
            "<p>{summary}</p>"
            "<p style=\"margin-top: 0.65rem; color: #3b82f6; font-weight: 600;\">{count} calculators</p>"
            "</a>".format(
                url=item["url"],
                slug=item["slug"],
                icon=item["icon"],
                name=item["name"],
                summary=item["summary"],
                count=counts.get(item["slug"], 0),
            )
        )
    return "\n".join(cards)


def build_itemlist_json() -> str:
    lines = []
    for position, item in enumerate(KITS, start=1):
        lines.append(
            f'          {{"@type": "ListItem", "position": {position}, "name": "{item["name"]}", "url": "https://devtoolbox.dedyn.io{item["url"]}"}}'
        )
    return ",\n".join(lines)


def render_kits_page(counts: dict[str, int]) -> str:
    total_calculators = sum(counts.values())
    cards_html = build_hub_cards(counts)
    itemlist_json = build_itemlist_json()
    template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Life Kits Directory — Date, Budget, Health, Sleep, Focus, Ops, Study, and Career Calculators</title>
    <meta name="description" content="Discover all DevToolbox planning suites in one place: DateKit, BudgetKit, HealthKit, SleepKit, FocusKit, OpsKit, StudyKit, and CareerKit. __TOTAL_CALCULATORS__ free calculators with no signup.">
    <meta name="robots" content="index, follow">
    <link rel="canonical" href="https://devtoolbox.dedyn.io/kits/">
    <meta property="og:title" content="Life Kits Directory — Free Planning Calculator Suites">
    <meta property="og:description" content="Explore DateKit, BudgetKit, HealthKit, SleepKit, FocusKit, OpsKit, StudyKit, and CareerKit from one discovery hub.">
    <meta property="og:type" content="website">
    <meta property="og:url" content="https://devtoolbox.dedyn.io/kits/">
    <meta property="og:site_name" content="DevToolbox">
    <meta property="og:image" content="https://devtoolbox.dedyn.io/og/default.png">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="Life Kits Directory — Free Planning Calculator Suites">
    <meta name="twitter:description" content="Date, budget, health, sleep, focus, ops, study, and career calculator suites in one place.">
    <meta name="twitter:image" content="https://devtoolbox.dedyn.io/og/default.png">
    <link rel="icon" href="/favicon.ico" sizes="any">
    <link rel="icon" href="/favicon.svg" type="image/svg+xml">
    <link rel="apple-touch-icon" href="/icons/icon-192.png">
    <link rel="manifest" href="/manifest.json">
    <meta name="theme-color" content="#3b82f6">
    <link rel="stylesheet" href="/css/style.css">
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": "Life Kits Directory",
        "description": "Directory of date, budget, health, sleep, focus, ops, study, and career planning calculator suites.",
        "url": "https://devtoolbox.dedyn.io/kits/",
        "isPartOf": {
            "@type": "WebSite",
            "name": "DevToolbox",
            "url": "https://devtoolbox.dedyn.io/"
        }
    }
    </script>
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": "Planning Calculator Suites",
        "itemListElement": [
__ITEMLIST_JSON__
        ]
    }
    </script>
    <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@type": "FAQPage",
      "mainEntity": [
        {
          "@type": "Question",
          "name": "Do these calculator suites require signup?",
          "acceptedAnswer": {
            "@type": "Answer",
            "text": "No. All calculators across DateKit, BudgetKit, HealthKit, SleepKit, FocusKit, OpsKit, StudyKit, and CareerKit are free and available without signup."
          }
        },
        {
          "@type": "Question",
          "name": "Can I use these suites on mobile?",
          "acceptedAnswer": {
            "@type": "Answer",
            "text": "Yes. Every suite in the directory is mobile friendly and can be used directly in a browser."
          }
        },
        {
          "@type": "Question",
          "name": "Where should I start?",
          "acceptedAnswer": {
            "@type": "Answer",
            "text": "Start with the suite tied to your immediate planning need, then use the directory links to move between related suites."
          }
        }
      ]
    }
    </script>
</head>
<body>
    <header>
        <nav>
            <a href="/" class="logo">
                <span class="logo-icon">{ }</span>
                <span>DevToolbox</span>
            </a>
            <div class="nav-links">
                <a href="/tools/">Tools</a>
                <a href="/cheatsheets/">Cheat Sheets</a>
                <a href="/blog/">Blog</a>
                <a href="/kits/">Life Kits</a>
            </div>
        </nav>
    </header>
    <nav class="breadcrumb" aria-label="Breadcrumb">
        <a href="/">Home</a><span class="separator">/</span><span class="current">Life Kits</span>
    </nav>
    <main class="tool-page">
        <h1>Life Kits Directory</h1>
        <p class="description">Switch quickly between all planning calculator suites. __TOTAL_CALCULATORS__ calculators are currently available across eight focused kits.</p>
        <div class="grid" style="margin-top: 1.25rem;">
__CARDS_HTML__
        </div>
        <section class="panel card" style="margin-top: 1.5rem; padding: 1rem 1.25rem; border: 1px solid rgba(59,130,246,0.25); border-radius: 8px; background: rgba(59,130,246,0.08);">
            <h2 style="font-size: 1.2rem; margin-bottom: 0.5rem;">How to Use This Directory</h2>
            <p style="margin: 0;">Use DateKit for scheduling math, BudgetKit for money decisions, HealthKit and SleepKit for wellness planning, FocusKit for deep-work execution planning, OpsKit for reliability operations planning, StudyKit for academic planning, and CareerKit for compensation decisions. Each suite cross-links to related paths so you can move between tasks without restarting your workflow.</p>
        </section>
    </main>
    <footer>
        <p>DevToolbox &mdash; Free practical calculators for daily planning.</p>
    </footer>
    <script src="/js/track.js" defer></script>
</body>
</html>
"""
    return (
        template.replace("__TOTAL_CALCULATORS__", str(total_calculators))
        .replace("__CARDS_HTML__", cards_html)
        .replace("__ITEMLIST_JSON__", itemlist_json)
    )


def ensure_kits_nav_link(homepage_html: str) -> str:
    if '<a href="/kits/">Life Kits</a>' in homepage_html:
        return homepage_html

    blog_link = '<a href="/blog/">Blog</a>'
    if blog_link in homepage_html:
        return homepage_html.replace(
            blog_link,
            blog_link + "\n                <a href=\"/kits/\">Life Kits</a>",
            1,
        )

    nav_pattern = re.compile(r'(<div class="nav-links">)(.*?)(</div>)', re.DOTALL)
    match = nav_pattern.search(homepage_html)
    if not match:
        return homepage_html

    nav_inner = match.group(2).rstrip()
    updated_inner = nav_inner + "\n                <a href=\"/kits/\">Life Kits</a>\n            "
    return homepage_html[: match.start()] + match.group(1) + updated_inner + match.group(3) + homepage_html[match.end() :]


def ensure_homepage_kit_cards(homepage_html: str) -> str:
    section_pattern = re.compile(
        r'(<section class="tools-grid" id="toolsGrid">\s*<h2>Popular Tools</h2>\s*<div class="grid">)(.*?)(\s*</div>\s*</section>)',
        re.DOTALL,
    )
    match = section_pattern.search(homepage_html)
    if not match:
        return homepage_html

    grid_html = match.group(2)
    grid_html = re.sub(
        r'\s*<a href="/(?:datekit|budgetkit|healthkit|sleepkit|focuskit|opskit|studykit|careerkit)/" class="tool-card"[^>]*>.*?</a>\s*',
        "\n",
        grid_html,
        flags=re.DOTALL,
    )

    timestamp_card_pattern = re.compile(
        r'(<a href="/tools/timestamp" class="tool-card"[^>]*>.*?</a>\s*)',
        re.DOTALL,
    )
    if timestamp_card_pattern.search(grid_html):
        grid_html = timestamp_card_pattern.sub(r"\1" + KIT_CARD_BLOCK + "\n", grid_html, count=1)
    else:
        grid_html = KIT_CARD_BLOCK + "\n" + grid_html

    return homepage_html[: match.start()] + match.group(1) + grid_html + match.group(3) + homepage_html[match.end() :]


def main() -> None:
    counts = {slug: calculator_count(path) for slug, path in KIT_ROOTS.items()}
    KITS_DIR.mkdir(parents=True, exist_ok=True)
    KITS_PAGE_PATH.write_text(render_kits_page(counts), encoding="utf-8")

    homepage_html = HOMEPAGE_PATH.read_text(encoding="utf-8")
    updated = ensure_kits_nav_link(homepage_html)
    updated = ensure_homepage_kit_cards(updated)
    HOMEPAGE_PATH.write_text(updated, encoding="utf-8")

    total_calculators = sum(counts.values())
    print(f"Wrote {KITS_PAGE_PATH} ({total_calculators} calculators across {len(KITS)} kits)")
    print(f"Patched {HOMEPAGE_PATH} with kits nav + kit cards")


if __name__ == "__main__":
    main()
