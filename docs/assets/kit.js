/* Tempo Lab chart kit: tiny SVG helpers shared by every page. No dependencies. */
(function () {
  const NS = "http://www.w3.org/2000/svg";
  const K = {};
  K.TEAM = { TOR: "var(--tor)", GS: "var(--gs)", POR: "var(--por)" };
  K.LOGO = ab => `../assets/logos/${String(ab).toLowerCase()}_sm.png`;
  K.logo = (ab, cls = "logo") => `<img class="${cls}" src="${K.LOGO(ab)}" alt="${ab} logo" loading="lazy">`;

  K.el = function (tag, attrs = {}, parent) {
    const n = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs)) if (v !== undefined && v !== null) n.setAttribute(k, v);
    if (parent) parent.appendChild(n);
    return n;
  };
  K.txt = function (parent, x, y, s, cls = "lbl", extra = {}) {
    const t = K.el("text", { x, y, class: cls, ...extra }, parent);
    t.textContent = s;
    return t;
  };
  K.scale = (d0, d1, r0, r1) => v => r0 + (v - d0) / (d1 - d0) * (r1 - r0);
  K.clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  K.fmt = (v, d = 1) => v == null || isNaN(v) ? "–" : (v > 0 ? "+" : v < 0 ? "−" : "") + Math.abs(v).toFixed(d);
  K.pct = (v, d = 1) => v == null || isNaN(v) ? "–" : (100 * v).toFixed(d) + "%";
  K.svgPoint = function (svg, ev, W) {
    const r = svg.getBoundingClientRect();
    const vb = svg.viewBox.baseVal;
    return { x: (ev.clientX - r.left) * vb.width / r.width, y: (ev.clientY - r.top) * vb.height / r.height };
  };

  // tooltip
  let tip;
  K.tip = function (html, ev) {
    if (!tip) { tip = document.getElementById("tip"); }
    tip.innerHTML = html;
    tip.style.opacity = 1;
    const x = Math.min(ev.clientX + 14, window.innerWidth - tip.offsetWidth - 8);
    const y = ev.clientY + 14 + tip.offsetHeight > window.innerHeight ? ev.clientY - tip.offsetHeight - 10 : ev.clientY + 14;
    tip.style.left = Math.max(8, x) + "px";
    tip.style.top = y + "px";
  };
  K.hide = () => { if (tip) tip.style.opacity = 0; };
  K.hover = function (node, html) {
    node.addEventListener("pointermove", ev => K.tip(typeof html === "function" ? html() : html, ev));
    node.addEventListener("pointerleave", K.hide);
  };

  // diverging colour between two CSS colours through --mid; t in [-1, 1]
  K.div = function (t, neg = "var(--cold)", pos = "var(--hot)") {
    t = K.clamp(t, -1, 1);
    const c = t >= 0 ? pos : neg;
    return `color-mix(in oklab, ${c} ${Math.round(Math.abs(t) * 100)}%, var(--mid))`;
  };
  K.seq = function (t, c = "var(--tor)") {
    return `color-mix(in oklab, ${c} ${Math.round(K.clamp(t, 0, 1) * 100)}%, var(--grid))`;
  };

  // half court, 10 px per foot, basket near the top; returns {X, Y, g}
  K.court = function (svg, opts = {}) {
    const S = 10, Y0 = 5.25, depth = opts.depth || 29;
    const X = v => v * S, Y = v => (v + Y0) * S;
    svg.setAttribute("viewBox", `0 0 500 ${Math.round(Y(depth))}`);
    const g = K.el("g", {}, svg);
    K.el("rect", { x: 0, y: 0, width: 500, height: Y(depth), class: "court-line", style: "opacity:.35" }, g);
    K.el("rect", { x: X(17), y: 0, width: X(16), height: Y(13.75), class: "court-line" }, g);
    K.el("path", { d: `M ${X(19)} ${Y(13.75)} A ${6 * S} ${6 * S} 0 0 0 ${X(31)} ${Y(13.75)}`, class: "court-line" }, g);
    K.el("line", { x1: X(22), x2: X(28), y1: Y(-1.25), y2: Y(-1.25), class: "court-line", style: "stroke-width:2" }, g);
    K.el("circle", { cx: X(25), cy: Y(0), r: 0.75 * S, class: "court-line" }, g);
    K.el("path", { d: `M ${X(21)} ${Y(0)} A ${4 * S} ${4 * S} 0 0 0 ${X(29)} ${Y(0)}`, class: "court-line", style: "opacity:.4" }, g);
    const c3 = Math.sqrt(22.15 ** 2 - 9);
    K.el("path", { d: `M ${X(25 - c3)} 0 L ${X(25 - c3)} ${Y(3)} A ${22.15 * S} ${22.15 * S} 0 0 0 ${X(25 + c3)} ${Y(3)} L ${X(25 + c3)} 0`, class: "court-line" }, g);
    return { X, Y, g, S };
  };
  K.hexPts = (cx, cy, r) => Array.from({ length: 6 }, (_, i) => {
    const a = Math.PI / 180 * (60 * i - 90);
    return `${(cx + r * Math.cos(a)).toFixed(1)},${(cy + r * Math.sin(a)).toFixed(1)}`;
  }).join(" ");

  K.ZONE = {
    "Rim": "At the rim (0–4 ft)", "Short": "Short paint (4–10 ft)", "Mid L": "Midrange, left", "Mid C": "Midrange, middle",
    "Mid R": "Midrange, right", "Corner3 L": "Left corner 3", "Corner3 R": "Right corner 3", "Arc3 L": "Left wing 3",
    "Arc3 C": "Top of the key 3", "Arc3 R": "Right wing 3",
  };

  // nudge text labels apart vertically: items {x, y, w}; mutates y
  K.declutter = function (items, h = 13) {
    items.sort((a, b) => a.y - b.y);
    for (let i = 1; i < items.length; i++) for (let j = 0; j < i; j++)
      if (Math.abs(items[i].x - items[j].x) < Math.max(items[i].w, items[j].w) && items[i].y - items[j].y < h) items[i].y = items[j].y + h;
    return items;
  };

  K.toggle = function (groupEl, onChange) {
    const btns = [...groupEl.querySelectorAll("button")];
    const set = v => { btns.forEach(b => b.setAttribute("aria-pressed", b.dataset.v === v)); onChange(v); };
    btns.forEach(b => b.addEventListener("click", () => set(b.dataset.v)));
    return set;
  };

  window.K = K;
})();
