#!/usr/bin/env python3
"""Add FAQ structured data (JSON-LD) to the remaining 23 DevToolbox tool pages."""

import os
import re
import json

# FAQ data for each remaining tool page (23 pages without FAQ)
FAQS = {
    "/var/www/web-ceo/tools/ascii-art.html": [
        ("What is ASCII art?", "ASCII art is a form of visual art created using printable characters from the ASCII character set. It originated in the early days of computing when graphics capabilities were limited, and text characters were used to create images and decorative text."),
        ("What is FIGlet?", "FIGlet is a program that generates text banners in large letters made up of smaller ASCII characters. Each font defines how letters are drawn using patterns of characters, creating distinctive stylized text perfect for terminal headers and README files."),
        ("How can I use ASCII art text in my projects?", "ASCII art text is commonly used in command-line tool headers, code comment blocks, README files, terminal splash screens, and email signatures. Simply copy the generated text and paste it where needed, wrapping it in a code block or pre tag for proper formatting."),
    ],
    "/var/www/web-ceo/tools/box-shadow.html": [
        ("What is CSS box-shadow?", "CSS box-shadow adds shadow effects around an element's frame. It takes values for horizontal offset, vertical offset, blur radius, spread radius, and color. Multiple shadows can be applied to create complex depth effects like Material Design elevation."),
        ("What is neumorphism?", "Neumorphism (or soft UI) is a design style that combines background colors with box shadows to create soft, extruded shapes. It uses two shadows — a light one and a dark one — to create the illusion of elements pushing out from the background."),
        ("Can I use multiple box shadows on one element?", "Yes, CSS supports multiple box shadows separated by commas. This allows you to create complex effects like layered depth, inner glows combined with outer shadows, or realistic material shadows with multiple light sources."),
    ],
    "/var/www/web-ceo/tools/code-screenshot.html": [
        ("Why use code screenshots instead of text?", "Code screenshots preserve syntax highlighting, fonts, and formatting exactly as intended. They're ideal for social media posts, presentations, documentation, and tutorials where you want code to look polished and consistent across all devices."),
        ("What image format are the screenshots?", "This tool exports code screenshots as PNG files at 2x resolution (retina quality) for crisp text rendering on high-DPI displays. PNG is ideal for code screenshots because it uses lossless compression, keeping text sharp."),
        ("Can I customize the appearance?", "Yes, you can choose from multiple themes (dark, light, colorful), change the background gradient, select different programming languages for syntax highlighting, and toggle window chrome (the macOS-style title bar with colored dots)."),
    ],
    "/var/www/web-ceo/tools/cron-parser.html": [
        ("What is a cron expression?", "A cron expression is a string of five or six fields separated by spaces that defines a schedule for recurring tasks. The fields represent minute, hour, day of month, month, and day of week. Cron is used in Unix/Linux systems and many scheduling services."),
        ("What does the asterisk (*) mean in cron?", "The asterisk means 'every' or 'any value' for that field. For example, * in the minute field means 'every minute,' and * in the day-of-week field means 'every day.' It's the most common wildcard in cron expressions."),
        ("How do I schedule a cron job to run every 5 minutes?", "Use the expression */5 * * * * — the /5 means 'every 5th value.' This pattern works for any interval: */15 for every 15 minutes, */2 for every 2 hours (in the hour field), etc."),
    ],
    "/var/www/web-ceo/tools/css-gradient.html": [
        ("What is a CSS gradient?", "A CSS gradient is a smooth transition between two or more colors, created purely with CSS — no images needed. CSS supports linear gradients (along a straight line), radial gradients (from a center point), and conic gradients (around a center point)."),
        ("What's the difference between linear and radial gradients?", "Linear gradients transition colors along a straight line at a specified angle (e.g., left to right, top to bottom, or diagonal). Radial gradients transition colors outward from a center point in a circular or elliptical shape."),
        ("Can I use gradients as backgrounds in all browsers?", "Yes, CSS gradients are supported in all modern browsers including Chrome, Firefox, Safari, and Edge. The standard syntax (linear-gradient, radial-gradient) works without vendor prefixes in all current browser versions."),
    ],
    "/var/www/web-ceo/tools/css-minifier.html": [
        ("What is CSS minification?", "CSS minification removes unnecessary characters from CSS code — whitespace, comments, newlines, and redundant semicolons — without changing functionality. This reduces file size, leading to faster page loads and less bandwidth usage."),
        ("How much can CSS minification reduce file size?", "Typical CSS minification reduces file size by 15-30%, depending on coding style. Well-commented code with lots of whitespace sees larger reductions. Combined with gzip compression, total transfer size can be reduced by 70-90%."),
        ("Does minification affect CSS functionality?", "No, minified CSS is functionally identical to the original. Only non-essential characters are removed. The browser interprets both versions exactly the same way. You should keep the original source files and only serve minified versions in production."),
    ],
    "/var/www/web-ceo/tools/html-beautifier.html": [
        ("What is HTML beautification?", "HTML beautification (or formatting) adds proper indentation, line breaks, and consistent spacing to HTML code. This makes the code more readable and easier to maintain, without changing how the browser renders the page."),
        ("Does beautifying HTML change how the page looks?", "In most cases, no. Beautification only adds whitespace between tags, which browsers typically ignore for rendering. However, in elements where whitespace matters (like pre tags or inline elements), formatting could potentially affect display."),
        ("What indentation style should I use for HTML?", "The most common styles are 2 spaces and 4 spaces per indent level. Two spaces is popular in web development communities and keeps deeply nested HTML more compact. Choose whichever your team prefers and be consistent."),
    ],
    "/var/www/web-ceo/tools/html-entity.html": [
        ("What are HTML entities?", "HTML entities are special codes used to display reserved characters in HTML. Since characters like <, >, and & have special meaning in HTML, you must use entities (like &lt;, &gt;, &amp;) to display them as literal text on a web page."),
        ("When should I use HTML entities?", "Use HTML entities when displaying reserved HTML characters (<, >, &, quotes) in page content, when including special symbols (©, ™, →), and when displaying characters not available on your keyboard. They ensure correct rendering across all browsers."),
        ("What's the difference between named and numeric entities?", "Named entities use descriptive names (like &amp; for &), while numeric entities use character codes (like &#38;). Named entities are easier to read but not all characters have names. Numeric entities work for any Unicode character."),
    ],
    "/var/www/web-ceo/tools/http-tester.html": [
        ("What is an HTTP request tester?", "An HTTP request tester lets you send HTTP requests (GET, POST, PUT, DELETE, etc.) to any URL and inspect the response. It's like a simplified version of tools like Postman or curl, useful for testing APIs and debugging web services."),
        ("What are HTTP methods?", "HTTP methods indicate the desired action on a resource. GET retrieves data, POST submits data, PUT updates/replaces data, PATCH partially updates data, DELETE removes data, HEAD gets headers only, and OPTIONS checks available methods."),
        ("What is the difference between PUT and PATCH?", "PUT replaces an entire resource with the provided data — you must send all fields. PATCH applies partial modifications — you only send the fields you want to change. PATCH is more efficient for small updates to large resources."),
    ],
    "/var/www/web-ceo/tools/image-to-base64.html": [
        ("Why convert images to Base64?", "Base64-encoded images can be embedded directly in HTML or CSS, eliminating extra HTTP requests. This is useful for small images like icons, logos, and UI elements. It simplifies deployment since everything is in one file."),
        ("Does Base64 encoding increase image size?", "Yes, Base64 encoding increases data size by approximately 33%. However, when gzip compression is applied (standard on web servers), the actual transfer size difference is much smaller, often just 5-10% larger."),
        ("When should I NOT use Base64 images?", "Avoid Base64 for large images (over 10KB) as it increases HTML/CSS file size, prevents browser caching of individual images, and blocks page rendering. Use regular image files for photos and large graphics, and Base64 only for small icons and sprites."),
    ],
    "/var/www/web-ceo/tools/ip-lookup.html": [
        ("What is an IP address?", "An IP (Internet Protocol) address is a unique numerical label assigned to each device connected to a network. IPv4 addresses use four numbers (0-255) separated by dots (like 192.168.1.1), while IPv6 uses eight groups of hexadecimal numbers."),
        ("What is a subnet mask?", "A subnet mask divides an IP address into network and host portions. For example, 255.255.255.0 (/24) means the first 24 bits identify the network, leaving 8 bits (256 addresses) for hosts. Subnet masks enable efficient network management and routing."),
        ("What's the difference between public and private IP addresses?", "Public IP addresses are globally unique and routable on the internet. Private IPs (10.x.x.x, 172.16-31.x.x, 192.168.x.x) are used within local networks and aren't directly reachable from the internet. NAT translates between them."),
    ],
    "/var/www/web-ceo/tools/js-minifier.html": [
        ("What is JavaScript minification?", "JavaScript minification removes unnecessary characters like whitespace, comments, and newlines from code without changing its functionality. It reduces file size for faster downloads, improving page load speed and user experience."),
        ("How much does JS minification save?", "JavaScript minification typically reduces file size by 20-40%. Combined with gzip compression, total savings can reach 60-80%. For large applications with many JavaScript files, this translates to significantly faster page loads."),
        ("Should I minify JavaScript in development?", "No, keep your source code readable during development and only minify for production builds. Most build tools (Webpack, Vite, esbuild) handle minification automatically as part of the production build process."),
    ],
    "/var/www/web-ceo/tools/json-diff.html": [
        ("What is JSON diffing?", "JSON diffing compares two JSON documents and identifies the differences between them — added keys, removed keys, and changed values. It performs deep recursive comparison, checking nested objects and arrays at every level."),
        ("How is JSON diff different from text diff?", "Text diff compares line by line, while JSON diff understands data structure. It can detect that two JSON documents with different formatting but identical data are equal, and it reports changes by their JSON path (like $.user.name) rather than line numbers."),
        ("Can JSON diff compare arrays?", "Yes, JSON diff compares arrays element by element at each index position. It detects added, removed, and modified elements. Note that JSON arrays are ordered, so the same elements in a different order will show as differences."),
    ],
    "/var/www/web-ceo/tools/json-path-finder.html": [
        ("What is a JSON path?", "A JSON path is a string expression that identifies a specific value within a JSON document. It uses dot notation ($.user.name) or bracket notation ($['user']['name']) to navigate through nested objects and arrays to locate data."),
        ("What's the difference between dot and bracket notation?", "Dot notation ($.user.name) is more concise and readable for simple keys. Bracket notation ($['user']['name']) is required for keys containing spaces, special characters, or when using array indices like $['items'][0]."),
        ("How do I access array elements in JSON paths?", "Use bracket notation with a zero-based index: $.items[0] gets the first element, $.items[1] the second, etc. Some implementations support wildcards ($.items[*]) to select all elements or filters ($.items[?(@.price > 10)])."),
    ],
    "/var/www/web-ceo/tools/json-schema-validator.html": [
        ("What is JSON Schema?", "JSON Schema is a vocabulary for annotating and validating JSON documents. It defines the expected structure, data types, required fields, value constraints, and patterns for JSON data. It's widely used for API validation and configuration files."),
        ("Why use JSON Schema validation?", "JSON Schema validates data before processing it, catching errors early. It ensures API request/response payloads match expected formats, validates configuration files, generates documentation, and enables IDE autocompletion for JSON files."),
        ("What validation rules does JSON Schema support?", "JSON Schema supports type checking (string, number, boolean, object, array, null), required fields, min/max values, string patterns (regex), enum values, array constraints (minItems, maxItems, uniqueItems), and nested object validation."),
    ],
    "/var/www/web-ceo/tools/json-to-csv.html": [
        ("What is JSON to CSV conversion?", "JSON to CSV conversion transforms structured JSON data into a flat, comma-separated values format suitable for spreadsheets and databases. Nested JSON objects are flattened by joining key names, and arrays are expanded into separate rows or columns."),
        ("When would I convert JSON to CSV?", "Common use cases include importing API data into spreadsheets (Excel, Google Sheets), preparing data for database imports, creating reports from JSON APIs, and sharing data with non-technical users who prefer tabular formats."),
        ("How are nested JSON objects handled?", "Nested objects are flattened using dot notation for column headers. For example, {\"user\": {\"name\": \"John\"}} becomes a column named 'user.name' with value 'John'. Arrays may be expanded into multiple rows or joined as comma-separated values."),
    ],
    "/var/www/web-ceo/tools/lorem-ipsum.html": [
        ("What is Lorem Ipsum?", "Lorem Ipsum is placeholder text used in design and typesetting since the 1500s. It's based on a scrambled passage from Cicero's 'De Finibus Bonorum et Malorum' (45 BC). It provides natural-looking text for layouts without distracting with readable content."),
        ("Why use Lorem Ipsum instead of real text?", "Lorem Ipsum prevents reviewers from focusing on content instead of design. Its letter distribution is similar to English, giving a realistic appearance. It comes in standard lengths, making it easy to fill layouts consistently during the design process."),
        ("Can I generate Lorem Ipsum in different amounts?", "Yes, this generator lets you create Lorem Ipsum in paragraphs, sentences, or words. You can specify exactly how much text you need, from a single sentence to many paragraphs, perfect for filling any design mockup or prototype."),
    ],
    "/var/www/web-ceo/tools/markdown-preview.html": [
        ("What is Markdown?", "Markdown is a lightweight markup language that uses simple text formatting syntax to create rich documents. Created by John Gruber in 2004, it's used for README files, documentation, blog posts, comments, and messaging. It converts easily to HTML."),
        ("What Markdown features does this tool support?", "This preview supports standard Markdown including headings, bold, italic, links, images, code blocks with syntax highlighting, tables, blockquotes, ordered and unordered lists, horizontal rules, and inline code."),
        ("Where is Markdown commonly used?", "Markdown is used on GitHub (README files, issues, PRs), Stack Overflow, Reddit, Discord, Slack, documentation sites, static site generators (Jekyll, Hugo), note-taking apps (Obsidian, Notion), and blogging platforms (Ghost, DEV.to)."),
    ],
    "/var/www/web-ceo/tools/number-base-converter.html": [
        ("What are number bases?", "A number base (or radix) determines how many digits are used to represent numbers. Decimal (base 10) uses 0-9, binary (base 2) uses 0-1, octal (base 8) uses 0-7, and hexadecimal (base 16) uses 0-9 and A-F."),
        ("Why do computers use binary?", "Computers use binary because electronic circuits have two states: on (1) and off (0). All data — numbers, text, images, programs — is ultimately stored and processed as sequences of binary digits (bits). Higher bases like hex are shorthand for binary."),
        ("When do programmers use hexadecimal?", "Hexadecimal is commonly used for memory addresses, color codes (#FF0000), byte values, MAC addresses, Unicode code points, and assembly language. Each hex digit represents exactly 4 binary bits, making it a compact way to express binary data."),
    ],
    "/var/www/web-ceo/tools/regex-debugger.html": [
        ("What is regex debugging?", "Regex debugging is the process of testing and understanding how a regular expression matches against input text. A debugger highlights matches, shows capture groups, and explains what each part of the pattern does, making complex regex easier to develop."),
        ("What are capture groups in regex?", "Capture groups, defined by parentheses (), save the matched text for later reference. For example, (\\d{3})-(\\d{4}) matching '555-1234' creates group 1 ('555') and group 2 ('1234'). They're used for extraction and backreferences."),
        ("How do I make a regex case-insensitive?", "Add the 'i' flag after your regex pattern. In most languages: /pattern/i in JavaScript, re.IGNORECASE in Python, Pattern.CASE_INSENSITIVE in Java, and (?i) inline flag in most regex engines."),
    ],
    "/var/www/web-ceo/tools/sql-formatter.html": [
        ("What is SQL formatting?", "SQL formatting adds proper indentation, line breaks, and consistent capitalization to SQL queries. It transforms hard-to-read single-line queries into well-structured, readable code — essential for maintaining complex database queries."),
        ("Should SQL keywords be uppercase?", "Uppercase SQL keywords (SELECT, FROM, WHERE, JOIN) is a widely followed convention that improves readability by visually distinguishing keywords from table/column names. Most style guides recommend it, though SQL itself is case-insensitive."),
        ("Does formatting change how SQL executes?", "No, SQL formatting is purely cosmetic. Adding whitespace, newlines, and changing keyword case doesn't affect query execution or performance. The database engine ignores all formatting when parsing and executing queries."),
    ],
    "/var/www/web-ceo/tools/text-case-converter.html": [
        ("What are the common text case formats?", "Common formats include UPPERCASE, lowercase, Title Case, camelCase, PascalCase, snake_case, kebab-case, CONSTANT_CASE, dot.case, and Sentence case. Each has specific uses in programming, writing, and naming conventions."),
        ("When should I use camelCase vs snake_case?", "camelCase is standard in JavaScript, Java, and C# for variables and functions. snake_case is preferred in Python, Ruby, and Rust. Use whatever convention your language or project follows for consistency."),
        ("What is kebab-case used for?", "kebab-case (words-separated-by-hyphens) is used for CSS class names, HTML attributes, URL slugs, file names, and CLI flags. It's readable, URL-safe, and the standard naming convention in web development for CSS and HTML."),
    ],
    "/var/www/web-ceo/tools/yaml-validator.html": [
        ("What is YAML?", "YAML (YAML Ain't Markup Language) is a human-readable data serialization format. It uses indentation to represent structure, making it cleaner than JSON for configuration files. It's used by Docker Compose, Kubernetes, Ansible, GitHub Actions, and many other tools."),
        ("What's the difference between YAML and JSON?", "YAML uses indentation for nesting (no braces), supports comments, allows multiline strings, and is more human-readable. JSON uses explicit braces and brackets, has no comments, and is more machine-friendly. YAML is a superset of JSON — valid JSON is valid YAML."),
        ("What are common YAML mistakes?", "Common errors include inconsistent indentation (mixing tabs and spaces), missing colons after keys, incorrect list formatting (forgetting the dash), unquoted strings that look like numbers or booleans, and using tabs instead of spaces (YAML only allows spaces)."),
    ],
}


def create_faq_jsonld(faqs):
    """Create FAQ structured data JSON-LD."""
    items = []
    for i, (question, answer) in enumerate(faqs):
        # Escape quotes in JSON
        q = question.replace('"', '\\"')
        a = answer.replace('"', '\\"')
        items.append(f'''        {{
            "@type": "Question",
            "name": "{q}",
            "acceptedAnswer": {{
                "@type": "Answer",
                "text": "{a}"
            }}
        }}''')

    return '''    <script type="application/ld+json">
    {{
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
{}
        ]
    }}
    </script>'''.format(',\n'.join(items))


def add_faq_to_page(filepath, faqs):
    """Add FAQ JSON-LD and visible FAQ section to a page."""
    with open(filepath, 'r') as f:
        content = f.read()

    # Skip if already has FAQ schema
    if '"FAQPage"' in content:
        print(f"  SKIP (already has FAQ): {filepath}")
        return False

    # Add JSON-LD before </head>
    faq_jsonld = create_faq_jsonld(faqs)
    content = content.replace('</head>', faq_jsonld + '\n</head>')

    # Add visible FAQ section before the footer
    faq_html = '\n    <section class="faq-section" style="max-width: 800px; margin: 2rem auto; padding: 0 1rem;">\n'
    faq_html += '        <h2 style="margin-bottom: 1.5rem;">Frequently Asked Questions</h2>\n'
    for question, answer in faqs:
        faq_html += f'''        <details class="faq-item" style="margin-bottom: 0.75rem; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 0;">
            <summary style="padding: 1rem 1.25rem; cursor: pointer; font-weight: 500; color: #e0e0e0; list-style: none; display: flex; justify-content: space-between; align-items: center;">{question}<span style="transition: transform 0.2s; color: #3b82f6;">&#9660;</span></summary>
            <div style="padding: 0 1.25rem 1rem; color: #a0a0a0; line-height: 1.7;">{answer}</div>
        </details>\n'''
    faq_html += '    </section>\n'

    # Insert before footer
    content = content.replace('    <footer>', faq_html + '    <footer>')

    with open(filepath, 'w') as f:
        f.write(content)

    print(f"  ADDED FAQ ({len(faqs)} questions): {filepath}")
    return True


def main():
    count = 0
    for filepath, faqs in FAQS.items():
        if os.path.exists(filepath):
            if add_faq_to_page(filepath, faqs):
                count += 1
        else:
            print(f"  NOT FOUND: {filepath}")

    print(f"\nDone! Added FAQ schema to {count} pages.")


if __name__ == '__main__':
    main()
