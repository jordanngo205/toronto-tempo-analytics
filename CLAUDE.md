# Tempo Lab: notes for AI assistants working in this repo

Static GitHub Pages site (`docs/`) built by Python (`build_site.py`), plus README posters (`readme_art/make_art.py`).
No framework, no bundler, no chart library. Each `NN_*/build.py` writes its data as JSON into its `page.html` via `lab.py`.
Shared styles live in `docs/assets/site.css`, shared chart helpers in `docs/assets/kit.js`.

## Look and layout

- **Keep the established look.** Barlow Condensed caps headlines, Barlow body, IBM Plex Mono labels, Tempo bordeaux
  and navy. The owner prefers this; don't swap fonts or restyle to "look less AI". The anti-slop work is about layout.
- **Layout, not a template.** Don't stack heading → paragraph → boxed chart on repeat. On desktop each section puts its
  note in a sticky column beside the chart; sections with big grids or side-by-side panels use `class="section wide"`.
  The opening puts the title and intro beside a scoreboard list of key numbers (`.hero > .stat-row`).
- **Shot charts of many shots** use the white full court (`K.fullCourt` in kit.js), not a dark one: Tempo attack the
  right basket, opponents the left. Made shots are a solid dot with a soft glow in the team's colour (Tempo bordeaux;
  a Game Center opponent uses its own colour, with a fallback when ESPN's colour is too pale), misses are small grey
  dots, positions get `K.wiggle` jitter. Labels go above the court, never on top of the dots.
- **Draft scores** (talent, fit) are standard scores (50 = class average, 10 = one standard deviation), not percentiles,
  so big gaps at the top of the class stay visible.
- **Charts must be readable:** no labels on top of marks (use `K.declutter` or a key beside the chart), zoom axes to the
  data, and use a log scale when the interesting values bunch at one end.
- **Every abbreviation is explained** where it's used (BPM, TS%, Game Score…): a glossary, a caption or a header tooltip.
- **Headlines** say what the chart shows ("Toronto was last in four defensive categories"), not slogans.

## Facts

- Every number in copy is computed from the page's data in its script, or checked against the data before it's typed.
- Don't invent context the data doesn't contain. If something is missing (e.g. a player with no 2025-26 games), say
  that plainly rather than guessing why.
- Elo settings in `elo.py` were tuned on 2004–2023 and tested on 2024–2026. If you change them, re-run that test.

## Before calling a change done

1. `.venv/bin/python build_site.py --shots` and, if README numbers or art changed, `.venv/bin/python readme_art/make_art.py`.
2. Syntax-check every page script and `docs/assets/kit.js` with `node --check` (extract the inline `<script>` blocks).
3. Render every page at 1280px and at a real phone width. Headless Chrome won't lay out narrower than 500px, so load
   the page in a 390px-wide `<iframe>`. Check that no SVG mark or HTML text sticks out of its panel, no image is broken,
   there are no script errors, and the page never scrolls sideways (wide grids may scroll inside `.heat-wrap`,
   `.gg-wrap` or `.tbl-wrap`).
4. Check that no chart label sits on top of two or more dots/bars. Put axis labels above the plot area; labels that
   must sit among dots get `class="halo"`.
5. Recompute key numbers independently: box vs play-by-play finals, quarter margins summing to the final, plus-minus
   = 5 × team margin, stint minutes vs box minutes, Elo zero-sum and calibration, and every claim in the copy.
6. Look at a screenshot of anything you changed.
7. Never `git checkout --` or reset a path that has uncommitted edits.

## Code style

Plain, student-style comments on every block (what it does and why, in simple words). Match the existing files.
Commits are authored by jordanngo205 only, with no AI attribution lines. One logical change per commit.
