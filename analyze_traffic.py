#!/usr/bin/env python3
"""Analyze organic search traffic from nginx access logs."""
import re
import subprocess
from collections import Counter

referrers = Counter()
pages = Counter()
engines = Counter()
today_pages = Counter()

search_pattern = re.compile(r'(bing\.com|google\.com|duckduckgo|yahoo\.com|ecosia|qwant|aol\.com|brave|yandex)')


def read_log_lines(path: str):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.readlines()
    except PermissionError:
        try:
            output = subprocess.check_output(
                ["sudo", "-n", "cat", path],
                stderr=subprocess.STDOUT,
                text=True,
            )
            return output.splitlines(keepends=True)
        except Exception as e:
            raise RuntimeError(f"sudo read failed: {e}") from e

for i, logfile in enumerate(['/var/log/nginx/web-ceo.access.log', '/var/log/nginx/web-ceo.access.log.1']):
    try:
        for line in read_log_lines(logfile):
            parts = line.split('"')
            if len(parts) >= 4:
                ref = parts[3]
                if ref not in ('-', '') and ref.strip():
                    referrers[ref] += 1
                    if search_pattern.search(ref):
                        req = parts[1].split()[1] if len(parts[1].split()) > 1 else ''
                        pages[req] += 1
                        if i == 0:
                            today_pages[req] += 1
                        m = search_pattern.search(ref)
                        if m:
                            engines[m.group(1)] += 1
    except Exception as e:
        print(f"Error reading {logfile}: {e}")

print('=== SEARCH ENGINE REFERRALS (2-day) ===')
for eng, c in engines.most_common():
    print(f'  {eng}: {c}')
print(f'  TOTAL: {sum(engines.values())}')

print()
print('=== TOP PAGES BY ORGANIC REFERRALS (2-day) ===')
for page, c in pages.most_common(30):
    t = today_pages.get(page, 0)
    print(f'  {c:3d} (today:{t:2d})  {page}')

print()
print('=== ALL NON-EMPTY REFERRERS (2-day) ===')
for ref, c in referrers.most_common(30):
    print(f'  {c:3d}  {ref}')
