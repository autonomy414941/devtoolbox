#!/usr/bin/env python3
"""Generate OG images for session 37 content."""
from PIL import Image, ImageDraw, ImageFont
import os

OUTPUT_DIR = "/var/www/web-ceo/og"
os.makedirs(OUTPUT_DIR, exist_ok=True)

WIDTH = 1200
HEIGHT = 630

BG_COLOR = (15, 17, 23)
SURFACE = (26, 29, 39)
PRIMARY = (59, 130, 246)
TEXT = (228, 228, 231)
MUTED = (156, 163, 175)
BORDER = (42, 46, 58)

def get_font(size):
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]:
        if os.path.exists(p): return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def get_regular_font(size):
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
        if os.path.exists(p): return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def get_mono_font(size):
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"]:
        if os.path.exists(p): return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def create_og_image(title, subtitle, category, filename):
    img = Image.new('RGB', (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)
    for i in range(6):
        alpha = 1.0 - (i / 6)
        color = tuple(int(c * alpha + BG_COLOR[j] * (1 - alpha)) for j, c in enumerate(PRIMARY))
        draw.rectangle([0, i, WIDTH, i + 1], fill=color)
    draw.rectangle([40, 40, WIDTH - 40, HEIGHT - 40], outline=BORDER, width=2)
    draw.rectangle([42, 42, WIDTH - 42, HEIGHT - 42], fill=SURFACE)
    mono_font = get_mono_font(24)
    draw.rounded_rectangle([70, 70, 130, 105], radius=4, fill=PRIMARY)
    draw.text((78, 72), "{ }", fill=(255, 255, 255), font=mono_font)
    brand_font = get_font(28)
    draw.text((145, 72), "DevToolbox", fill=TEXT, font=brand_font)
    if category:
        cat_font = get_regular_font(18)
        bbox = draw.textbbox((0, 0), category, font=cat_font)
        cat_w = bbox[2] - bbox[0] + 24
        cat_x = WIDTH - 42 - cat_w - 30
        draw.rounded_rectangle([cat_x, 70, cat_x + cat_w, 100], radius=12, fill=PRIMARY)
        draw.text((cat_x + 12, 73), category, fill=(255, 255, 255), font=cat_font)
    title_font = get_font(48)
    words = title.split()
    lines, current_line = [], ""
    for word in words:
        test = current_line + " " + word if current_line else word
        bbox = draw.textbbox((0, 0), test, font=title_font)
        if bbox[2] - bbox[0] > WIDTH - 180:
            if current_line: lines.append(current_line)
            current_line = word
        else:
            current_line = test
    if current_line: lines.append(current_line)
    y = 180
    for line in lines[:3]:
        draw.text((70, y), line, fill=TEXT, font=title_font)
        y += 60
    if subtitle:
        sub_font = get_regular_font(24)
        draw.text((70, y + 20), subtitle, fill=MUTED, font=sub_font)
    draw.rectangle([42, HEIGHT - 80, WIDTH - 42, HEIGHT - 78], fill=PRIMARY)
    bottom_font = get_regular_font(18)
    draw.text((70, HEIGHT - 68), "Free  •  Private  •  No Signup", fill=MUTED, font=bottom_font)
    draw.text((WIDTH - 280, HEIGHT - 68), "devtoolbox.dev", fill=PRIMARY, font=bottom_font)
    img.save(os.path.join(OUTPUT_DIR, filename), "PNG", optimize=True)

# Blog posts - session 37
blogs = [
    ("Elasticsearch: The Complete Guide", "Master full-text search, aggregations, and cluster management", "Blog", "elasticsearch-complete-guide"),
    ("CSS @starting-style Guide", "Animate elements from display:none with pure CSS", "Blog", "css-starting-style-guide"),
    ("Python CLI with Click & Typer", "Build professional command-line tools in Python", "Blog", "python-click-typer-cli-guide"),
    ("Apache Kafka: The Complete Guide", "Event streaming, topics, partitions, and consumer groups", "Blog", "apache-kafka-complete-guide"),
    ("SQLite: The Complete Guide", "The most used database in the world, explained", "Blog", "sqlite-complete-guide"),
    ("Deno: The Complete Guide", "Modern JavaScript runtime with TypeScript built in", "Blog", "deno-complete-guide"),
]

tools = [
    ("Kafka Partition Calculator", "Calculate optimal partitions and storage", "Tool", "kafka-calculator"),
    ("SQLite Playground", "Run SQLite queries in your browser", "Tool", "sqlite-playground"),
    ("CSS @starting-style Generator", "Generate entry animations with @starting-style", "Tool", "css-starting-style-generator"),
]

print("Generating session 37 OG images...")
for title, subtitle, category, slug in blogs:
    fn = f"blog-{slug}.png"
    create_og_image(title, subtitle, category, fn)
    print(f"  {fn}")

for title, subtitle, category, slug in tools:
    # Create both tool-slug.png and tools-slug.png variants
    for prefix in ["tool", "tools"]:
        fn = f"{prefix}-{slug}.png"
        create_og_image(title, subtitle, category, fn)
        print(f"  {fn}")

print("Done!")
