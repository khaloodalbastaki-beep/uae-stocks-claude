/* Tiny dependency-free SVG charts (sparkline, bars, meter). Keeping the chart layer
   vanilla matches Khalid's "small, stable tool set" rule — no charting library, no build
   step, works offline. */
(function () {
  function sparkline(values, { w = 220, h = 44, color = "var(--accent)" } = {}) {
    if (!values || values.length < 2) return "";
    const min = Math.min(...values), max = Math.max(...values);
    const span = max - min || 1;
    const step = w / (values.length - 1);
    const pts = values.map((v, i) => [i * step, h - ((v - min) / span) * (h - 6) - 3]);
    const d = pts.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join(" ");
    const up = values[values.length - 1] >= values[0];
    const stroke = up ? "var(--pos)" : "var(--neg)";
    const area = `${d} L ${w} ${h} L 0 ${h} Z`;
    const id = "g" + Math.random().toString(36).slice(2, 7);
    return `<svg viewBox="0 0 ${w} ${h}" width="100%" height="${h}" preserveAspectRatio="none">
      <defs><linearGradient id="${id}" x1="0" x2="0" y1="0" y2="1">
        <stop offset="0" stop-color="${stroke}" stop-opacity="0.22"/>
        <stop offset="1" stop-color="${stroke}" stop-opacity="0"/></linearGradient></defs>
      <path d="${area}" fill="url(#${id})"/>
      <path d="${d}" fill="none" stroke="${stroke}" stroke-width="1.8" stroke-linejoin="round"/>
    </svg>`;
  }

  function meter(pct, color) {
    const c = color || (pct >= 66 ? "var(--pos)" : pct >= 45 ? "var(--caution)" : "var(--neg)");
    return `<div class="meter"><i style="width:${Math.max(2, Math.min(100, pct))}%;background:${c}"></i></div>`;
  }

  function bars(labels, values, fmt) {
    if (!values || !values.length) return "";
    const nums = values.filter((v) => typeof v === "number" && isFinite(v));
    if (!nums.length) return `<div class="empty">—</div>`;
    const max = Math.max(...nums.map(Math.abs)) || 1;
    return `<div class="barchart">${values.map((v, i) => {
      const ok = typeof v === "number" && isFinite(v);
      const h = ok ? Math.max(3, (Math.abs(v) / max) * 100) : 0;
      const lbl = ok ? (fmt ? fmt(v) : String(v)) : "—";
      return `<div class="b${ok ? "" : " na"}" style="height:${h}%" title="${labels[i]}: ${lbl}">
        <b class="bval">${lbl}</b><span>${labels[i]}</span></div>`;
    }).join("")}</div>`;
  }

  function gauge(score, label) {
    const c = score >= 72 ? "var(--pos)" : score >= 50 ? "var(--caution)" : "var(--neg)";
    const r = 26, circ = 2 * Math.PI * r, off = circ * (1 - score / 100);
    return `<svg width="70" height="70" viewBox="0 0 70 70">
      <circle cx="35" cy="35" r="${r}" fill="none" stroke="var(--surface-2)" stroke-width="7"/>
      <circle cx="35" cy="35" r="${r}" fill="none" stroke="${c}" stroke-width="7" stroke-linecap="round"
        stroke-dasharray="${circ}" stroke-dashoffset="${off}" transform="rotate(-90 35 35)"/>
      <text x="35" y="40" text-anchor="middle" font-size="18" font-weight="800" fill="var(--text)">${score}</text>
    </svg>`;
  }

  window.Charts = { sparkline, meter, bars, gauge };
})();
