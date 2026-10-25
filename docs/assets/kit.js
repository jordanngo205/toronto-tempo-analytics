/* Tempo Lab chart kit: tiny SVG helpers shared by every page. No dependencies. */
// Every page loads this file first. It puts all the helpers on one object, window.K,
// so the page scripts can write K.el(...), K.scale(...) and so on.
(function () {
  // SVG elements have to be created with this "namespace" or the browser won't draw them
  const NS = "http://www.w3.org/2000/svg";
  const K = {};
  // team colours (the real values live in site.css so dark mode can change them)
  K.TEAM = { TOR: "var(--tor)", GS: "var(--gs)", POR: "var(--por)" };
  // path to a team's logo, e.g. "TOR" -> ../assets/logos/tor_sm.png
  K.LOGO = ab => `../assets/logos/${String(ab).toLowerCase()}_sm.png`;
  // same thing but as an <img> tag ready to drop into HTML
  K.logo = (ab, cls = "logo") => `<img class="${cls}" src="${K.LOGO(ab)}" alt="${ab} logo" loading="lazy">`;

  // make an SVG element, set its attributes, and (optionally) add it to a parent
  // example: K.el("circle", { cx: 10, cy: 10, r: 5 }, svg)
  K.el = function (tag, attrs = {}, parent) {
    const n = document.createElementNS(NS, tag);
    // skip attributes that are undefined/null so I can pass "maybe" values
    for (const [k, v] of Object.entries(attrs)) if (v !== undefined && v !== null) n.setAttribute(k, v);
    if (parent) parent.appendChild(n);
    return n;
  };
  // add a text label to an SVG (cls is the CSS class, "lbl" = small grey label)
  K.txt = function (parent, x, y, s, cls = "lbl", extra = {}) {
    const t = K.el("text", { x, y, class: cls, ...extra }, parent);
    t.textContent = s;
    return t;
  };
  // linear scale: turns a data value into a pixel position
  // K.scale(0, 100, 50, 550) maps 0 -> 50px and 100 -> 550px
  K.scale = (d0, d1, r0, r1) => v => r0 + (v - d0) / (d1 - d0) * (r1 - r0);
  // keep a number between a and b
  K.clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  // number with a + or − sign, e.g. 3.2 -> "+3.2" (uses a real minus sign, not a hyphen)
  K.fmt = (v, d = 1) => v == null || isNaN(v) ? "–" : (v > 0 ? "+" : v < 0 ? "−" : "") + Math.abs(v).toFixed(d);
  // 0.456 -> "45.6%"
  K.pct = (v, d = 1) => v == null || isNaN(v) ? "–" : (100 * v).toFixed(d) + "%";
  // where the mouse is inside an SVG, in the SVG's own units (not screen pixels)
  // needed because the SVGs stretch to fit the screen
  K.svgPoint = function (svg, ev, W) {
    const r = svg.getBoundingClientRect();
    const vb = svg.viewBox.baseVal;
    return { x: (ev.clientX - r.left) * vb.width / r.width, y: (ev.clientY - r.top) * vb.height / r.height };
  };

  // tooltip
  // every page has one <div id="tip">, I just move it to the mouse and change its text
  let tip;
  K.tip = function (html, ev) {
    if (!tip) { tip = document.getElementById("tip"); }
    tip.innerHTML = html;
    tip.style.opacity = 1;
    // put it bottom-right of the mouse, but flip it if it would go off the screen
    const x = Math.min(ev.clientX + 14, window.innerWidth - tip.offsetWidth - 8);
    const y = ev.clientY + 14 + tip.offsetHeight > window.innerHeight ? ev.clientY - tip.offsetHeight - 10 : ev.clientY + 14;
    tip.style.left = Math.max(8, x) + "px";
    tip.style.top = y + "px";
  };
  K.hide = () => { if (tip) tip.style.opacity = 0; };
  // show a tooltip while the mouse is over a shape. html can be text or a function that makes text
  K.hover = function (node, html) {
    node.addEventListener("pointermove", ev => K.tip(typeof html === "function" ? html() : html, ev));
    node.addEventListener("pointerleave", K.hide);
  };

  // diverging colour between two CSS colours through --mid; t in [-1, 1]
  // t = -1 is fully the "neg" colour, 0 is the grey middle, +1 is fully the "pos" colour
  K.div = function (t, neg = "var(--cold)", pos = "var(--hot)") {
    t = K.clamp(t, -1, 1);
    const c = t >= 0 ? pos : neg;
    // color-mix lets CSS blend two colours, so it still works when dark mode swaps the variables
    return `color-mix(in oklab, ${c} ${Math.round(Math.abs(t) * 100)}%, var(--mid))`;
  };
  // one-colour scale from light grey (t = 0) to the full colour (t = 1)
  K.seq = function (t, c = "var(--tor)") {
    return `color-mix(in oklab, ${c} ${Math.round(K.clamp(t, 0, 1) * 100)}%, var(--grid))`;
  };

  // half court, 10 px per foot, basket near the top; returns {X, Y, g}
  // X() and Y() turn court feet into SVG pixels so pages can place shots
  K.court = function (svg, opts = {}) {
    // Y0 = the baseline is 5.25 ft behind the basket, depth = how much of the court to show
    const S = 10, Y0 = 5.25, depth = opts.depth || 29;
    const X = v => v * S, Y = v => (v + Y0) * S;
    svg.setAttribute("viewBox", `0 0 500 ${Math.round(Y(depth))}`);
    const g = K.el("g", {}, svg);
    // outline
    K.el("rect", { x: 0, y: 0, width: 500, height: Y(depth), class: "court-line", style: "opacity:.35" }, g);
    // the paint (16 ft wide, free throw line 13.75 ft from the basket)
    K.el("rect", { x: X(17), y: 0, width: X(16), height: Y(13.75), class: "court-line" }, g);
    // free throw circle (top half)
    K.el("path", { d: `M ${X(19)} ${Y(13.75)} A ${6 * S} ${6 * S} 0 0 0 ${X(31)} ${Y(13.75)}`, class: "court-line" }, g);
    // backboard and rim
    K.el("line", { x1: X(22), x2: X(28), y1: Y(-1.25), y2: Y(-1.25), class: "court-line", style: "stroke-width:2" }, g);
    K.el("circle", { cx: X(25), cy: Y(0), r: 0.75 * S, class: "court-line" }, g);
    // restricted area arc (4 ft)
    K.el("path", { d: `M ${X(21)} ${Y(0)} A ${4 * S} ${4 * S} 0 0 0 ${X(29)} ${Y(0)}`, class: "court-line", style: "opacity:.4" }, g);
    // three-point line: straight corners, then an arc of radius 22.15 ft
    // c3 = how far left/right of the basket the arc meets the corner lines (3 ft up from the basket)
    const c3 = Math.sqrt(22.15 ** 2 - 9);
    K.el("path", { d: `M ${X(25 - c3)} 0 L ${X(25 - c3)} ${Y(3)} A ${22.15 * S} ${22.15 * S} 0 0 0 ${X(25 + c3)} ${Y(3)} L ${X(25 + c3)} 0`, class: "court-line" }, g);
    return { X, Y, g, S };
  };
  // a small fixed "random" nudge in feet (-0.45 to +0.45) for shot number i.
  // ESPN rounds shot locations to whole feet, which makes dots line up in a grid; this spreads them out
  // the same way every time the page loads
  K.wiggle = i => { const v = Math.sin(i * 12.9898) * 43758.5453; return (v - Math.floor(v) - 0.5) * 0.9; };

  // full court on a dark background (the "every shot" look), 10 px per foot.
  // Toronto attacks the RIGHT basket, opponents attack the LEFT one.
  // Returns place(x, y, side): turns a shot's ESPN location (x = 0-50 ft across, y = feet out from
  // the basket) into a point on this court. side 0 = Tempo, side 1 = opponent.
  K.fullCourt = function (svg) {
    const k = 10, W = 94 * k, H = 50 * k;
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    const defs = K.el("defs", {}, svg);
    // soft glow for made shots
    const f = K.el("filter", { id: "glow", x: "-50%", y: "-50%", width: "200%", height: "200%" }, defs);
    K.el("feGaussianBlur", { stdDeviation: 4 }, f);
    K.el("rect", { x: 0, y: 0, width: W, height: H, fill: "#0d0b10" }, svg);
    const line = { fill: "none", stroke: "#ffffff", "stroke-opacity": 0.16, "stroke-width": 1.5 };
    K.el("rect", { x: 1, y: 1, width: W - 2, height: H - 2, ...line }, svg);
    K.el("line", { x1: W / 2, x2: W / 2, y1: 0, y2: H, ...line }, svg);
    K.el("circle", { cx: W / 2, cy: H / 2, r: 6 * k, ...line }, svg);
    const c3 = Math.sqrt(22.15 ** 2 - 9);
    for (const side of [0, 1]) {
      const bx = side === 0 ? 5.25 * k : W - 5.25 * k;   // basket x
      const edge = side === 0 ? 0 : W;                    // baseline x
      const d = side === 0 ? 1 : -1;                      // direction into the court
      K.el("rect", { x: Math.min(edge, edge + d * 19 * k), y: 17 * k, width: 19 * k, height: 16 * k, ...line }, svg);
      K.el("circle", { cx: bx, cy: 25 * k, r: 0.75 * k, ...line }, svg);
      K.el("path", { d: `M ${edge} ${(25 - c3) * k} L ${bx + d * 3 * k} ${(25 - c3) * k} A ${22.15 * k} ${22.15 * k} 0 0 ${side === 0 ? 1 : 0} ${bx + d * 3 * k} ${(25 + c3) * k} L ${edge} ${(25 + c3) * k}`, ...line }, svg);
    }
    const place = (x, y, side) => side === 0
      ? [(94 - 5.25 - y) * k, x * k]          // Tempo: distance from the right basket goes left
      : [(5.25 + y) * k, (50 - x) * k];       // opponent: distance from the left basket goes right
    return { place, W, H, k };
  };

  // the six corner points of a pointy-top hexagon centred at (cx, cy), as an SVG points string
  K.hexPts = (cx, cy, r) => Array.from({ length: 6 }, (_, i) => {
    const a = Math.PI / 180 * (60 * i - 90);
    return `${(cx + r * Math.cos(a)).toFixed(1)},${(cy + r * Math.sin(a)).toFixed(1)}`;
  }).join(" ");

  // readable names for the zone codes that the Python builds use
  K.ZONE = {
    "Rim": "At the rim (0–4 ft)", "Short": "Short paint (4–10 ft)", "Mid L": "Midrange, left", "Mid C": "Midrange, middle",
    "Mid R": "Midrange, right", "Corner3 L": "Left corner 3", "Corner3 R": "Right corner 3", "Arc3 L": "Left wing 3",
    "Arc3 C": "Top of the key 3", "Arc3 R": "Right wing 3",
  };

  // nudge text labels apart vertically: items {x, y, w}; mutates y
  // go from top to bottom, and if a label is too close to one above it, push it down
  K.declutter = function (items, h = 13) {
    items.sort((a, b) => a.y - b.y);
    for (let i = 1; i < items.length; i++) for (let j = 0; j < i; j++)
      if (Math.abs(items[i].x - items[j].x) < Math.max(items[i].w, items[j].w) && items[i].y - items[j].y < h) items[i].y = items[j].y + h;
    return items;
  };

  // a row of buttons where only one can be "on" at a time (like radio buttons)
  // each button has data-v="something", and onChange gets called with that value
  K.toggle = function (groupEl, onChange) {
    const btns = [...groupEl.querySelectorAll("button")];
    const set = v => { btns.forEach(b => b.setAttribute("aria-pressed", b.dataset.v === v)); onChange(v); };
    btns.forEach(b => b.addEventListener("click", () => set(b.dataset.v)));
    return set;
  };

  // make K available to the page scripts
  window.K = K;
})();
