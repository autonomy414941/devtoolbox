#!/usr/bin/env python3
"""Bulk SEO upgrade for all DevToolbox pages.
Adds: OG tags, JSON-LD, breadcrumbs, favicon/manifest, meta robots."""

import os
import re
import json
from pathlib import Path

SITE_ROOT = Path("/var/www/web-ceo")
BASE_URL = "http://46.225.49.219"

# Page metadata for structured data
TOOL_DESCRIPTIONS = {
    "json-formatter": ("JSON Formatter & Validator", "Format, validate, and beautify JSON data", "json,formatter,validator"),
    "base64": ("Base64 Encoder/Decoder", "Encode and decode Base64 data", "base64,encoder,decoder"),
    "url-encode": ("URL Encoder/Decoder", "Encode and decode URL components", "url,encoder,decoder"),
    "regex-tester": ("Regex Tester", "Test and debug regular expressions in real-time", "regex,tester,regular expressions"),
    "timestamp": ("Unix Timestamp Converter", "Convert between Unix timestamps and dates", "timestamp,unix,converter"),
    "hash-generator": ("Hash Generator", "Generate MD5, SHA-1, SHA-256 hashes", "hash,md5,sha,generator"),
    "color-picker": ("Color Picker & Converter", "Pick colors and convert between formats", "color,picker,hex,rgb,hsl"),
    "jwt-decoder": ("JWT Decoder", "Decode and inspect JSON Web Tokens", "jwt,decoder,json web token"),
    "diff-checker": ("Diff Checker", "Compare two texts and see differences", "diff,compare,checker"),
    "uuid-generator": ("UUID Generator", "Generate random UUIDs/GUIDs", "uuid,guid,generator"),
    "lorem-ipsum": ("Lorem Ipsum Generator", "Generate placeholder text", "lorem ipsum,placeholder,text"),
    "markdown-preview": ("Markdown Preview", "Preview Markdown with live rendering", "markdown,preview,renderer"),
    "css-minifier": ("CSS Minifier", "Minify and compress CSS code", "css,minifier,compress"),
    "html-entity": ("HTML Entity Encoder/Decoder", "Encode and decode HTML entities", "html,entity,encoder"),
    "cron-parser": ("Cron Expression Parser", "Parse and explain cron expressions", "cron,parser,scheduler"),
    "json-to-csv": ("JSON to CSV Converter", "Convert JSON data to CSV format", "json,csv,converter"),
    "password-generator": ("Password Generator", "Generate secure random passwords", "password,generator,security"),
    "yaml-validator": ("YAML Validator & Formatter", "Validate and format YAML documents", "yaml,validator,formatter"),
    "text-case-converter": ("Text Case Converter", "Convert text between cases", "text,case,converter,camelCase"),
    "qr-code-generator": ("QR Code Generator", "Generate QR codes from text or URLs", "qr code,generator"),
    "json-schema-validator": ("JSON Schema Validator", "Validate JSON against a schema", "json,schema,validator"),
    "number-base-converter": ("Number Base Converter", "Convert between binary, octal, decimal, hex", "number,base,converter,binary,hex"),
    "ip-lookup": ("IP Address Lookup", "Look up IP address information", "ip,address,lookup,geolocation"),
    "sql-formatter": ("SQL Formatter", "Format and beautify SQL queries", "sql,formatter,beautifier"),
    "html-beautifier": ("HTML Beautifier", "Format and indent HTML code", "html,beautifier,formatter"),
    "js-minifier": ("JavaScript Minifier", "Minify and compress JavaScript", "javascript,minifier,compress"),
}

CHEATSHEET_DESCRIPTIONS = {
    "http-status-codes": ("HTTP Status Codes", "Complete reference of HTTP status codes with descriptions"),
    "git-commands": ("Git Commands", "Essential Git commands cheat sheet"),
    "css-flexbox": ("CSS Flexbox", "Complete CSS Flexbox layout reference"),
    "css-grid": ("CSS Grid", "CSS Grid layout properties and examples"),
    "docker-commands": ("Docker Commands", "Docker CLI commands reference"),
    "sql-basics": ("SQL Basics", "Essential SQL commands and syntax"),
    "bash-shortcuts": ("Bash Shortcuts", "Keyboard shortcuts for Bash terminal"),
    "vim-shortcuts": ("Vim Keyboard Shortcuts", "Essential Vim navigation and editing shortcuts"),
    "linux-permissions": ("Linux File Permissions", "Linux chmod, chown, and permission reference"),
    "python-string-methods": ("Python String Methods", "Python string methods quick reference"),
    "javascript-array-methods": ("JavaScript Array Methods", "JavaScript array methods cheat sheet"),
    "kubernetes-commands": ("Kubernetes Commands", "kubectl commands and Kubernetes reference"),
    "typescript-types": ("TypeScript Types", "TypeScript type system cheat sheet"),
    "react-hooks": ("React Hooks", "React Hooks API reference and examples"),
}

BLOG_DESCRIPTIONS = {
    "json-api-debugging-tips": ("10 JSON API Debugging Tips Every Developer Should Know", "2025-01-15"),
    "regex-guide-for-beginners": ("Regex Guide for Beginners: From Zero to Pattern Matching", "2025-01-20"),
    "http-status-codes-explained": ("HTTP Status Codes Explained: The Complete Developer Guide", "2025-01-25"),
    "cron-job-schedule-guide": ("Cron Job Scheduling: A Practical Guide with Examples", "2025-02-01"),
    "css-performance-optimization": ("CSS Performance Optimization: 12 Techniques That Actually Work", "2025-02-05"),
    "git-commands-every-developer-should-know": ("25 Git Commands Every Developer Should Know", "2025-02-08"),
    "javascript-array-methods-complete-guide": ("JavaScript Array Methods: The Complete Guide", "2025-02-09"),
    "docker-containers-beginners-guide": ("Docker Containers for Beginners: A Practical Guide", "2025-02-10"),
    "typescript-tips-and-tricks": ("15 TypeScript Tips and Tricks for Cleaner Code", "2025-02-11"),
}

# Cross-linking maps
TOOL_RELATED = {
    "color-picker": [("hash-generator", "Hash Generator"), ("css-minifier", "CSS Minifier"), ("text-case-converter", "Text Case Converter")],
    "cron-parser": [("timestamp", "Timestamp Converter"), ("regex-tester", "Regex Tester"), ("json-formatter", "JSON Formatter")],
    "css-minifier": [("html-beautifier", "HTML Beautifier"), ("js-minifier", "JS Minifier"), ("color-picker", "Color Picker")],
    "diff-checker": [("json-formatter", "JSON Formatter"), ("markdown-preview", "Markdown Preview"), ("text-case-converter", "Text Case")],
    "html-entity": [("url-encode", "URL Encoder"), ("html-beautifier", "HTML Beautifier"), ("base64", "Base64 Encoder")],
    "json-to-csv": [("json-formatter", "JSON Formatter"), ("json-schema-validator", "JSON Schema Validator"), ("yaml-validator", "YAML Validator")],
    "jwt-decoder": [("base64", "Base64 Encoder"), ("hash-generator", "Hash Generator"), ("json-formatter", "JSON Formatter")],
    "lorem-ipsum": [("text-case-converter", "Text Case Converter"), ("password-generator", "Password Generator"), ("uuid-generator", "UUID Generator")],
    "markdown-preview": [("html-beautifier", "HTML Beautifier"), ("diff-checker", "Diff Checker"), ("text-case-converter", "Text Case")],
    "password-generator": [("hash-generator", "Hash Generator"), ("uuid-generator", "UUID Generator"), ("base64", "Base64 Encoder")],
    "timestamp": [("cron-parser", "Cron Parser"), ("uuid-generator", "UUID Generator"), ("json-formatter", "JSON Formatter")],
    "url-encode": [("base64", "Base64 Encoder"), ("html-entity", "HTML Entity Encoder"), ("json-formatter", "JSON Formatter")],
    "uuid-generator": [("hash-generator", "Hash Generator"), ("password-generator", "Password Generator"), ("timestamp", "Timestamp")],
}

CHEATSHEET_RELATED = {
    "bash-shortcuts": [("/cheatsheets/vim-shortcuts", "Vim Shortcuts"), ("/cheatsheets/linux-permissions", "Linux Permissions"), ("/cheatsheets/git-commands", "Git Commands")],
    "css-flexbox": [("/cheatsheets/css-grid", "CSS Grid"), ("/tools/css-minifier", "CSS Minifier"), ("/blog/css-performance-optimization", "CSS Performance")],
    "css-grid": [("/cheatsheets/css-flexbox", "CSS Flexbox"), ("/tools/css-minifier", "CSS Minifier"), ("/blog/css-performance-optimization", "CSS Performance")],
    "docker-commands": [("/cheatsheets/kubernetes-commands", "Kubernetes Commands"), ("/blog/docker-containers-beginners-guide", "Docker Guide"), ("/cheatsheets/bash-shortcuts", "Bash Shortcuts")],
    "git-commands": [("/blog/git-commands-every-developer-should-know", "Git Guide"), ("/cheatsheets/bash-shortcuts", "Bash Shortcuts"), ("/tools/diff-checker", "Diff Checker")],
    "http-status-codes": [("/blog/http-status-codes-explained", "HTTP Codes Guide"), ("/tools/json-formatter", "JSON Formatter"), ("/cheatsheets/sql-basics", "SQL Basics")],
    "javascript-array-methods": [("/blog/javascript-array-methods-complete-guide", "Array Methods Guide"), ("/cheatsheets/typescript-types", "TypeScript Types"), ("/cheatsheets/react-hooks", "React Hooks")],
    "linux-permissions": [("/cheatsheets/bash-shortcuts", "Bash Shortcuts"), ("/cheatsheets/docker-commands", "Docker Commands"), ("/cheatsheets/vim-shortcuts", "Vim Shortcuts")],
    "python-string-methods": [("/cheatsheets/bash-shortcuts", "Bash Shortcuts"), ("/tools/regex-tester", "Regex Tester"), ("/tools/text-case-converter", "Text Case Converter")],
    "react-hooks": [("/cheatsheets/typescript-types", "TypeScript Types"), ("/cheatsheets/javascript-array-methods", "JS Array Methods"), ("/tools/json-formatter", "JSON Formatter")],
    "sql-basics": [("/tools/sql-formatter", "SQL Formatter"), ("/cheatsheets/docker-commands", "Docker Commands"), ("/cheatsheets/git-commands", "Git Commands")],
    "typescript-types": [("/cheatsheets/react-hooks", "React Hooks"), ("/blog/typescript-tips-and-tricks", "TypeScript Tips"), ("/cheatsheets/javascript-array-methods", "JS Array Methods")],
    "vim-shortcuts": [("/cheatsheets/bash-shortcuts", "Bash Shortcuts"), ("/cheatsheets/linux-permissions", "Linux Permissions"), ("/cheatsheets/git-commands", "Git Commands")],
}


def add_breadcrumb_css():
    """Add breadcrumb styles to the CSS file."""
    css_file = SITE_ROOT / "css" / "style.css"
    content = css_file.read_text()

    if ".breadcrumb" in content:
        return  # Already has breadcrumb styles

    breadcrumb_css = """
/* Breadcrumbs */
.breadcrumb {
    max-width: var(--max-width);
    margin: 0 auto;
    padding: 0.75rem 1.5rem 0;
    font-size: 0.85rem;
    color: var(--text-muted);
}

.breadcrumb a { color: var(--text-muted); }
.breadcrumb a:hover { color: var(--primary); }
.breadcrumb span.separator { margin: 0 0.5rem; opacity: 0.5; }
.breadcrumb span.current { color: var(--text); }

/* Embed banner */
.embed-banner {
    max-width: var(--max-width);
    margin: 1rem auto 0;
    padding: 0.75rem 1.5rem;
}

.embed-banner details {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 0.75rem 1rem;
}

.embed-banner summary {
    cursor: pointer;
    color: var(--text-muted);
    font-size: 0.85rem;
}

.embed-banner pre {
    margin-top: 0.5rem;
    background: var(--code-bg);
    padding: 0.75rem;
    border-radius: var(--radius);
    overflow-x: auto;
    font-size: 0.8rem;
}

.embed-banner code {
    font-family: 'SF Mono', 'Fira Code', monospace;
    color: var(--text);
}
"""
    content += breadcrumb_css
    css_file.write_text(content)
    print("  Added breadcrumb + embed CSS styles")


def get_og_tags(title, description, url, og_type="website"):
    """Generate Open Graph meta tags."""
    return f'''    <meta property="og:title" content="{title}">
    <meta property="og:description" content="{description}">
    <meta property="og:type" content="{og_type}">
    <meta property="og:url" content="{url}">
    <meta property="og:site_name" content="DevToolbox">
    <meta name="twitter:card" content="summary">
    <meta name="twitter:title" content="{title}">
    <meta name="twitter:description" content="{description}">'''


def get_favicon_links():
    """Generate favicon/manifest/theme meta tags."""
    return '''    <link rel="icon" href="/favicon.ico" sizes="any">
    <link rel="icon" href="/favicon.svg" type="image/svg+xml">
    <link rel="apple-touch-icon" href="/icons/icon-192.png">
    <link rel="manifest" href="/manifest.json">
    <meta name="theme-color" content="#3b82f6">'''


def get_breadcrumb_html(crumbs):
    """Generate breadcrumb navigation HTML.
    crumbs: list of (url, label) tuples. Last one is current page (no link)."""
    parts = []
    for i, (url, label) in enumerate(crumbs):
        if i == len(crumbs) - 1:
            parts.append(f'<span class="current">{label}</span>')
        else:
            parts.append(f'<a href="{url}">{label}</a>')

    separator = '<span class="separator">/</span>'
    nav_html = separator.join(parts)

    # JSON-LD breadcrumb
    items = []
    for i, (url, label) in enumerate(crumbs):
        items.append({
            "@type": "ListItem",
            "position": i + 1,
            "name": label,
            "item": f"{BASE_URL}{url}" if url != "#" else None
        })
    # Remove None items from last breadcrumb
    for item in items:
        if item.get("item") is None:
            del item["item"]

    ld_json = json.dumps({
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": items
    }, indent=8)

    return f'''    <nav class="breadcrumb" aria-label="Breadcrumb">{nav_html}</nav>
    <script type="application/ld+json">
    {ld_json}
    </script>'''


def get_tool_jsonld(name, title, description, url):
    """Generate JSON-LD for a tool page."""
    data = {
        "@context": "https://schema.org",
        "@type": "WebApplication",
        "name": title,
        "description": description,
        "url": url,
        "applicationCategory": "DeveloperApplication",
        "operatingSystem": "Any",
        "offers": {
            "@type": "Offer",
            "price": "0",
            "priceCurrency": "USD"
        },
        "creator": {
            "@type": "Organization",
            "name": "DevToolbox"
        }
    }
    return f'''    <script type="application/ld+json">
    {json.dumps(data, indent=8)}
    </script>'''


def get_blog_jsonld(title, description, date_published, url):
    """Generate JSON-LD for a blog post."""
    data = {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": title,
        "description": description,
        "datePublished": date_published,
        "dateModified": date_published,
        "url": url,
        "author": {
            "@type": "Organization",
            "name": "DevToolbox"
        },
        "publisher": {
            "@type": "Organization",
            "name": "DevToolbox"
        }
    }
    return f'''    <script type="application/ld+json">
    {json.dumps(data, indent=8)}
    </script>'''


def get_related_section_html(related_items, section_title="Related Tools"):
    """Generate related content section HTML."""
    cards = ""
    for url, title in related_items:
        if not url.startswith("/"):
            url = f"/tools/{url}"
        cards += f'''        <a href="{url}" class="tool-card">
            <h3>{title}</h3>
        </a>
'''
    return f'''
    <section class="related-tools">
        <h3>{section_title}</h3>
        <div class="grid">
{cards}        </div>
    </section>
'''


def get_embed_snippet(tool_slug, tool_title):
    """Generate embed snippet HTML for a tool."""
    return f'''
    <div class="embed-banner">
        <details>
            <summary>Embed this tool on your site</summary>
            <pre><code>&lt;iframe src="{BASE_URL}/tools/{tool_slug}" width="100%" height="600" frameborder="0" title="{tool_title}"&gt;&lt;/iframe&gt;</code></pre>
        </details>
    </div>
'''


def upgrade_tool_page(filepath):
    """Add SEO elements to a tool page."""
    slug = filepath.stem
    if slug == "index":
        return upgrade_tool_index(filepath)

    info = TOOL_DESCRIPTIONS.get(slug)
    if not info:
        print(f"  SKIP {slug} — no metadata defined")
        return

    title, description, keywords = info
    url = f"{BASE_URL}/tools/{slug}"
    content = filepath.read_text()
    modified = False

    # Add OG tags if missing
    if 'og:title' not in content:
        og_tags = get_og_tags(f"{title} | DevToolbox", description, url)
        content = content.replace('    <link rel="canonical"', f'{og_tags}\n    <meta name="robots" content="index, follow">\n    <link rel="canonical"')
        modified = True

    # Add favicon/manifest if missing
    if 'favicon.ico' not in content:
        favicon = get_favicon_links()
        content = content.replace('    <link rel="stylesheet"', f'{favicon}\n    <link rel="stylesheet"')
        modified = True

    # Add JSON-LD if missing
    if 'application/ld+json' not in content:
        jsonld = get_tool_jsonld(slug, title, description, url)
        content = content.replace('</head>', f'{jsonld}\n</head>')
        modified = True

    # Add breadcrumbs after header if missing
    if 'breadcrumb' not in content:
        breadcrumb = get_breadcrumb_html([
            ("/", "Home"),
            ("/tools", "Tools"),
            ("#", title)
        ])
        content = content.replace('</header>\n', f'</header>\n{breadcrumb}\n')
        modified = True

    # Add related tools if missing
    if 'related-tools' not in content and slug in TOOL_RELATED:
        related = get_related_section_html(TOOL_RELATED[slug])
        # Insert before </main> or before footer
        if '</main>' in content:
            content = content.replace('</main>', f'{related}\n    </main>')
        modified = True

    # Add embed snippet if missing
    if 'embed-banner' not in content:
        embed = get_embed_snippet(slug, title)
        # Insert after breadcrumb or after header
        if 'breadcrumb' in content:
            # Insert after the breadcrumb script closing tag
            content = content.replace('    </script>\n\n    <main', f'    </script>\n{embed}\n    <main')
        modified = True

    if modified:
        filepath.write_text(content)
        print(f"  UPGRADED: tools/{slug}")
    else:
        print(f"  OK: tools/{slug} (already complete)")


def upgrade_tool_index(filepath):
    """Add SEO elements to the tools index page."""
    content = filepath.read_text()
    modified = False

    if 'og:title' not in content:
        og_tags = get_og_tags("26 Free Online Developer Tools | DevToolbox",
                              "JSON formatter, Base64 encoder, regex tester, SQL formatter, and 22 more free developer tools. 100% client-side.",
                              f"{BASE_URL}/tools")
        content = content.replace('    <link rel="canonical"', f'{og_tags}\n    <meta name="robots" content="index, follow">\n    <link rel="canonical"')
        modified = True

    if 'favicon.ico' not in content:
        favicon = get_favicon_links()
        content = content.replace('    <link rel="stylesheet"', f'{favicon}\n    <link rel="stylesheet"')
        modified = True

    if 'application/ld+json' not in content:
        data = {
            "@context": "https://schema.org",
            "@type": "CollectionPage",
            "name": "Developer Tools",
            "description": "26 free online developer tools",
            "url": f"{BASE_URL}/tools",
            "isPartOf": {"@type": "WebSite", "name": "DevToolbox"}
        }
        jsonld = f'    <script type="application/ld+json">\n    {json.dumps(data, indent=8)}\n    </script>'
        content = content.replace('</head>', f'{jsonld}\n</head>')
        modified = True

    if 'breadcrumb' not in content:
        breadcrumb = get_breadcrumb_html([("/", "Home"), ("#", "Tools")])
        content = content.replace('</header>\n', f'</header>\n{breadcrumb}\n')
        modified = True

    if modified:
        filepath.write_text(content)
        print(f"  UPGRADED: tools/index")


def upgrade_cheatsheet_page(filepath):
    """Add SEO elements to a cheatsheet page."""
    slug = filepath.stem
    if slug == "index":
        return upgrade_cheatsheet_index(filepath)

    info = CHEATSHEET_DESCRIPTIONS.get(slug)
    if not info:
        print(f"  SKIP cheatsheets/{slug} — no metadata defined")
        return

    title, description = info
    url = f"{BASE_URL}/cheatsheets/{slug}"
    content = filepath.read_text()
    modified = False

    if 'og:title' not in content:
        og_tags = get_og_tags(f"{title} Cheat Sheet | DevToolbox", description, url)
        content = content.replace('    <link rel="canonical"', f'{og_tags}\n    <meta name="robots" content="index, follow">\n    <link rel="canonical"')
        modified = True

    if 'favicon.ico' not in content:
        favicon = get_favicon_links()
        content = content.replace('    <link rel="stylesheet"', f'{favicon}\n    <link rel="stylesheet"')
        modified = True

    if 'application/ld+json' not in content:
        data = {
            "@context": "https://schema.org",
            "@type": "Article",
            "name": f"{title} Cheat Sheet",
            "description": description,
            "url": url,
            "author": {"@type": "Organization", "name": "DevToolbox"},
            "publisher": {"@type": "Organization", "name": "DevToolbox"}
        }
        jsonld = f'    <script type="application/ld+json">\n    {json.dumps(data, indent=8)}\n    </script>'
        content = content.replace('</head>', f'{jsonld}\n</head>')
        modified = True

    if 'breadcrumb' not in content:
        breadcrumb = get_breadcrumb_html([
            ("/", "Home"),
            ("/cheatsheets", "Cheat Sheets"),
            ("#", title)
        ])
        content = content.replace('</header>\n', f'</header>\n{breadcrumb}\n')
        modified = True

    # Add related section if missing
    if 'related-tools' not in content and slug in CHEATSHEET_RELATED:
        related = get_related_section_html(CHEATSHEET_RELATED[slug], "Related Resources")
        if '</main>' in content:
            content = content.replace('</main>', f'{related}\n    </main>')
        elif '<footer>' in content:
            content = content.replace('<footer>', f'{related}\n\n    <footer>')
        modified = True

    if modified:
        filepath.write_text(content)
        print(f"  UPGRADED: cheatsheets/{slug}")
    else:
        print(f"  OK: cheatsheets/{slug}")


def upgrade_cheatsheet_index(filepath):
    """Add SEO elements to cheatsheets index."""
    content = filepath.read_text()
    modified = False

    if 'og:title' not in content:
        og_tags = get_og_tags("14 Developer Cheat Sheets | DevToolbox",
                              "Quick reference cheat sheets for Git, Docker, SQL, CSS, Kubernetes, TypeScript, React, and more.",
                              f"{BASE_URL}/cheatsheets")
        content = content.replace('    <link rel="canonical"', f'{og_tags}\n    <meta name="robots" content="index, follow">\n    <link rel="canonical"')
        modified = True

    if 'favicon.ico' not in content:
        favicon = get_favicon_links()
        content = content.replace('    <link rel="stylesheet"', f'{favicon}\n    <link rel="stylesheet"')
        modified = True

    if 'application/ld+json' not in content:
        data = {
            "@context": "https://schema.org",
            "@type": "CollectionPage",
            "name": "Developer Cheat Sheets",
            "description": "14 developer cheat sheets for quick reference",
            "url": f"{BASE_URL}/cheatsheets"
        }
        jsonld = f'    <script type="application/ld+json">\n    {json.dumps(data, indent=8)}\n    </script>'
        content = content.replace('</head>', f'{jsonld}\n</head>')
        modified = True

    if 'breadcrumb' not in content:
        breadcrumb = get_breadcrumb_html([("/", "Home"), ("#", "Cheat Sheets")])
        content = content.replace('</header>\n', f'</header>\n{breadcrumb}\n')
        modified = True

    if modified:
        filepath.write_text(content)
        print(f"  UPGRADED: cheatsheets/index")


def upgrade_blog_post(filepath):
    """Add SEO elements to a blog post."""
    slug = filepath.stem
    if slug == "index":
        return upgrade_blog_index(filepath)

    info = BLOG_DESCRIPTIONS.get(slug)
    if not info:
        print(f"  SKIP blog/{slug} — no metadata defined")
        return

    title, date_published = info
    url = f"{BASE_URL}/blog/{slug}"
    content = filepath.read_text()
    modified = False

    # Extract description from meta tag
    desc_match = re.search(r'<meta name="description" content="([^"]*)"', content)
    description = desc_match.group(1) if desc_match else title

    if 'og:title' not in content:
        og_tags = get_og_tags(f"{title} | DevToolbox", description, url, "article")
        og_tags += f'\n    <meta property="article:published_time" content="{date_published}">'
        content = content.replace('    <link rel="canonical"', f'{og_tags}\n    <meta name="robots" content="index, follow">\n    <link rel="canonical"')
        modified = True

    if 'favicon.ico' not in content:
        favicon = get_favicon_links()
        content = content.replace('    <link rel="stylesheet"', f'{favicon}\n    <link rel="stylesheet"')
        modified = True

    if 'application/ld+json' not in content:
        jsonld = get_blog_jsonld(title, description, date_published, url)
        content = content.replace('</head>', f'{jsonld}\n</head>')
        modified = True

    if 'breadcrumb' not in content:
        # Shorten title for breadcrumb
        short_title = title[:40] + "..." if len(title) > 40 else title
        breadcrumb = get_breadcrumb_html([
            ("/", "Home"),
            ("/blog", "Blog"),
            ("#", short_title)
        ])
        content = content.replace('</header>\n', f'</header>\n{breadcrumb}\n')
        modified = True

    if modified:
        filepath.write_text(content)
        print(f"  UPGRADED: blog/{slug}")
    else:
        print(f"  OK: blog/{slug}")


def upgrade_blog_index(filepath):
    """Add SEO elements to blog index."""
    content = filepath.read_text()
    modified = False

    if 'og:title' not in content:
        og_tags = get_og_tags("Developer Blog | DevToolbox",
                              "Tutorials, guides, and tips for developers. JSON debugging, regex, Git, Docker, TypeScript, and more.",
                              f"{BASE_URL}/blog")
        content = content.replace('    <link rel="canonical"', f'{og_tags}\n    <meta name="robots" content="index, follow">\n    <link rel="canonical"')
        modified = True

    if 'favicon.ico' not in content:
        favicon = get_favicon_links()
        content = content.replace('    <link rel="stylesheet"', f'{favicon}\n    <link rel="stylesheet"')
        modified = True

    if 'application/ld+json' not in content:
        data = {
            "@context": "https://schema.org",
            "@type": "Blog",
            "name": "DevToolbox Blog",
            "description": "Developer tutorials and guides",
            "url": f"{BASE_URL}/blog"
        }
        jsonld = f'    <script type="application/ld+json">\n    {json.dumps(data, indent=8)}\n    </script>'
        content = content.replace('</head>', f'{jsonld}\n</head>')
        modified = True

    if 'breadcrumb' not in content:
        breadcrumb = get_breadcrumb_html([("/", "Home"), ("#", "Blog")])
        content = content.replace('</header>\n', f'</header>\n{breadcrumb}\n')
        modified = True

    if modified:
        filepath.write_text(content)
        print(f"  UPGRADED: blog/index")


def main():
    print("=== DevToolbox SEO Bulk Upgrade ===\n")

    # 1. Add CSS styles
    print("[1] Adding CSS styles...")
    add_breadcrumb_css()

    # 2. Upgrade tool pages
    print("\n[2] Upgrading tool pages...")
    tools_dir = SITE_ROOT / "tools"
    for f in sorted(tools_dir.glob("*.html")):
        upgrade_tool_page(f)

    # 3. Upgrade cheatsheet pages
    print("\n[3] Upgrading cheatsheet pages...")
    cs_dir = SITE_ROOT / "cheatsheets"
    for f in sorted(cs_dir.glob("*.html")):
        upgrade_cheatsheet_page(f)

    # 4. Upgrade blog pages
    print("\n[4] Upgrading blog posts...")
    blog_dir = SITE_ROOT / "blog"
    for f in sorted(blog_dir.glob("*.html")):
        upgrade_blog_post(f)

    # 5. Summary
    print("\n=== Done! ===")
    total_tools = len(list(tools_dir.glob("*.html")))
    total_cs = len(list(cs_dir.glob("*.html")))
    total_blog = len(list(blog_dir.glob("*.html")))
    print(f"Processed: {total_tools} tools, {total_cs} cheatsheets, {total_blog} blog posts")


if __name__ == "__main__":
    main()
