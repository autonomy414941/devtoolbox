#!/usr/bin/env python3
"""Add 'Try Our Tool' callout boxes and 'Related Resources' sections to blog posts."""

import os
import re

BLOG_DIR = "/var/www/web-ceo/blog"

# Mapping: blog slug -> (tool callouts to insert, related resources section)
BLOG_DATA = {
    "http-status-codes-explained.html": {
        "callout": {
            "text": "Need a quick reference? Check out our <a href=\"/cheatsheets/http-status-codes\" style=\"color: #3b82f6;\">HTTP Status Codes Cheat Sheet</a> for a printable, searchable reference.",
            "position": "early"  # Insert after first few paragraphs
        },
        "related": [
            ("/cheatsheets/http-status-codes", "HTTP Status Codes Cheat Sheet", "Quick reference for all HTTP status codes"),
            ("/tools/http-tester", "HTTP Request Tester", "Test HTTP requests and see status codes in action"),
            ("/tools/json-formatter", "JSON Formatter", "Format API responses for easier debugging"),
            ("/blog/json-api-debugging-tips", "JSON API Debugging Tips", "More tips for working with APIs"),
        ]
    },
    "json-api-debugging-tips.html": {
        "callout": {
            "text": "Try it yourself: Use our <a href=\"/tools/json-formatter\" style=\"color: #3b82f6;\">JSON Formatter</a> to validate and beautify your API responses, or test endpoints with our <a href=\"/tools/http-tester\" style=\"color: #3b82f6;\">HTTP Request Tester</a>.",
            "position": "early"
        },
        "related": [
            ("/tools/json-formatter", "JSON Formatter", "Format and validate JSON responses"),
            ("/tools/http-tester", "HTTP Request Tester", "Send HTTP requests and inspect responses"),
            ("/tools/json-diff", "JSON Diff & Compare", "Compare API responses side by side"),
            ("/tools/json-path-finder", "JSON Path Finder", "Navigate complex JSON structures"),
        ]
    },
    "regex-guide-for-beginners.html": {
        "callout": {
            "text": "Practice as you learn: Open our <a href=\"/tools/regex-tester\" style=\"color: #3b82f6;\">Regex Tester</a> in another tab to try these patterns in real-time, or use the <a href=\"/tools/regex-debugger\" style=\"color: #3b82f6;\">Regex Debugger</a> to understand complex patterns.",
            "position": "early"
        },
        "related": [
            ("/tools/regex-tester", "Regex Tester", "Test regular expressions with real-time matching"),
            ("/tools/regex-debugger", "Regex Debugger", "Debug and visualize regex patterns step by step"),
            ("/tools/text-case-converter", "Text Case Converter", "Convert text between different case formats"),
        ]
    },
    "cron-job-schedule-guide.html": {
        "callout": {
            "text": "Build your cron schedule: Use our <a href=\"/tools/cron-parser\" style=\"color: #3b82f6;\">Cron Expression Parser</a> to build and verify cron schedules interactively.",
            "position": "early"
        },
        "related": [
            ("/tools/cron-parser", "Cron Expression Parser", "Parse and verify cron expressions"),
            ("/cheatsheets/bash-shortcuts", "Bash Shortcuts Cheat Sheet", "Essential terminal shortcuts"),
            ("/cheatsheets/linux-permissions", "Linux Permissions Cheat Sheet", "File permissions reference"),
        ]
    },
    "css-performance-optimization.html": {
        "callout": {
            "text": "Optimize your CSS: Use our <a href=\"/tools/css-minifier\" style=\"color: #3b82f6;\">CSS Minifier</a> to compress your stylesheets, or try the <a href=\"/tools/css-gradient\" style=\"color: #3b82f6;\">CSS Gradient Generator</a> for optimized gradient code.",
            "position": "early"
        },
        "related": [
            ("/tools/css-minifier", "CSS Minifier", "Minify and compress CSS code"),
            ("/tools/css-gradient", "CSS Gradient Generator", "Generate optimized CSS gradients"),
            ("/tools/box-shadow", "CSS Box Shadow Generator", "Create CSS box shadows visually"),
            ("/cheatsheets/css-flexbox", "CSS Flexbox Cheat Sheet", "Quick reference for Flexbox"),
        ]
    },
    "git-commands-every-developer-should-know.html": {
        "callout": {
            "text": "Keep this handy: Our <a href=\"/cheatsheets/git-commands\" style=\"color: #3b82f6;\">Git Commands Cheat Sheet</a> puts all essential commands on one page.",
            "position": "early"
        },
        "related": [
            ("/cheatsheets/git-commands", "Git Commands Cheat Sheet", "Quick reference for essential Git commands"),
            ("/tools/diff-checker", "Diff Checker", "Compare text changes side by side"),
            ("/cheatsheets/bash-shortcuts", "Bash Shortcuts", "Terminal shortcuts for faster Git workflow"),
        ]
    },
    "javascript-array-methods-complete-guide.html": {
        "callout": {
            "text": "Quick reference: Our <a href=\"/cheatsheets/javascript-array-methods\" style=\"color: #3b82f6;\">JavaScript Array Methods Cheat Sheet</a> has all methods on one page.",
            "position": "early"
        },
        "related": [
            ("/cheatsheets/javascript-array-methods", "JavaScript Array Methods Cheat Sheet", "All array methods at a glance"),
            ("/tools/json-formatter", "JSON Formatter", "Format and validate JSON data"),
            ("/cheatsheets/typescript-types", "TypeScript Types Cheat Sheet", "Type-safe JavaScript reference"),
            ("/blog/typescript-tips-and-tricks", "TypeScript Tips and Tricks", "Advanced TypeScript patterns"),
        ]
    },
    "docker-containers-beginners-guide.html": {
        "callout": {
            "text": "Quick reference: Bookmark our <a href=\"/cheatsheets/docker-commands\" style=\"color: #3b82f6;\">Docker Commands Cheat Sheet</a> for all essential Docker commands.",
            "position": "early"
        },
        "related": [
            ("/cheatsheets/docker-commands", "Docker Commands Cheat Sheet", "Essential Docker commands reference"),
            ("/cheatsheets/kubernetes-commands", "Kubernetes Commands Cheat Sheet", "Container orchestration reference"),
            ("/tools/yaml-validator", "YAML Validator", "Validate Docker Compose and Kubernetes YAML"),
        ]
    },
    "typescript-tips-and-tricks.html": {
        "callout": {
            "text": "Keep this handy: Our <a href=\"/cheatsheets/typescript-types\" style=\"color: #3b82f6;\">TypeScript Types Cheat Sheet</a> covers all built-in types and utility types.",
            "position": "early"
        },
        "related": [
            ("/cheatsheets/typescript-types", "TypeScript Types Cheat Sheet", "Complete TypeScript type reference"),
            ("/tools/json-schema-validator", "JSON Schema Validator", "Validate JSON with type-like schemas"),
            ("/cheatsheets/react-hooks", "React Hooks Cheat Sheet", "React hooks with TypeScript"),
            ("/blog/javascript-array-methods-complete-guide", "JavaScript Array Methods Guide", "Array methods in depth"),
        ]
    },
}

CALLOUT_STYLE = '''style="background: rgba(59, 130, 246, 0.08); border: 1px solid rgba(59, 130, 246, 0.2); border-radius: 8px; padding: 1rem 1.25rem; margin: 1.5rem 0; line-height: 1.7; color: #d1d5db;"'''

RELATED_SECTION_TEMPLATE = '''
    <section style="max-width: 800px; margin: 2.5rem auto; padding: 0 1rem;">
        <h2 style="margin-bottom: 1rem; font-size: 1.4rem;">Related Resources</h2>
        <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1rem;">
{cards}
        </div>
    </section>
'''

CARD_TEMPLATE = '''            <a href="{url}" style="display: block; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 1rem 1.25rem; text-decoration: none; transition: border-color 0.2s, background 0.2s;">
                <div style="font-weight: 600; color: #e4e4e7; margin-bottom: 0.25rem;">{title}</div>
                <div style="color: #9ca3af; font-size: 0.9rem;">{desc}</div>
            </a>'''


def add_crosslinks(filepath, data):
    """Add callout and related resources to a blog post."""
    with open(filepath, 'r') as f:
        content = f.read()

    modified = False

    # Add callout box if not already present
    if "callout" in data and "Try it yourself" not in content and "Keep this handy" not in content and "Quick reference:" not in content and "Build your cron" not in content and "Practice as you learn" not in content and "Optimize your CSS" not in content:
        callout_html = f'\n        <div class="tool-callout" {CALLOUT_STYLE}>\n            <strong style="color: #3b82f6;">&#9881; Try it:</strong> {data["callout"]["text"]}\n        </div>\n'

        # Find a good insertion point - after the first <p> tag in the article/main content
        # Look for the second </p> after the article starts
        article_match = re.search(r'(<article|<main|<div class="(blog|article|content))', content)
        if article_match:
            # Find the 2nd paragraph end after the article start
            pos = article_match.start()
            p_count = 0
            search_pos = pos
            while p_count < 2:
                p_end = content.find('</p>', search_pos)
                if p_end == -1:
                    break
                p_count += 1
                search_pos = p_end + 4
            if p_count >= 2:
                content = content[:search_pos] + callout_html + content[search_pos:]
                modified = True
                print(f"  Added callout to {os.path.basename(filepath)}")

    # Add related resources section if not already present
    if "related" in data:
        has_related_section = 'Related Resources</h2>' in content
        if not has_related_section:
            cards = ""
            for url, title, desc in data["related"]:
                cards += CARD_TEMPLATE.format(url=url, title=title, desc=desc) + "\n"
            related_html = RELATED_SECTION_TEMPLATE.format(cards=cards)

            # Insert before the footer
            footer_pos = content.find('    <footer>')
            if footer_pos == -1:
                footer_pos = content.find('<footer>')
            if footer_pos != -1:
                content = content[:footer_pos] + related_html + '\n' + content[footer_pos:]
                modified = True
                print(f"  Added related resources to {os.path.basename(filepath)}")

    if modified:
        with open(filepath, 'w') as f:
            f.write(content)
        return True
    else:
        print(f"  SKIP (already has cross-links): {os.path.basename(filepath)}")
        return False


def main():
    count = 0
    for filename, data in BLOG_DATA.items():
        filepath = os.path.join(BLOG_DIR, filename)
        if os.path.exists(filepath):
            if add_crosslinks(filepath, data):
                count += 1
        else:
            print(f"  NOT FOUND: {filepath}")

    print(f"\nDone! Updated {count} blog posts with cross-links.")


if __name__ == '__main__':
    main()
