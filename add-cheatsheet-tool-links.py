#!/usr/bin/env python3
"""Add tool links to cheat sheet 'Related Resources' sections."""

import os

CS_DIR = "/var/www/web-ceo/cheatsheets"

# Map: cheatsheet filename -> tool links to add
TOOL_LINKS = {
    "bash-shortcuts.html": [
        ("/tools/cron-parser", "Cron Parser"),
        ("/tools/text-case-converter", "Text Case Converter"),
    ],
    "docker-commands.html": [
        ("/tools/yaml-validator", "YAML Validator"),
        ("/tools/json-formatter", "JSON Formatter"),
    ],
    "javascript-array-methods.html": [
        ("/tools/json-formatter", "JSON Formatter"),
        ("/tools/json-path-finder", "JSON Path Finder"),
    ],
    "linux-permissions.html": [
        ("/tools/number-base-converter", "Number Base Converter"),
    ],
    "typescript-types.html": [
        ("/tools/json-schema-validator", "JSON Schema Validator"),
        ("/tools/json-formatter", "JSON Formatter"),
    ],
    "vim-shortcuts.html": [
        ("/tools/regex-tester", "Regex Tester"),
        ("/tools/diff-checker", "Diff Checker"),
    ],
    "python-string-methods.html": [
        ("/tools/regex-tester", "Regex Tester"),
    ],
    "css-flexbox.html": [
        ("/tools/css-gradient", "CSS Gradient Generator"),
        ("/tools/box-shadow", "Box Shadow Generator"),
    ],
    "css-grid.html": [
        ("/tools/css-gradient", "CSS Gradient Generator"),
        ("/tools/css-minifier", "CSS Minifier"),
    ],
    "sql-basics.html": [
        ("/tools/sql-formatter", "SQL Formatter"),
        ("/tools/json-to-csv", "JSON to CSV Converter"),
    ],
    "http-status-codes.html": [
        ("/tools/http-tester", "HTTP Request Tester"),
    ],
    "git-commands.html": [
        ("/tools/diff-checker", "Diff Checker"),
    ],
    "react-hooks.html": [
        ("/tools/json-formatter", "JSON Formatter"),
    ],
    "kubernetes-commands.html": [
        ("/tools/yaml-validator", "YAML Validator"),
    ],
}


def add_tool_links(filepath, links):
    """Add tool card links to the Related Resources section."""
    with open(filepath, 'r') as f:
        content = f.read()

    added = 0
    for url, title in links:
        # Check if this link already exists
        if url in content:
            continue

        # Find the end of the Related Resources grid div
        # Look for </div> after "Related Resources"
        related_pos = content.find('Related Resources')
        if related_pos == -1:
            continue

        # Find the closing </div> of the grid
        grid_start = content.find('<div class="grid">', related_pos)
        if grid_start == -1:
            continue

        # Find the </div> that closes the grid
        grid_end = content.find('</div>', grid_start + 18)
        if grid_end == -1:
            continue

        # Insert new card before the closing </div>
        card = f'''        <a href="{url}" class="tool-card">
            <h3>{title}</h3>
        </a>
'''
        content = content[:grid_end] + card + content[grid_end:]
        added += 1

    if added > 0:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"  Added {added} tool links to {os.path.basename(filepath)}")
        return True
    else:
        print(f"  SKIP (already linked): {os.path.basename(filepath)}")
        return False


def main():
    count = 0
    for filename, links in TOOL_LINKS.items():
        filepath = os.path.join(CS_DIR, filename)
        if os.path.exists(filepath):
            if add_tool_links(filepath, links):
                count += 1
        else:
            print(f"  NOT FOUND: {filepath}")

    print(f"\nDone! Updated {count} cheat sheet pages with tool links.")


if __name__ == '__main__':
    main()
