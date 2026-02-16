#!/usr/bin/env python3
"""Generate OG images for new content in session 31."""
from PIL import Image, ImageDraw, ImageFont
import os

OG_DIR = "/var/www/web-ceo/og"
os.makedirs(OG_DIR, exist_ok=True)

# New content for this session
pages = [
    ("blog-fastapi-complete-guide", "FastAPI\nComplete Guide"),
    ("blog-sqlalchemy-complete-guide", "SQLAlchemy\nComplete Guide"),
    ("blog-vue3-complete-guide", "Vue 3\nComplete Guide"),
    ("blog-css-scroll-animations-guide", "CSS Scroll\nAnimations Guide"),
    ("blog-git-stash-complete-guide", "Git Stash\nComplete Guide"),
    ("tool-json-path-tester", "JSON Path\nTester"),
    ("tools-json-path-tester", "JSON Path\nTester"),
    ("tool-css-keyframe-animator", "CSS Keyframe\nAnimator"),
    ("tools-css-keyframe-animator", "CSS Keyframe\nAnimator"),
]

def create_og_image(filename, title_text):
    img = Image.new('RGB', (1200, 630), color=(19, 20, 26))
    draw = ImageDraw.Draw(img)

    # Border
    draw.rectangle([0, 0, 1199, 629], outline=(59, 130, 246), width=3)

    # Top accent bar
    draw.rectangle([0, 0, 1200, 6], fill=(59, 130, 246))

    # Try to use a nice font, fall back to default
    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 64)
        brand_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
        sub_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
    except:
        title_font = ImageFont.load_default()
        brand_font = ImageFont.load_default()
        sub_font = ImageFont.load_default()

    # Brand name
    draw.text((60, 40), "{ } DevToolbox", fill=(59, 130, 246), font=brand_font)

    # Title
    lines = title_text.split('\n')
    y = 180
    for line in lines:
        draw.text((60, y), line, fill=(228, 228, 231), font=title_font)
        y += 80

    # Bottom tagline
    draw.text((60, 540), "devtoolbox.dedyn.io", fill=(156, 163, 175), font=sub_font)

    filepath = os.path.join(OG_DIR, f"{filename}.png")
    img.save(filepath, "PNG", optimize=True)
    print(f"  Created: {filepath}")

print("Generating OG images...")
for filename, title in pages:
    create_og_image(filename, title)

print(f"\nDone! Generated {len(pages)} OG images.")
