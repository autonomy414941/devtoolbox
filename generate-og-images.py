#!/usr/bin/env python3
"""Generate Open Graph images for DevToolbox pages."""

from PIL import Image, ImageDraw, ImageFont
import os

OUTPUT_DIR = "/var/www/web-ceo/og"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# OG image dimensions (1200x630 is the standard)
WIDTH = 1200
HEIGHT = 630

# Colors matching the dark theme
BG_COLOR = (15, 17, 23)       # #0f1117
SURFACE = (26, 29, 39)        # #1a1d27
PRIMARY = (59, 130, 246)      # #3b82f6
ACCENT = (16, 185, 129)       # #10b981
TEXT = (228, 228, 231)         # #e4e4e7
MUTED = (156, 163, 175)       # #9ca3af
BORDER = (42, 46, 58)         # #2a2e3a

def get_font(size):
    """Get a font, falling back to default."""
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    for path in font_paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()

def get_regular_font(size):
    """Get a regular weight font."""
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for path in font_paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()

def get_mono_font(size):
    """Get a monospace font."""
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    ]
    for path in font_paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def create_og_image(title, subtitle, category, filename):
    """Create a branded OG image."""
    img = Image.new('RGB', (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Draw gradient-like accent bar at top
    for i in range(6):
        alpha = 1.0 - (i / 6)
        color = tuple(int(c * alpha + BG_COLOR[j] * (1 - alpha)) for j, c in enumerate(PRIMARY))
        draw.rectangle([0, i, WIDTH, i + 1], fill=color)

    # Draw border rectangle
    draw.rectangle([40, 40, WIDTH - 40, HEIGHT - 40], outline=BORDER, width=2)

    # Draw inner surface
    draw.rectangle([42, 42, WIDTH - 42, HEIGHT - 42], fill=SURFACE)

    # Logo area
    mono_font = get_mono_font(24)
    draw.rounded_rectangle([70, 70, 130, 105], radius=4, fill=PRIMARY)
    draw.text((78, 72), "{ }", fill=(255, 255, 255), font=mono_font)

    brand_font = get_font(28)
    draw.text((145, 72), "DevToolbox", fill=TEXT, font=brand_font)

    # Category badge
    if category:
        cat_font = get_regular_font(18)
        bbox = draw.textbbox((0, 0), category, font=cat_font)
        cat_w = bbox[2] - bbox[0] + 24
        cat_x = WIDTH - 42 - cat_w - 30
        draw.rounded_rectangle([cat_x, 70, cat_x + cat_w, 100], radius=12, fill=PRIMARY)
        draw.text((cat_x + 12, 73), category, fill=(255, 255, 255), font=cat_font)

    # Main title - wrap if needed
    title_font = get_font(48)
    # Simple word wrap
    words = title.split()
    lines = []
    current_line = ""
    for word in words:
        test = current_line + " " + word if current_line else word
        bbox = draw.textbbox((0, 0), test, font=title_font)
        if bbox[2] - bbox[0] > WIDTH - 180:
            if current_line:
                lines.append(current_line)
            current_line = word
        else:
            current_line = test
    if current_line:
        lines.append(current_line)

    y = 180
    for line in lines[:3]:  # Max 3 lines
        draw.text((70, y), line, fill=TEXT, font=title_font)
        y += 60

    # Subtitle
    if subtitle:
        sub_font = get_regular_font(24)
        draw.text((70, y + 20), subtitle, fill=MUTED, font=sub_font)

    # Bottom accent line
    draw.rectangle([42, HEIGHT - 80, WIDTH - 42, HEIGHT - 78], fill=PRIMARY)

    # Bottom text
    bottom_font = get_regular_font(18)
    draw.text((70, HEIGHT - 68), "Free  •  Private  •  No Signup", fill=MUTED, font=bottom_font)
    draw.text((WIDTH - 280, HEIGHT - 68), "devtoolbox.dev", fill=PRIMARY, font=bottom_font)

    img.save(os.path.join(OUTPUT_DIR, filename), "PNG", optimize=True)


def main():
    print("Generating OG images...")

    # Default/homepage OG image
    create_og_image(
        "Developer Tools That Just Work",
        "38 free tools, 14 cheat sheets, 9 blog posts",
        "",
        "default.png"
    )
    print("  default.png")

    # Tool pages
    tools = {
        "json-formatter": ("JSON Formatter & Validator", "Format, validate, and beautify JSON data"),
        "base64": ("Base64 Encoder / Decoder", "Encode and decode Base64 data"),
        "regex-tester": ("Regex Tester", "Test regular expressions in real-time"),
        "sql-formatter": ("SQL Formatter", "Format and beautify SQL queries"),
        "css-gradient": ("CSS Gradient Generator", "Create beautiful gradients visually"),
        "json-path-finder": ("JSON Path Finder", "Find and extract JSON paths visually"),
        "image-to-base64": ("Image to Base64 Encoder", "Convert images to data URIs"),
        "html-beautifier": ("HTML Beautifier", "Format and indent HTML code"),
        "js-minifier": ("JavaScript Minifier", "Minify and compress JavaScript code"),
        "yaml-validator": ("YAML Validator", "Validate and format YAML documents"),
        "jwt-decoder": ("JWT Decoder", "Decode and inspect JSON Web Tokens"),
        "hash-generator": ("Hash Generator", "Generate MD5, SHA-1, SHA-256 hashes"),
        "color-picker": ("Color Picker & Converter", "Pick colors and convert formats"),
        "diff-checker": ("Diff Checker", "Compare two texts side by side"),
        "uuid-generator": ("UUID Generator", "Generate random UUIDs/GUIDs"),
        "qr-code-generator": ("QR Code Generator", "Generate QR codes from text"),
        "password-generator": ("Password Generator", "Generate secure passwords"),
        "timestamp": ("Unix Timestamp Converter", "Convert timestamps and dates"),
        "cron-parser": ("Cron Expression Parser", "Parse and explain cron schedules"),
        "url-encode": ("URL Encoder / Decoder", "Encode and decode URLs"),
        "css-minifier": ("CSS Minifier", "Minify and compress CSS code"),
        "markdown-preview": ("Markdown Preview", "Preview Markdown with live rendering"),
        "html-entity": ("HTML Entity Encoder", "Encode and decode HTML entities"),
        "json-to-csv": ("JSON to CSV Converter", "Convert JSON data to CSV"),
        "json-schema-validator": ("JSON Schema Validator", "Validate JSON against schemas"),
        "number-base-converter": ("Number Base Converter", "Convert binary, octal, hex"),
        "ip-lookup": ("IP Address Lookup", "Look up IP information"),
        "text-case-converter": ("Text Case Converter", "Convert text between cases"),
        "lorem-ipsum": ("Lorem Ipsum Generator", "Generate placeholder text"),
        "http-tester": ("HTTP Request Tester", "Send HTTP requests like a mini Postman"),
        "code-screenshot": ("Code Screenshot Generator", "Beautiful code screenshots with themes"),
        "ascii-art": ("ASCII Art Text Generator", "Turn text into ASCII art with FIGlet fonts"),
        "json-diff": ("JSON Diff & Compare", "Deep compare two JSON objects"),
        "regex-debugger": ("Regex Debugger & Visualizer", "Debug regex with match highlighting"),
        "box-shadow": ("CSS Box Shadow Generator", "Visual box-shadow editor with presets"),
        "markdown-table": ("Markdown Table Generator", "Create Markdown tables visually"),
        "jwt-generator": ("JWT Generator", "Create and sign JSON Web Tokens"),
        "chmod-calculator": ("Chmod Calculator", "Calculate Linux file permissions"),
    }

    for slug, (title, subtitle) in tools.items():
        create_og_image(title, subtitle, "TOOL", f"tool-{slug}.png")
        print(f"  tool-{slug}.png")

    # Cheatsheet pages
    cheatsheets = {
        "http-status-codes": "HTTP Status Codes",
        "git-commands": "Git Commands",
        "css-flexbox": "CSS Flexbox",
        "css-grid": "CSS Grid",
        "docker-commands": "Docker Commands",
        "sql-basics": "SQL Basics",
        "bash-shortcuts": "Bash Shortcuts",
        "vim-shortcuts": "Vim Shortcuts",
        "linux-permissions": "Linux Permissions",
        "python-string-methods": "Python String Methods",
        "javascript-array-methods": "JavaScript Array Methods",
        "kubernetes-commands": "Kubernetes Commands",
        "typescript-types": "TypeScript Types",
        "react-hooks": "React Hooks",
    }

    for slug, title in cheatsheets.items():
        create_og_image(f"{title} Cheat Sheet", "Quick reference for developers", "CHEAT SHEET", f"cs-{slug}.png")
        print(f"  cs-{slug}.png")

    # Blog posts
    blogs = {
        "json-api-debugging-tips": "10 JSON API Debugging Tips",
        "regex-guide-for-beginners": "Regex Guide for Beginners",
        "http-status-codes-explained": "HTTP Status Codes Explained",
        "cron-job-schedule-guide": "Cron Job Scheduling Guide",
        "css-performance-optimization": "CSS Performance Optimization",
        "git-commands-every-developer-should-know": "25 Git Commands You Should Know",
        "javascript-array-methods-complete-guide": "JavaScript Array Methods Guide",
        "docker-containers-beginners-guide": "Docker Containers for Beginners",
        "typescript-tips-and-tricks": "15 TypeScript Tips and Tricks",
    }

    for slug, title in blogs.items():
        create_og_image(title, "Developer tutorial and guide", "BLOG", f"blog-{slug}.png")
        print(f"  blog-{slug}.png")

    print(f"\nDone! Generated {len(tools) + len(cheatsheets) + len(blogs) + 1} OG images in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
