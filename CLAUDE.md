# Tempo Lab: notes for AI assistants working in this repo

Static GitHub Pages site (`docs/`) built by Python (`build_site.py`), plus README posters (`readme_art/make_art.py`).
No framework, no bundler, no chart library. Each `NN_*/build.py` writes its data as JSON into its `page.html` via `lab.py`.

## Design rules (the site must not look machine-made)

- **Type:** Schibsted Grotesk for headlines, numbers, labels and controls; Newsreader (serif) for reading text only.
  Never Inter, Space Grotesk, Barlow, or monospace labels.
- **Case:** sentence case everywhere. No `text-transform: uppercase`, no letter-spaced (tracked) small caps labels.
- **No eyebrows:** no kicker line above a page title or section heading, and no numbered section labels (01 · …).
  Sections are marked only by the Tempo "speed lines" before each `h2` (in `docs/assets/site.css`).
- **No accent rails:** no coloured top/left border on cards, tiles or sections. Panels are plain.
- **Headline numbers** use the box-score row (`.stat-row`): figures between thin rules, not cards.
- **Headlines** are plain, specific statements of what the chart shows ("Toronto was last in four defensive
  categories"). No slogans, no "X. Y." pairs, no "not X but Y", no colon-then-reveal.
- **Colour:** tokens only (`--tor`, `--tor-2`, `--gs`, `--por`, `--good`/`--bad`, `--hot`/`--cold`), defined in light and
  dark. Team colours identify teams; good/bad and hot/cold are separate and never reused for a team.
- **Facts:** every number in copy is computed from the data in the page script, or checked against the data before
  it is typed. Don't invent context (contracts, lottery odds, injuries) that the data doesn't contain.

## Before calling a change done

1. `.venv/bin/python build_site.py` (add `--shots` if a page's look changed).
2. Syntax-check every page script with `node --check` (extract the inline `<script>` blocks).
3. Render each page at 1280px and 400px wide and check nothing sticks out of its panel and the page never scrolls
   sideways (wide grids may scroll inside their own `.heat-wrap` / `.gg-wrap` / `.tbl-wrap`).
4. Look at a screenshot of anything you changed.

## Code style

Plain, student-style comments on every block (what it does and why, in simple words). Match the existing files.
Commits are authored by jordanngo205 only, with no AI attribution lines.
