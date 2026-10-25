"""Builds the GitHub Pages site in docs/: shared head, nav and footer around each page's own markup."""
import json
from pathlib import Path

ROOT = Path(__file__).parent
DOCS = ROOT / "docs"

PAGES = [  # slug, nav label
    ("expansion-class", "Expansion Class"),
    ("shot-lab", "Shot Lab"),
    ("rotation-lab", "Rotation Lab"),
    ("game-flow", "Game Flow"),
    ("game-center", "Game Center"),
]
FONTS = ("https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700;800"
         "&family=Barlow:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap")


def head(title, description, prefix="../"):
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{title}</title>
<meta name="description" content="{description}">
<link rel="icon" href="{prefix}assets/logos/tor_sm.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="{FONTS}">
<link rel="stylesheet" href="{prefix}assets/site.css">
"""


def nav(current, prefix="../"):
    links = "".join(
        f'<a href="{prefix}{slug}/"{" aria-current=\"page\"" if slug == current else ""}>{label}</a>'
        for slug, label in PAGES)
    return (f'<nav class="nav" aria-label="Tempo Lab"><a class="brand" href="{prefix}">'
            f'<img src="{prefix}assets/logos/tor_sm.png" alt="">Tempo Lab</a><div class="links">{links}</div></nav>')


FOOTER = ('<footer class="footer"><span>Built by Jordan Ngo with sportsdataverse (ESPN play-by-play, box scores, WNBA Stats).</span>'
          '<a href="https://github.com/jordanngo205/toronto-tempo-analytics">Code on GitHub</a>'
          '<span>Inspired by Rise of the Valkyries and Neil Paine.</span></footer>')


def summary(slug, values):
    """Headline numbers for the landing page, merged into docs/assets/summary.json."""
    f = DOCS / "assets" / "summary.json"
    allv = json.loads(f.read_text()) if f.exists() else {}
    allv[slug] = values
    f.write_text(json.dumps(allv, indent=1, default=float))


def write_home(page_file, data):
    """docs/index.html: the Tempo Lab landing page."""
    body = Path(page_file).read_text()
    style, rest = body.split("</style>", 1)
    payload = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    html = (head("Tempo Lab", "Toronto Tempo analytics: expansion-year Elo, shot charts, rotations, game flow and recaps for every 2026 game.", prefix="")
            + style + "</style>\n</head>\n<body>\n<div class=\"wrap\">\n" + nav(None, prefix="") + "\n"
            + rest.replace("/*DATA*/", payload).replace("<!--FOOTER-->", FOOTER) + "\n</div>\n</body>\n</html>\n")
    out = DOCS / "index.html"
    out.write_text(html)
    print("wrote", out.relative_to(ROOT))


def write_page(slug, title, description, page_file, data):
    """page_file holds the page's <style>, markup and <script>; /*DATA*/ is replaced with JSON."""
    body = Path(page_file).read_text()
    payload = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    style, rest = "", body
    if body.lstrip().startswith("<style>"):
        style, rest = body.split("</style>", 1)
        style += "</style>\n"
    html = (head(title, description) + style + "</head>\n<body>\n<div class=\"wrap\">\n" + nav(slug) + "\n"
            + rest.replace("/*DATA*/", payload).replace("<!--FOOTER-->", FOOTER)
            + "\n</div>\n</body>\n</html>\n")
    # page scripts sit inside .wrap in the source; move the tip + scripts after it is fine for browsers
    out = DOCS / slug / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)
    print("wrote", out.relative_to(ROOT), f"{out.stat().st_size // 1024} KB")
    return out
