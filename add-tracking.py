#!/usr/bin/env python3
"""Add track.js to all tool pages that don't have it yet."""
import os
import glob

TRACK_TAG = '<script src="/js/track.js"></script>'
tool_dir = '/var/www/web-ceo/tools'
count = 0

for filepath in sorted(glob.glob(os.path.join(tool_dir, '*.html'))):
    basename = os.path.basename(filepath)
    if basename == 'index.html':
        continue

    with open(filepath, 'r') as f:
        content = f.read()

    if '/js/track.js' in content:
        continue

    # Add before </body>
    if '</body>' in content:
        content = content.replace('</body>', f'{TRACK_TAG}\n</body>')
        with open(filepath, 'w') as f:
            f.write(content)
        count += 1
        print(f'  Added tracking to {basename}')

print(f'\nDone. Updated {count} files.')
