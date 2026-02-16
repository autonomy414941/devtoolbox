#!/usr/bin/env python3
"""Add keyboard shortcuts to DevToolbox tool pages.
Adds Ctrl+Enter to run/format, Ctrl+Shift+C to copy output, and a help tooltip."""

import os
import re
import glob

TOOLS_DIR = "/var/www/web-ceo/tools"

# Keyboard shortcuts script to inject
SHORTCUTS_SCRIPT = '''
    <!-- Keyboard shortcuts -->
    <div id="kbd-toast" style="display:none;position:fixed;bottom:20px;right:20px;background:#3b82f6;color:#fff;padding:10px 20px;border-radius:8px;font-size:14px;z-index:9999;box-shadow:0 4px 12px rgba(0,0,0,0.3);transition:opacity 0.3s;"></div>
    <div id="kbd-help" style="position:fixed;bottom:20px;left:20px;z-index:9998;">
        <button onclick="this.nextElementSibling.style.display=this.nextElementSibling.style.display==='block'?'none':'block'" style="background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.2);color:#a0a0a0;padding:6px 12px;border-radius:6px;cursor:pointer;font-size:12px;" title="Keyboard shortcuts">&#9000; Shortcuts</button>
        <div style="display:none;position:absolute;bottom:40px;left:0;background:#1a1a2e;border:1px solid rgba(255,255,255,0.15);border-radius:8px;padding:12px 16px;min-width:220px;box-shadow:0 8px 24px rgba(0,0,0,0.4);">
            <div style="font-weight:600;margin-bottom:8px;color:#e0e0e0;font-size:13px;">Keyboard Shortcuts</div>
            <div style="color:#a0a0a0;font-size:12px;line-height:2;">
                <kbd style="background:#2a2a4a;padding:2px 6px;border-radius:3px;font-size:11px;">Ctrl</kbd>+<kbd style="background:#2a2a4a;padding:2px 6px;border-radius:3px;font-size:11px;">Enter</kbd> Run / Format<br>
                <kbd style="background:#2a2a4a;padding:2px 6px;border-radius:3px;font-size:11px;">Ctrl</kbd>+<kbd style="background:#2a2a4a;padding:2px 6px;border-radius:3px;font-size:11px;">Shift</kbd>+<kbd style="background:#2a2a4a;padding:2px 6px;border-radius:3px;font-size:11px;">C</kbd> Copy output<br>
                <kbd style="background:#2a2a4a;padding:2px 6px;border-radius:3px;font-size:11px;">Ctrl</kbd>+<kbd style="background:#2a2a4a;padding:2px 6px;border-radius:3px;font-size:11px;">L</kbd> Clear
            </div>
        </div>
    </div>
    <script>
    (function(){
        function showToast(msg){var t=document.getElementById('kbd-toast');if(!t)return;t.textContent=msg;t.style.display='block';t.style.opacity='1';setTimeout(function(){t.style.opacity='0';setTimeout(function(){t.style.display='none';},300);},1500);}
        document.addEventListener('keydown',function(e){
            if(e.ctrlKey&&e.key==='Enter'){
                e.preventDefault();
                var btn=document.querySelector('.btn-primary')||document.querySelector('button[onclick*="format"]')||document.querySelector('button[onclick*="generate"]')||document.querySelector('button[onclick*="convert"]')||document.querySelector('button[onclick*="encode"]')||document.querySelector('button[onclick*="decode"]')||document.querySelector('button[onclick*="validate"]')||document.querySelector('button[onclick*="check"]')||document.querySelector('button[onclick*="send"]');
                if(btn){btn.click();showToast('Executed!');}
            }
            if(e.ctrlKey&&e.shiftKey&&e.key==='C'){
                e.preventDefault();
                var out=document.getElementById('output')||document.querySelector('.code-output')||document.querySelector('#result')||document.querySelector('[id*="output"]');
                if(out){var txt=out.textContent||out.innerText;if(txt){navigator.clipboard.writeText(txt);showToast('Copied to clipboard!');}}
            }
            if(e.ctrlKey&&e.key==='l'&&!e.shiftKey){
                e.preventDefault();
                var clrBtn=document.querySelector('button[onclick*="clear"]')||document.querySelector('button[onclick*="Clear"]');
                if(clrBtn){clrBtn.click();showToast('Cleared!');}
            }
        });
    })();
    </script>
'''

def add_shortcuts_to_page(filepath):
    """Add keyboard shortcuts to a tool page."""
    with open(filepath, 'r') as f:
        content = f.read()

    # Skip if already has shortcuts
    if 'kbd-toast' in content:
        print(f"  SKIP (already has shortcuts): {os.path.basename(filepath)}")
        return False

    # Skip index pages
    if filepath.endswith('index.html'):
        print(f"  SKIP (index page): {os.path.basename(filepath)}")
        return False

    # Insert before </body>
    content = content.replace('</body>', SHORTCUTS_SCRIPT + '\n</body>')

    with open(filepath, 'w') as f:
        f.write(content)

    print(f"  ADDED shortcuts: {os.path.basename(filepath)}")
    return True

def main():
    count = 0
    for filepath in sorted(glob.glob(os.path.join(TOOLS_DIR, '*.html'))):
        if add_shortcuts_to_page(filepath):
            count += 1

    print(f"\nDone! Added keyboard shortcuts to {count} tool pages.")

if __name__ == '__main__':
    main()
