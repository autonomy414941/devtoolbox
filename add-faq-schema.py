#!/usr/bin/env python3
"""Add FAQ structured data (JSON-LD) to key DevToolbox pages for rich snippets in search results."""

import os
import re

# FAQ data for each tool/page
FAQS = {
    "/var/www/web-ceo/tools/json-formatter.html": [
        ("What is JSON formatting?", "JSON formatting (or beautifying) is the process of adding proper indentation, line breaks, and spacing to minified or poorly formatted JSON data, making it human-readable and easier to debug."),
        ("Is my data safe when using this JSON formatter?", "Yes, absolutely. This JSON formatter runs 100% in your browser using JavaScript. Your data never leaves your computer — nothing is sent to any server."),
        ("What's the difference between formatting and minifying JSON?", "Formatting adds whitespace, indentation, and line breaks for readability. Minifying removes all unnecessary whitespace to reduce file size, which is useful for production APIs and data transfer."),
        ("Can this tool validate JSON syntax?", "Yes. The formatter automatically validates your JSON and shows clear error messages with line numbers if there are syntax errors like missing commas, unclosed brackets, or invalid values."),
    ],
    "/var/www/web-ceo/tools/base64.html": [
        ("What is Base64 encoding?", "Base64 is a binary-to-text encoding scheme that represents binary data as ASCII characters. It's commonly used to embed images in HTML/CSS, encode email attachments, and transmit binary data over text-based protocols."),
        ("Is Base64 encoding the same as encryption?", "No. Base64 is an encoding, not encryption. It doesn't provide any security — anyone can decode Base64 data. It's used for data transport, not data protection."),
        ("Why does Base64 increase data size?", "Base64 encoding increases data size by approximately 33% because it represents every 3 bytes of binary data as 4 ASCII characters. This trade-off enables safe text-based transmission of binary data."),
    ],
    "/var/www/web-ceo/tools/regex-tester.html": [
        ("What is a regular expression (regex)?", "A regular expression is a sequence of characters that defines a search pattern. Regex is used for string matching, validation, search-and-replace, and data extraction in virtually every programming language."),
        ("What do regex flags like g, i, and m mean?", "The 'g' flag enables global matching (find all matches, not just the first). The 'i' flag makes matching case-insensitive. The 'm' flag enables multiline mode where ^ and $ match line starts/ends."),
        ("How do I match an email address with regex?", "A common email regex pattern is: ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$ — though perfect email validation with regex is extremely complex. For production use, consider using your language's built-in email validation."),
    ],
    "/var/www/web-ceo/tools/hash-generator.html": [
        ("What is a hash function?", "A hash function takes input data of any size and produces a fixed-size output (hash/digest). It's a one-way function — you can't reverse a hash to get the original data. Common uses include password storage, data integrity verification, and digital signatures."),
        ("What's the difference between MD5, SHA-1, and SHA-256?", "MD5 produces a 128-bit hash, SHA-1 produces 160-bit, and SHA-256 produces 256-bit. MD5 and SHA-1 are considered cryptographically broken and should not be used for security. SHA-256 is currently the standard for secure hashing."),
        ("Can two different inputs produce the same hash?", "Yes, this is called a 'collision.' While theoretically possible for any hash function, modern algorithms like SHA-256 make collisions practically impossible to find intentionally."),
    ],
    "/var/www/web-ceo/tools/jwt-decoder.html": [
        ("What is a JWT (JSON Web Token)?", "A JWT is a compact, URL-safe token format used for authentication and information exchange. It consists of three parts: a header (algorithm info), a payload (claims/data), and a signature for verification."),
        ("Is it safe to decode JWTs in the browser?", "Yes, decoding a JWT only reveals its contents — it doesn't validate or forge tokens. The signature verification requires the secret key, which this tool doesn't need. This tool runs entirely in your browser."),
        ("Do JWTs expire?", "JWTs can include an 'exp' (expiration) claim that specifies when the token becomes invalid. This is set by the token issuer and is a Unix timestamp. Our decoder shows this expiration time in human-readable format."),
    ],
    "/var/www/web-ceo/tools/timestamp.html": [
        ("What is a Unix timestamp?", "A Unix timestamp (also called Epoch time) is the number of seconds that have elapsed since January 1, 1970, 00:00:00 UTC. It's a standard way to represent time in computing, used by most programming languages and databases."),
        ("Why do developers use Unix timestamps?", "Unix timestamps are timezone-independent, easy to store (just a number), simple to compare, and universally supported across programming languages and systems. They avoid timezone confusion in distributed systems."),
        ("What is the Year 2038 problem?", "The Year 2038 problem occurs because 32-bit systems store Unix timestamps as signed 32-bit integers, which will overflow on January 19, 2038. Most modern systems use 64-bit timestamps, which won't overflow for billions of years."),
    ],
    "/var/www/web-ceo/tools/url-encode.html": [
        ("What is URL encoding?", "URL encoding (percent-encoding) converts special characters into a format that can be safely transmitted in URLs. Characters like spaces, &, =, and non-ASCII characters are replaced with % followed by their hex value."),
        ("Why do URLs need encoding?", "URLs can only contain certain ASCII characters. Special characters like spaces, quotes, and non-English characters must be encoded to be valid in URLs. Without encoding, browsers and servers may misinterpret the URL."),
        ("What's the difference between encodeURI and encodeURIComponent?", "encodeURI encodes a full URI but preserves characters like :, /, ?, and # that have special meaning in URLs. encodeURIComponent encodes everything except letters, digits, and - _ . ~ — use it for encoding individual parameter values."),
    ],
    "/var/www/web-ceo/tools/color-picker.html": [
        ("What are HEX, RGB, and HSL color formats?", "HEX uses hexadecimal (#FF0000 for red). RGB uses red/green/blue values 0-255 (rgb(255,0,0)). HSL uses hue (0-360°), saturation (0-100%), and lightness (0-100%). Each format represents the same colors differently."),
        ("How do I choose accessible color combinations?", "Ensure a contrast ratio of at least 4.5:1 for normal text and 3:1 for large text (WCAG AA). Use our color picker to compare foreground and background colors. Dark text on light backgrounds or vice versa typically works best."),
    ],
    "/var/www/web-ceo/tools/diff-checker.html": [
        ("What is a diff checker?", "A diff checker compares two texts and highlights the differences between them. It shows added, removed, and modified lines — similar to how Git shows code changes. It's essential for code review, document comparison, and debugging."),
        ("How does text diffing work?", "Text diff algorithms (like the Myers diff algorithm) find the longest common subsequence between two texts, then identify the minimum set of changes (insertions and deletions) needed to transform one text into the other."),
    ],
    "/var/www/web-ceo/tools/uuid-generator.html": [
        ("What is a UUID?", "A UUID (Universally Unique Identifier) is a 128-bit identifier that is unique across space and time. UUIDs are used as database primary keys, session IDs, and anywhere a unique identifier is needed without a central authority."),
        ("What's the difference between UUID v1 and v4?", "UUID v1 is generated from the current timestamp and MAC address — it's sequential but reveals machine identity. UUID v4 is randomly generated and is the most commonly used version because it doesn't expose any information."),
        ("Can two UUIDs ever be the same?", "While theoretically possible, the probability is astronomically low. With UUID v4, you'd need to generate about 2.71 quintillion UUIDs to have a 50% chance of a single collision."),
    ],
    "/var/www/web-ceo/tools/password-generator.html": [
        ("What makes a password strong?", "A strong password is at least 12-16 characters long and includes a mix of uppercase letters, lowercase letters, numbers, and special characters. It should not contain dictionary words, personal information, or common patterns."),
        ("How does a password generator work?", "Password generators use cryptographically secure random number generators (like the Web Crypto API) to select characters randomly from the allowed character sets, ensuring truly unpredictable passwords."),
        ("Are generated passwords safe to use?", "Yes, passwords generated in your browser using the Web Crypto API are cryptographically secure. This tool runs entirely client-side — no passwords are sent to any server or stored anywhere."),
    ],
    "/var/www/web-ceo/tools/qr-code-generator.html": [
        ("What is a QR code?", "A QR (Quick Response) code is a two-dimensional barcode that stores data in a matrix of black and white squares. It can encode URLs, text, contact information, Wi-Fi credentials, and more, readable by smartphone cameras."),
        ("How much data can a QR code hold?", "A QR code can store up to 7,089 numeric characters, 4,296 alphanumeric characters, or 2,953 bytes of binary data. Practically, keeping content under 300 characters ensures reliable scanning."),
    ],
}

def create_faq_jsonld(faqs):
    """Create FAQ structured data JSON-LD."""
    items = []
    for i, (question, answer) in enumerate(faqs):
        items.append(f'''        {{
            "@type": "Question",
            "name": "{question}",
            "acceptedAnswer": {{
                "@type": "Answer",
                "text": "{answer}"
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
