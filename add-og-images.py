#!/usr/bin/env python3
"""Add og:image meta tags to all pages, referencing their OG images."""

import os
import re
from pathlib import Path

SITE_ROOT = Path("/var/www/web-ceo")
BASE_URL = "http://46.225.49.219"

def add_og_image(filepath, og_image_path):
    """Add og:image tag if missing."""
    content = filepath.read_text()
    if 'og:image' in content:
        return False

    # Add og:image after og:url or og:site_name
    if 'og:site_name' in content:
        content = content.replace(
            '<meta property="og:site_name" content="DevToolbox">',
            f'<meta property="og:site_name" content="DevToolbox">\n    <meta property="og:image" content="{BASE_URL}{og_image_path}">'
        )
    elif 'og:url' in content:
        # Find the og:url line and add after it
        content = re.sub(
            r'(<meta property="og:url" content="[^"]*">)',
            rf'\1\n    <meta property="og:image" content="{BASE_URL}{og_image_path}">',
            content
        )
    else:
        return False

    filepath.write_text(content)
    return True


def main():
    count = 0

    # Homepage
    f = SITE_ROOT / "index.html"
    if add_og_image(f, "/og/default.png"):
        print(f"  Added: index.html -> default.png")
        count += 1

    # Tool pages
    tools_dir = SITE_ROOT / "tools"
    for f in sorted(tools_dir.glob("*.html")):
        slug = f.stem
        if slug == "index":
            og_path = "/og/default.png"
        else:
            og_path = f"/og/tool-{slug}.png"
        if os.path.exists(SITE_ROOT / og_path.lstrip("/")):
            if add_og_image(f, og_path):
                print(f"  Added: tools/{slug} -> {og_path}")
                count += 1
        else:
            if add_og_image(f, "/og/default.png"):
                print(f"  Added: tools/{slug} -> default.png (fallback)")
                count += 1

    # Cheatsheet pages
    cs_dir = SITE_ROOT / "cheatsheets"
    for f in sorted(cs_dir.glob("*.html")):
        slug = f.stem
        if slug == "index":
            og_path = "/og/default.png"
        else:
            og_path = f"/og/cs-{slug}.png"
        if os.path.exists(SITE_ROOT / og_path.lstrip("/")):
            if add_og_image(f, og_path):
                print(f"  Added: cheatsheets/{slug} -> {og_path}")
                count += 1
        else:
            if add_og_image(f, "/og/default.png"):
                print(f"  Added: cheatsheets/{slug} -> default.png (fallback)")
                count += 1

    # Blog pages
    blog_dir = SITE_ROOT / "blog"
    for f in sorted(blog_dir.glob("*.html")):
        slug = f.stem
        if slug == "index":
            og_path = "/og/default.png"
        else:
            og_path = f"/og/blog-{slug}.png"
        if os.path.exists(SITE_ROOT / og_path.lstrip("/")):
            if add_og_image(f, og_path):
                print(f"  Added: blog/{slug} -> {og_path}")
                count += 1
        else:
            if add_og_image(f, "/og/default.png"):
                print(f"  Added: blog/{slug} -> default.png (fallback)")
                count += 1

    print(f"\nDone! Added og:image to {count} pages")


if __name__ == "__main__":
    main()
