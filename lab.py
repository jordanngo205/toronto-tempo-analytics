"""Builds the GitHub Pages site in docs/: shared head, nav and footer around each page's own markup."""
import json
from pathlib import Path

ROOT = Path(__file__).parent
DOCS = ROOT / "docs"  # GitHub Pages serves the site from this folder

# every page on the site: (folder name in the URL, text in the nav bar)
PAGES = [  # slug, nav label
    ("expansion-class", "Expansion Class"),
    ("shot-lab", "Shot Lab"),
    ("rotation-lab", "Rotation Lab"),
    ("game-flow", "Game Flow"),
    ("game-center", "Game Center"),
    ("draft-lab", "Draft Lab"),
    ("posters", "Posters"),
]
# the live site's address (link previews need a full URL for the picture)
SITE = "https://jordanngo205.github.io/toronto-tempo-analytics/"
# Google Fonts link: Barlow Condensed for headings, Barlow for text, IBM Plex Mono for numbers
FONTS = ("https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700;800"
         "&family=Barlow:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap")


def version(path):
    """Short fingerprint of a file's contents. Added to asset links (site.css?v=...) so browsers fetch
    the new file as soon as it changes instead of mixing a new page with an old cached stylesheet or script."""
    import hashlib
    return hashlib.md5((DOCS / path).read_bytes()).hexdigest()[:8]


def versioned(html):
    # add the fingerprint to the shared script tag every page uses
    return html.replace('src="../assets/kit.js"', f'src="../assets/kit.js?v={version("assets/kit.js")}"')


def head(title, description, prefix="../"):
    # the top of every html page. prefix is how to get back to docs/ from the page
    # (pages live one folder down, so "../"; the home page is in docs/ itself, so "")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{title}</title>
<meta name="description" content="{description}">
<!-- link previews (Slack, iMessage, X, LinkedIn...): title, description and the social card picture -->
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:image" content="{SITE}assets/social.png">
<meta property="og:type" content="website">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="{prefix}assets/logos/tor_sm.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="{FONTS}">
<link rel="stylesheet" href="{prefix}assets/site.css?v={version("assets/site.css")}">
"""


def nav(current, prefix="../"):
    # the nav bar. The current page gets aria-current="page" so the CSS can underline it
    links = "".join(
        f'<a href="{prefix}{slug}/"{" aria-current=\"page\"" if slug == current else ""}>{label}</a>'
        for slug, label in PAGES)
    return (f'<nav class="nav" aria-label="Tempo Lab"><a class="brand" href="{prefix}">'
            f'<img src="{prefix}assets/logos/tor_sm.png" alt="">Tempo Lab</a><div class="links">{links}</div></nav>')


# same footer on every page (pages put <!--FOOTER--> where it should go)
FOOTER = ('<footer class="footer"><span>Built by Jordan Ngo with sportsdataverse (ESPN play-by-play, box scores, WNBA Stats).</span>'
          '<a href="https://github.com/jordanngo205/toronto-tempo-analytics">Code on GitHub</a>'
          '<span>Inspired by Rise of the Valkyries and Neil Paine.</span></footer>')


def summary(slug, values):
    """Headline numbers for the landing page, merged into docs/assets/summary.json."""
    f = DOCS / "assets" / "summary.json"
    # read what other pages already saved, add/replace this page's numbers, write it back
    allv = json.loads(f.read_text()) if f.exists() else {}
    allv[slug] = values
    f.write_text(json.dumps(allv, indent=1, default=float))


def write_home(page_file, data):
    """docs/index.html: the Tempo Lab landing page."""
    body = Path(page_file).read_text()
    # home.html starts with its own <style> block; split it off so it can go in the <head>
    style, rest = body.split("</style>", 1)
    # turn the data into JSON. "</" is escaped so a string can never close the <script> tag early
    payload = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    html = (head("Tempo Lab", "Toronto Tempo analytics: expansion-year Elo, shot charts, rotations, game flow and recaps for every 2026 game.", prefix="")
            + style + "</style>\n</head>\n<body>\n<div class=\"wrap\">\n" + nav(None, prefix="") + "\n"
            + rest.replace("/*DATA*/", payload).replace("<!--FOOTER-->", FOOTER) + "\n</div>\n</body>\n</html>\n")
    out = DOCS / "index.html"
    out.write_text(versioned(html))
    print("wrote", out.relative_to(ROOT))


def write_page(slug, title, description, page_file, data):
    """page_file holds the page's <style>, markup and <script>; /*DATA*/ is replaced with JSON."""
    body = Path(page_file).read_text()
    # all the numbers the page needs, as compact JSON (escaped the same way as write_home)
    payload = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    # if the page starts with a <style> block, move it into the <head>
    style, rest = "", body
    if body.lstrip().startswith("<style>"):
        style, rest = body.split("</style>", 1)
        style += "</style>\n"
    # glue it all together: head + styles + nav + page content (with data and footer filled in)
    html = (head(title, description) + style + "</head>\n<body>\n<div class=\"wrap\">\n" + nav(slug) + "\n"
            + rest.replace("/*DATA*/", payload).replace("<!--FOOTER-->", FOOTER)
            + "\n</div>\n</body>\n</html>\n")
    # the page's tooltip div and scripts end up inside <div class="wrap">, which browsers are fine with
    # each page gets its own folder so the URL is nice, e.g. /shot-lab/
    out = DOCS / slug / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(versioned(html))
    print("wrote", out.relative_to(ROOT), f"{out.stat().st_size // 1024} KB")
    return out
