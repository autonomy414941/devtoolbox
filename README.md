# DevToolbox

Practical developer resources in a single static site:

- Browser tools (`python-formatter`, `json-formatter`, `mongodb-query-builder`, `pomodoro-timer`)
- Fast cheat sheets (`pandas`, `regex`, `redis`)
- Production-focused implementation guides (Git, Docker, Nginx, FastAPI, systemd, and more)

## Why This Repo

Most developer content is either too shallow or too long to use during real work.  
DevToolbox is optimized for "need it now" usage:

- direct examples
- copy/paste-friendly sections
- minimal setup (plain static HTML)

## Quick Start

```bash
git clone https://github.com/autonomy414941/devtoolbox.git
cd devtoolbox
python3 -m http.server 8000
```

Then open `http://localhost:8000`.

## Repository Layout

- `index.html`: generated landing page with search and categorized resource cards
- `*.html`: tools, cheat sheets, and long-form guides
- `generate-index.py`: rebuilds `index.html` from page metadata
- `generate-sitemap.py`: sitemap generation script used in deployment workflow
- `check-internal-links.py`: link integrity checker against a running site

## Add a New Page

1. Add a new `*.html` file with:
   - `<title>...</title>`
   - `<meta name="description" content="...">`
2. Rebuild the landing page:

```bash
./generate-index.py
```

3. Commit and push.

## Maintenance Commands

```bash
# Regenerate landing page
./generate-index.py

# Validate Python scripts
python3 -m py_compile generate-index.py generate-sitemap.py check-internal-links.py

# Verify internal anchors against a local preview
python3 -m http.server 8000
python3 check-internal-links.py --site-root . --base-url http://127.0.0.1:8000
```

## License

[MIT](LICENSE)
