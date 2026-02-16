#!/usr/bin/env python3
"""Generate 10 missing OG images for DevToolbox."""

from PIL import Image, ImageDraw, ImageFont
import os

# Colors (dark theme)
BG_COLOR = (15, 17, 23)
SURFACE = (26, 29, 39)
PRIMARY = (59, 130, 246)
ACCENT = (16, 185, 129)
TEXT = (228, 228, 231)
MUTED = (156, 163, 175)

# Image dimensions
WIDTH = 1200
HEIGHT = 630

# Fonts
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# Output directory
OUTPUT_DIR = "/var/www/web-ceo/og"

# Images to generate: (filename, title, subtitle)
IMAGES = [
    ("api.png", "API Documentation", "DevToolbox REST API"),
    ("json-validator.png", "JSON Validator", "Validate & Fix JSON"),
    ("json-viewer.png", "JSON Viewer", "Interactive Tree View"),
    ("tool-meta-tag-generator.png", "Meta Tag Generator", "SEO Meta Tags"),
    ("tool-placeholder-image.png", "Placeholder Image", "Generate Placeholders"),
    ("tool-slug-generator.png", "Slug Generator", "URL-Friendly Slugs"),
    ("tool-word-counter.png", "Word Counter", "Count Words & Characters"),
    ("xml-formatter.png", "XML Formatter", "Format & Beautify XML"),
    ("xml-json-converter.png", "XML \u2194 JSON", "Convert XML to JSON"),
    ("blog-essential-web-dev-tools-2026.png", "58+ Web Dev Tools", "Essential Free Tools for 2026"),
]


def generate_og_image(filename, title, subtitle):
    """Generate a single branded OG image."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Load fonts
    font_brand = ImageFont.truetype(FONT_BOLD, 28)
    font_title = ImageFont.truetype(FONT_BOLD, 56)
    font_subtitle = ImageFont.truetype(FONT_REGULAR, 30)
    font_url = ImageFont.truetype(FONT_REGULAR, 22)

    # --- Decorative accent bar at top ---
    draw.rectangle([0, 0, WIDTH, 6], fill=PRIMARY)

    # --- Surface card background (centered rounded rect area) ---
    card_margin_x = 60
    card_margin_top = 40
    card_margin_bottom = 40
    card_rect = [
        card_margin_x,
        card_margin_top,
        WIDTH - card_margin_x,
        HEIGHT - card_margin_bottom,
    ]
    # Draw rounded rectangle for card
    draw.rounded_rectangle(card_rect, radius=20, fill=SURFACE)

    # --- Accent line inside card (decorative left bar) ---
    accent_bar_x = card_margin_x + 30
    accent_bar_top = card_margin_top + 60
    accent_bar_bottom = HEIGHT - card_margin_bottom - 60
    draw.rectangle(
        [accent_bar_x, accent_bar_top, accent_bar_x + 4, accent_bar_bottom],
        fill=ACCENT,
    )

    # --- Brand text "DevToolbox" at top of card ---
    brand_text = "DevToolbox"
    brand_x = card_margin_x + 60
    brand_y = card_margin_top + 50
    draw.text((brand_x, brand_y), brand_text, fill=PRIMARY, font=font_brand)

    # Small dot separator after brand
    brand_bbox = draw.textbbox((brand_x, brand_y), brand_text, font=font_brand)
    dot_x = brand_bbox[2] + 15
    dot_y = brand_y + 10
    draw.ellipse([dot_x, dot_y, dot_x + 8, dot_y + 8], fill=ACCENT)

    # --- Tool title (large, centered vertically) ---
    title_x = brand_x
    title_y = brand_y + 100

    # Handle long titles: reduce font size if needed
    title_font = font_title
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    max_title_width = WIDTH - card_margin_x * 2 - 120
    if title_width > max_title_width:
        # Scale down
        scale = max_title_width / title_width
        new_size = max(36, int(56 * scale))
        title_font = ImageFont.truetype(FONT_BOLD, new_size)

    draw.text((title_x, title_y), title, fill=TEXT, font=title_font)

    # --- Subtitle (muted, below title) ---
    subtitle_y = title_y + 80
    draw.text((title_x, subtitle_y), subtitle, fill=MUTED, font=font_subtitle)

    # --- Horizontal rule ---
    rule_y = HEIGHT - card_margin_bottom - 80
    draw.rectangle(
        [brand_x, rule_y, WIDTH - card_margin_x - 60, rule_y + 1],
        fill=(50, 55, 70),
    )

    # --- URL at the bottom of card ---
    url_text = "devtoolbox.dedyn.io"
    url_bbox = draw.textbbox((0, 0), url_text, font=font_url)
    url_width = url_bbox[2] - url_bbox[0]
    url_x = WIDTH - card_margin_x - 60 - url_width
    url_y = rule_y + 15
    draw.text((url_x, url_y), url_text, fill=MUTED, font=font_url)

    # --- Small decorative circles (top right) ---
    for i, color in enumerate([PRIMARY, ACCENT, (99, 102, 241)]):
        cx = WIDTH - card_margin_x - 60 - i * 30
        cy = card_margin_top + 65
        draw.ellipse([cx - 8, cy - 8, cx + 8, cy + 8], fill=color)

    # Save
    output_path = os.path.join(OUTPUT_DIR, filename)
    img.save(output_path, "PNG", optimize=True)
    print(f"  Generated: {output_path}")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Generating {len(IMAGES)} OG images...\n")

    for filename, title, subtitle in IMAGES:
        generate_og_image(filename, title, subtitle)

    print(f"\nDone. {len(IMAGES)} images saved to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
