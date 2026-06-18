/* UAE Stocks Intelligence — SPA router + views.
   Card-first surface, institutional depth on the stock page (8 tabs). Every derived
   value carries a source badge + timestamp (the blueprint's provenance spine), official
   facts are visually separated from media / opinion / AI, and the AI tab leads with a
   compliance label. */
(function () {
  const t = (k) => I18N.t(k);
  const $ = (s, r = document) => r.querySelector(s);
  const app = $("#app");

  // ---------- formatting (Khalid's rules: AED, % to 1dp, price to 2dp) ----------
  const fmtPrice = (v) => v == null ? "—" : Number(v).toLocaleString("en", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const fmtPct = (v) => v == null ? "—" : (v * 100).toFixed(1) + "%";
  const fmtPctSigned = (v) => v == null ? "—" : (v >= 0 ? "+" : "") + (v * 100).toFixed(1) + "%";
  const fmtAED = (v) => v == null ? "—" : "AED " + Number(v).toLocaleString("en", { maximumFractionDigits: 2 });
  const fmtBig = (v) => {
    if (v == null) return "—";
    const a = Math.abs(v);
    if (a >= 1e9) return (v / 1e9).toFixed(1) + "B";
    if (a >= 1e6) return (v / 1e6).toFixed(1) + "M";
    if (a >= 1e3) return (v / 1e3).toFixed(1) + "K";
    return "" + v;
  };
  const fmtDate = (s) => { if (!s) return "—"; const d = new Date(s); return isNaN(d) ? s : d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" }); };
  const ago = (s) => { const d = new Date(s); if (isNaN(d)) return s; const m = Math.round((Date.now() - d) / 60000); if (m < 60) return m + "m"; const h = Math.round(m / 60); if (h < 24) return h + "h"; return Math.round(h / 24) + "d"; };
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const nm = (o) => I18N.isAr() && o.name_ar ? o.name_ar : o.name_en;

  // ---------- shared bits ----------
  const dqBadge = (dq) => {
    const map = { realtime: "realtime", delayed: "delayed", eod: "delayed", demo: "demo" };
    const cls = map[dq] || "demo";
    const label = dq === "demo" ? t("demo") : dq === "realtime" ? t("realtime") : t("delayed");
    return `<span class="badge ${cls}">${label}</span>`;
  };
  const srcBadge = (type) => `<span class="badge ${type}">${type}</span>`;
  const scoreChips = (s) => `
    <span class="chip g" title="${t("growth")}">G ${s.growth}</span>
    <span class="chip s" title="${t("stability")}">S ${s.stability}</span>
    <span class="chip d" title="${t("dividend")}">D ${s.dividend}</span>`;

  function stockCard(c) {
    const cls = c.change_pct >= 0 ? "pos" : "neg";
    const starred = Watch.has(c.symbol);
    return `<a class="card" href="#/stock/${c.symbol}">
      <div class="card-top">
        <div><div class="sym">${esc(c.symbol)} <span class="exch">${c.exchange}</span></div>
        <div class="name">${esc(nm(c))}</div></div>
        <button class="star ${starred ? "on" : ""}" data-star="${c.symbol}" title="${t(starred ? "in_watch" : "add_watch")}">${starred ? "★" : "☆"}</button>
      </div>
      <div class="price-row">
        <span class="price mono">${fmtPrice(c.price)}</span>
        <span class="chg mono ${cls}">${fmtPctSigned(c.change_pct)}</span>
        <span class="impact ${c.impact} pull-end">${c.impact}</span>
      </div>
      <div class="chips">${scoreChips(c.scores)}</div>
      <div class="footer">
        <span class="tag">${esc(c.catalyst)}</span>
        <span>${t("yield_")}: ${fmtPct(c.dividend_yield)}</span>
        ${dqBadge(c.data_quality)}
      </div>
    </a>`;
  }

  function bindStars(root) {
    root.querySelectorAll("[data-star]").forEach((b) => b.addEventListener("click", (e) => {
      e.preventDefault(); e.stopPropagation();
      const on = Watch.toggle(b.dataset.star);
      b.classList.toggle("on", on); b.textContent = on ? "★" : "☆";
    }));
  }

  // ---------- nav ----------
  function renderNav() {
    const items = [
      ["#/", "home"], ["#/markets/adx", "markets"], ["#/watchlist", "watchlist"],
      ["#/alerts", "alerts"], ["#/screeners", "screeners"], ["#/global-factors", "global_factors"],
      ["#/ipos", "ipos"], ["#/admin", "admin"],
    ];
    const cur = location.hash || "#/";
    $("#nav").innerHTML = items.map(([h, k]) =>
      `<a href="${h}" class="${cur === h || (k === "markets" && cur.startsWith("#/markets")) ? "active" : ""}">${t(k)}</a>`).join("");
  }

  // ---------- HOME ----------
  async function viewHome() {
    app.innerHTML = skel();
    const [meta, uni, idx, events, cmo] = await Promise.all([
      DATA.meta(), DATA.universe(), DATA.indices(), DATA.events(), DATA.commodities(),
    ]);
    const watch = Watch.list();
    const favs = uni.filter((c) => watch.includes(c.symbol));
    const topDisc = uni.slice().sort((a, b) => b.scores.headline - a.scores.headline);
    const ms = meta.market_status;

    app.innerHTML = `
      ${demoNotice(meta)}
      <div class="banner ${ms.state}">
        <span class="dot"></span>
        <strong>${I18N.isAr() ? ms.label_ar : ms.label_en}</strong>
        <span class="meta">${t("updated")} ${ago(meta.generated_at)} ${I18N.isAr() ? "" : "ago"} · ${meta.counts.securities} securities</span>
      </div>

      <section class="section">
        <h2>${t("market_pulse")}</h2>
        <div class="pulse">
          ${pulseCard(t("adx_index"), idx.adx)}
          ${pulseCard(t("dfm_index"), idx.dfm)}
          ${sectorPulse(idx.sectors)}
        </div>
      </section>

      <section class="section">
        <h2>${t("favorites")}</h2>
        ${favs.length ? `<div class="grid cards">${favs.map(stockCard).join("")}</div>`
          : `<div class="empty">${t("no_watch")}</div>`}
      </section>

      <section class="section">
        <h2>${t("upcoming_events")}</h2>
        <div class="panel">${eventsStrip(events)}</div>
      </section>

      <section class="section">
        <h2>${t("latest_disclosures")}</h2>
        <div class="grid cards">${topDisc.slice(0, 6).map(stockCard).join("")}</div>
      </section>

      <section class="section">
        <h2>${t("macro")}</h2>
        <div class="panel"><div class="expo">${cmo.map(commodityCard).join("")}</div></div>
      </section>
    `;
    bindStars(app);
  }

  const pulseCard = (label, idx) => {
    const hasReal = idx.index_value != null;
    const chg = hasReal ? idx.index_change_pct : idx.avg_change_pct;
    const up = (chg || 0) >= 0;
    const headline = hasReal
      ? `<div class="v mono">${Number(idx.index_value).toLocaleString("en", { minimumFractionDigits: 2 })}
           <span class="${up ? "pos" : "neg"}" style="font-size:14px">${fmtPctSigned(chg)}</span></div>`
      : `<div class="v ${up ? "pos" : "neg"} mono">${fmtPctSigned(chg)}</div>`;
    return `<div class="pcard"><div class="k">${idx.name || label}</div>
      ${headline}
      <div class="sub">${idx.advancers} ${t("advancers")} · ${idx.decliners} ${t("decliners")}${hasReal ? " · live" : ""}</div></div>`;
  };
  const sectorPulse = (sectors) => {
    const top = sectors.slice().sort((a, b) => b.avg_score - a.avg_score).slice(0, 3);
    return `<div class="pcard"><div class="k">Top sectors (house score)</div>
      ${top.map((s) => `<div class="sub" style="display:flex;justify-content:space-between;margin-top:6px">
        <span>${esc(s.sector)}</span><strong class="mono">${s.avg_score}</strong></div>`).join("")}</div>`;
  };
  const commodityCard = (c) => {
    const up = c.change_pct >= 0;
    return `<div class="e"><div class="lab">${esc(c.label)}</div>
      <div class="val mono">${fmtPrice(c.value)} <span class="u">${esc(c.unit)}</span></div>
      <div class="${up ? "pos" : "neg"} mono" style="font-size:12px">${fmtPctSigned(c.change_pct)}</div></div>`;
  };
  function eventsStrip(events) {
    if (!events.length) return `<div class="empty">${t("no_data")}</div>`;
    const icon = { board: "🪑", agm: "🗳️", egm: "🗳️", dividend: "💵", ipo: "📈" };
    return events.slice(0, 14).map((e) => `<a class="row-item" href="#/stock/${e.symbol}">
      <span class="date mono">${fmtDate(e.date)}</span>
      <span>${icon[e.type] || "•"}</span>
      <span><strong>${esc(e.symbol)}</strong> — ${esc(e.label.replace(/^[A-Z]+ — /, ""))}</span>
      <span class="tag pull-end">${esc(e.type)}</span></a>`).join("");
  }

  // ---------- MARKETS ----------
  async function viewMarkets(exch) {
    app.innerHTML = skel();
    const [meta, uni] = await Promise.all([DATA.meta(), DATA.universe()]);
    const ex = (exch || "adx").toUpperCase();
    const tabs = ["ADX", "DFM", "ALL"];
    let list = ex === "ALL" ? uni : uni.filter((c) => c.exchange === ex);
    list = list.slice().sort((a, b) => b.scores.headline - a.scores.headline);
    app.innerHTML = `
      ${demoNotice(meta)}
      <div class="tabs">${tabs.map((x) => `<button class="${x === ex ? "active" : ""}" onclick="location.hash='#/markets/${x.toLowerCase()}'">${x}</button>`).join("")}</div>
      <div class="muted" style="margin-bottom:10px">${list.length} securities · sorted by overall house score</div>
      <div class="grid cards">${list.map(stockCard).join("")}</div>`;
    bindStars(app);
    renderNav();
  }

  // ---------- STOCK PAGE ----------
  let stockTab = "overview";
  async function viewStock(sym) {
    app.innerHTML = skel();
    let s, meta;
    try { [s, meta] = await Promise.all([DATA.stock(sym), DATA.meta()]); }
    catch (e) { app.innerHTML = `<div class="empty">${t("no_data")} (${esc(sym)})</div>`; return; }

    const q = s.quote || {};
    const cls = (q.change_pct || 0) >= 0 ? "pos" : "neg";
    const starred = Watch.has(s.symbol);
    const tabs = [
      ["overview", "overview"], ["news", "news"], ["meetings", "meetings"],
      ["financials", "financials"], ["dividends", "dividends"], ["ownership", "ownership"],
      ["global", "global_factors"], ["ai", "ai_analysis"],
    ];
    app.innerHTML = `
      ${demoNotice(meta)}
      <div class="stock-head">
        <div class="stock-id">
          <h1>${esc(s.symbol)} <button class="star ${starred ? "on" : ""}" data-star="${s.symbol}" style="font-size:22px;background:none;border:none;color:${starred ? "var(--gold)" : "var(--text-faint)"}">${starred ? "★" : "☆"}</button></h1>
          <div>${esc(s.name_en)}</div>
          <div class="ar">${esc(s.name_ar)}</div>
          <div class="sub">${s.exchange} · ${esc(s.sector)} · ${dqBadge(q.prov ? q.prov.data_quality : "demo")}</div>
        </div>
        <div class="price-big">
          <div class="p mono">${fmtPrice(q.price)} <span class="muted" style="font-size:14px">AED</span></div>
          <div class="c mono ${cls}">${q.change >= 0 ? "+" : ""}${fmtPrice(q.change)} (${fmtPctSigned(q.change_pct)})</div>
          <div style="margin-top:6px">${Charts.sparkline(q.spark || [], { h: 40, w: 200 })}</div>
        </div>
      </div>

      <div class="scorebar">
        ${scorePill(t("headline"), s.scores.headline, s.scores.headline_grade)}
        ${scorePill(t("growth"), s.scores.growth.score, s.scores.growth.grade)}
        ${scorePill(t("stability"), s.scores.stability.score, s.scores.stability.grade)}
        ${scorePill(t("dividend"), s.scores.dividend.score, s.scores.dividend.grade)}
      </div>

      <div class="tabs" id="stock-tabs">
        ${tabs.map(([id, k]) => `<button data-tab="${id}" class="${stockTab === id ? "active" : ""}">${t(k)}</button>`).join("")}
      </div>
      <div id="tabpanel"></div>
    `;
    bindStars(app);
    const panel = $("#tabpanel");
    const renderTab = () => { panel.innerHTML = stockTabHTML(stockTab, s); afterTab(stockTab, s, panel); };
    $("#stock-tabs").querySelectorAll("[data-tab]").forEach((b) => b.addEventListener("click", () => {
      stockTab = b.dataset.tab;
      $("#stock-tabs").querySelectorAll("button").forEach((x) => x.classList.toggle("active", x === b));
      renderTab();
    }));
    renderTab();
  }

  const scorePill = (lbl, val, grade) => `<div class="score-pill"><div class="lbl">${lbl}</div>
    <div class="val mono">${val}</div><div class="grade">${grade || ""}</div>
    ${Charts.meter(val)}</div>`;

  function stockTabHTML(tab, s) {
    if (tab === "overview") return overviewTab(s);
    if (tab === "news") return newsTab(s);
    if (tab === "meetings") return meetingsTab(s);
    if (tab === "financials") return financialsTab(s);
    if (tab === "dividends") return dividendsTab(s);
    if (tab === "ownership") return ownershipTab(s);
    if (tab === "global") return globalTab(s);
    if (tab === "ai") return aiTab(s);
    return "";
  }
  function afterTab() {}

  function overviewTab(s) {
    const o = s.overview, qs = o.quick_stats;
    const fs = s.fundamentals_source || {};
    const fundLine = fs.real
      ? `<div class="disclaimer" style="border-color:var(--ai);color:#56e0bd">📊 <strong>Real fundamentals</strong> — reported figures ${fs.as_of ? "(" + esc(fs.as_of) + ")" : ""} from ${fs.source_url ? `<a href="${esc(fs.source_url)}" target="_blank" rel="noopener">${esc(fs.source || "source")}</a>` : esc(fs.source || "filing")}. House scores are computed from these; ${esc(fs.confidence || "")} confidence.</div>`
      : `<div class="disclaimer">📊 Fundamentals are a <strong>modeled estimate</strong> for this name (real prices, modeled financials) — the Mizan agent fills real filings as they're sourced.</div>`;
    return `<div class="panel"><h3>${t("business_summary")}</h3>
      <p>${esc(I18N.isAr() ? o.business_summary_ar : o.business_summary_en)}</p>${fundLine}</div>
      <div class="panel"><h3>${t("quick_stats")}</h3>
        <div class="kv">
          <div><div class="k">${t("market_cap")}</div><div class="v mono">${fmtBig(qs.market_cap)}</div></div>
          <div><div class="k">${t("volume")}</div><div class="v mono">${fmtBig(qs.volume)}</div></div>
          <div><div class="k">52w high</div><div class="v mono">${fmtPrice(qs.high_52w)}</div></div>
          <div><div class="k">52w low</div><div class="v mono">${fmtPrice(qs.low_52w)}</div></div>
          <div><div class="k">${t("yield_")}</div><div class="v mono">${fmtPct(qs.dividend_yield)}</div></div>
          <div><div class="k">Index</div><div class="v">${(o.index_membership || []).join(", ")}</div></div>
        </div></div>
      <div class="grid" style="grid-template-columns:1fr 1fr;gap:12px">
        <div class="panel"><h3>${t("top_catalysts")}</h3><ul>${o.top_catalysts.map((x) => `<li>${esc(x)}</li>`).join("") || "—"}</ul></div>
        <div class="panel"><h3>${t("top_risks")}</h3><ul>${o.top_risks.map((x) => `<li>${esc(x)}</li>`).join("") || "—"}</ul></div>
      </div>`;
  }

  function newsTab(s) {
    if (!s.disclosures.length) return `<div class="empty">${t("no_data")}</div>`;
    return s.disclosures.map((d) => {
      const isAr = d.title_lang === "ar";
      return `<div class="disc">
        <div class="head">
          <span class="et">${esc(d.event_type.replace(/_/g, " "))}</span>
          ${srcBadge(d.prov ? d.prov.source_type : "official")}
          ${d.translation_app_generated ? `<span class="badge ai">translated</span>` : ""}
          <span class="muted pull-end">${fmtDate(d.published_at)}</span>
        </div>
        <div class="ttl">${esc(d.title_en)}</div>
        ${isAr ? `<div class="ar">${esc(d.title_src)}</div>` : ""}
        ${d.summary_en ? `<div class="muted" style="margin-top:6px">${esc(d.summary_en)}</div>` : ""}
        <div class="why"><strong>${t("why_it_matters")}:</strong> ${esc(d.why_it_matters)}</div>
        <div class="metarow">
          <span>${t("materiality")}</span><span class="mat-bar"><i style="width:${d.materiality}%"></i></span><span class="mono">${d.materiality}</span>
          <span>·</span><span>${t("sentiment")}: <span class="senti ${d.sentiment}">${d.sentiment}</span></span>
        </div>
      </div>`;
    }).join("") + aiFootnote();
  }

  function meetingsTab(s) {
    if (!s.meetings.length) return `<div class="empty">${t("no_data")}</div>`;
    const order = { upcoming: 0, held: 1 };
    const ms = s.meetings.slice().sort((a, b) => (order[a.status] - order[b.status]) || a.date.localeCompare(b.date));
    return `<div class="panel">${ms.map((m) => `
      <div class="row-item" style="align-items:flex-start">
        <span class="date mono">${fmtDate(m.date)}</span>
        <div style="flex:1">
          <div><strong>${m.kind.toUpperCase()}</strong> <span class="tag">${m.status === "upcoming" ? t("upcoming") : t("held")}</span>
          ${(m.topics || []).map((x) => `<span class="tag">${esc(x.replace(/_/g, " "))}</span>`).join(" ")}</div>
          ${m.agenda && m.agenda.length ? `<div class="muted" style="margin-top:4px">${m.agenda.map(esc).join(" · ")}</div>` : ""}
          ${m.outcome_summary ? `<div class="why" style="margin-top:6px">${esc(m.outcome_summary)}</div>` : ""}
        </div>
      </div>`).join("")}</div>`;
  }

  function financialsTab(s) {
    const f = s.financials;
    const yrs = f.years.map(String);
    return `<div class="panel"><h3>Revenue (${t("demo")})</h3>${Charts.bars(yrs, f.revenue, fmtBig)}</div>
      <div class="panel"><h3>Net income</h3>${Charts.bars(yrs, f.net_income, fmtBig)}</div>
      <div class="panel"><h3>Operating cash flow</h3>${Charts.bars(yrs, f.operating_cash_flow, fmtBig)}</div>
      <div class="panel"><h3>Key ratios</h3><div class="kv">
        <div><div class="k">Net margin</div><div class="v mono">${f.ratios.net_margin != null ? fmtPct(f.ratios.net_margin) : "—"}</div></div>
        <div><div class="k">Net debt / EBITDA</div><div class="v mono">${f.ratios.net_debt_to_ebitda}×</div></div>
        <div><div class="k">Current ratio</div><div class="v mono">${f.ratios.current_ratio}</div></div>
        <div><div class="k">Payout ratio</div><div class="v mono">${fmtPct(f.ratios.payout_ratio)}</div></div>
        <div><div class="k">Revenue CAGR 3y</div><div class="v mono">${fmtPct(f.revenue_cagr_3y)}</div></div>
      </div></div>`;
  }

  function dividendsTab(s) {
    if (!s.dividends.length) return `<div class="empty">No dividend record (or non-paying name).</div>`;
    const dsc = s.scores.dividend;
    return `<div class="panel"><h3>${t("dividend")} score: ${dsc.score} (${dsc.grade})</h3>
      ${dsc.subfactors.map((f) => `<div class="row-item">
        <span style="flex:1">${esc(f.label)}</span>
        <span class="muted mono">${typeof f.raw === "number" ? f.raw : esc(f.raw)}</span>
        <span class="mono" style="min-width:40px;text-align:end">${Math.round(f.points)}</span>
        <span style="width:80px">${Charts.meter(f.points)}</span></div>`).join("")}
      <div class="muted" style="margin-top:8px">${esc(dsc.subfactors.map((f) => f.note).filter(Boolean)[0] || "")}</div>
    </div>
    <div class="panel"><h3>Distribution calendar</h3>
      ${s.dividends.map((d) => `<div class="row-item">
        <span class="date mono">${fmtDate(d.ex_date)}</span>
        <span><strong class="mono">${fmtAED(d.amount)}</strong> / share · ${esc(d.frequency)}</span>
        <span class="muted pull-end">${t("payment")}: ${fmtDate(d.payment_date)}</span></div>`).join("")}
    </div>`;
  }

  function ownershipTab(s) {
    const o = s.ownership;
    if (!o) return `<div class="empty">${t("no_data")}</div>`;
    return `<div class="panel"><h3>${t("foreign_own")}</h3><div class="kv">
        <div><div class="k">${t("permitted")}</div><div class="v mono">${o.foreign_permitted ?? "—"}%</div></div>
        <div><div class="k">${t("actual")}</div><div class="v mono">${o.foreign_actual ?? "—"}%</div></div>
        <div><div class="k">${t("available")}</div><div class="v mono">${o.foreign_available ?? "—"}%</div></div>
        <div><div class="k">${t("free_float")}</div><div class="v mono">${o.free_float ?? "—"}%</div></div>
      </div></div>
      <div class="panel"><h3>${t("top_holders")}</h3>
        ${(o.top_holders || []).map((h) => `<div class="row-item"><span style="flex:1">${esc(h.name)}</span>
          <span class="mono">${h.pct}%</span><span style="width:120px">${Charts.meter(h.pct)}</span></div>`).join("")}
      </div>`;
  }

  function globalTab(s) {
    const g = s.global_factors;
    return `<div class="panel"><h3>${t("exposure_map")}</h3>
      <div class="expo">${g.exposures.map((e) => `<div class="e">
        <div class="lab">${esc(I18N.isAr() ? e.label_ar : e.label_en)}</div>
        ${e.latest_value != null ? `<div class="val mono">${fmtPrice(e.latest_value)} <span class="u">${esc(e.unit)}</span></div>
          <div class="${e.latest_change_pct >= 0 ? "pos" : "neg"} mono" style="font-size:12px">${fmtPctSigned(e.latest_change_pct)}</div>`
          : `<div class="u">structural driver</div>`}
      </div>`).join("")}</div>
      <div class="muted" style="margin-top:8px">${esc(g.note)}</div></div>
      <div class="panel"><h3>Linked global events ${srcBadge(g.events[0] && g.events[0].prov ? g.events[0].prov.source_type : "media")}</h3>
        ${g.events.length ? g.events.map((e) => `<div class="row-item">
          <span class="date mono">${ago(e.published_at)}</span>
          <span style="flex:1">${e.url ? `<a href="${esc(e.url)}" target="_blank" rel="noopener">${esc(e.title)}</a>` : esc(e.title)}</span>
          <span class="tag">${esc(e.domain || e.theme)}</span></div>`).join("") : `<div class="empty">${t("no_data")}</div>`}
      </div>`;
  }

  function aiTab(s) {
    const a = s.ai_analysis;
    const col = (horizon, data) => `<div class="ai-col">
      <div class="muted">${t(horizon)}</div>
      <div class="stance ${data.stance}">${data.stance}</div>
      <div class="conf">${t("confidence")}: ${data.confidence}</div>
      <div style="margin-top:10px"><strong>${t("reasons")}</strong><ul>${data.reasons.map((x) => `<li>${esc(x)}</li>`).join("")}</ul></div>
      <div><strong>${t("risks")}</strong><ul>${data.risks.map((x) => `<li>${esc(x)}</li>`).join("")}</ul></div>
      <div class="muted" style="margin-top:6px"><strong>${t("change_view")}:</strong> ${esc(data.what_would_change_view)}</div>
    </div>`;
    return `<div class="disclaimer">⚠️ ${t("not_advice")} — AI provider: <strong>${esc(a.provider)}</strong>, engine: ${esc(a._engine)}. House scores are computed deterministically; the AI only narrates.</div>
      <div class="ai-grid" style="margin-top:12px">
        ${col("short_term", a.short_term)}
        ${col("long_term", a.long_term)}
      </div>`;
  }

  const aiFootnote = () => `<div class="disclaimer">${t("ar_official")} ${t("not_advice")}</div>`;

  // ---------- WATCHLIST ----------
  async function viewWatchlist() {
    app.innerHTML = skel();
    const [meta, uni] = await Promise.all([DATA.meta(), DATA.universe()]);
    const watch = Watch.list();
    const favs = uni.filter((c) => watch.includes(c.symbol));
    app.innerHTML = `${demoNotice(meta)}<section class="section"><h2>${t("watchlist")}</h2>
      ${favs.length ? `<div class="grid cards">${favs.map(stockCard).join("")}</div>` : `<div class="empty">${t("no_watch")}</div>`}</section>`;
    bindStars(app);
  }

  // ---------- ALERTS (derived from events + watchlist) ----------
  async function viewAlerts() {
    app.innerHTML = skel();
    const [meta, uni, events] = await Promise.all([DATA.meta(), DATA.universe(), DATA.events()]);
    const watch = Watch.list();
    const moved = uni.filter((c) => Math.abs(c.change_pct || 0) >= 0.02)
      .sort((a, b) => Math.abs(b.change_pct) - Math.abs(a.change_pct)).slice(0, 8);
    const myEvents = events.filter((e) => watch.includes(e.symbol)).slice(0, 12);
    app.innerHTML = `${demoNotice(meta)}
      <section class="section"><h2>${t("alerts")} — price moves</h2>
        <div class="panel">${moved.map((c) => `<a class="row-item" href="#/stock/${c.symbol}">
          <strong style="min-width:90px">${esc(c.symbol)}</strong>
          <span class="${c.change_pct >= 0 ? "pos" : "neg"} mono">${fmtPctSigned(c.change_pct)}</span>
          <span class="muted pull-end">${esc(c.catalyst)}</span></a>`).join("")}</div></section>
      <section class="section"><h2>Your watchlist events</h2>
        <div class="panel">${myEvents.length ? eventsStrip(myEvents) : `<div class="empty">${t("no_watch")}</div>`}</div></section>
      <div class="disclaimer">Alert rules run client-side over the brain's emitted data. Push delivery to Telegram/Hermes is the phase-2 hook (same pattern as the finance app).</div>`;
  }

  // ---------- SCREENERS ----------
  async function viewScreeners() {
    app.innerHTML = skel();
    const [meta, uni] = await Promise.all([DATA.meta(), DATA.universe()]);
    const presets = [
      ["Dividend income (D≥70, yield≥4%)", (c) => c.scores.dividend >= 70 && c.dividend_yield >= 0.04],
      ["Growth leaders (G≥70)", (c) => c.scores.growth >= 70],
      ["Sleep-well / stable (S≥66)", (c) => c.scores.stability >= 66],
      ["All-rounders (overall≥62)", (c) => c.scores.headline >= 62],
    ];
    app.innerHTML = `${demoNotice(meta)}${presets.map(([label, fn]) => {
      const hits = uni.filter(fn).sort((a, b) => b.scores.headline - a.scores.headline);
      return `<section class="section"><h2>${esc(label)} — ${hits.length}</h2>
        <div class="grid cards">${hits.slice(0, 8).map(stockCard).join("") || `<div class="empty">${t("no_data")}</div>`}</div></section>`;
    }).join("")}`;
    bindStars(app);
  }

  // ---------- GLOBAL FACTORS ----------
  async function viewGlobalFactors() {
    app.innerHTML = skel();
    const [meta, cmo, gev] = await Promise.all([DATA.meta(), DATA.commodities(), DATA.globalEvents()]);
    app.innerHTML = `${demoNotice(meta)}
      <section class="section"><h2>${t("macro")}</h2><div class="panel"><div class="expo">${cmo.map(commodityCard).join("")}</div></div></section>
      <section class="section"><h2>Global events ${srcBadge(gev[0] && gev[0].prov ? gev[0].prov.source_type : "media")}</h2>
        <div class="panel">${gev.length ? gev.map((e) => `<div class="row-item">
          <span class="date mono">${ago(e.published_at)}</span>
          <span style="flex:1">${e.url ? `<a href="${esc(e.url)}" target="_blank" rel="noopener">${esc(e.title)}</a>` : esc(e.title)}</span>
          <span class="tag">${esc(e.domain || e.theme)}</span></div>`).join("") : `<div class="empty">${t("no_data")}</div>`}</div></section>`;
  }

  // ---------- IPOs ----------
  async function viewIpos() {
    const meta = await DATA.meta();
    app.innerHTML = `${demoNotice(meta)}<section class="section"><h2>${t("ipos")}</h2>
      <div class="empty">IPO window tracking is wired in the data model (IPOEvent) and the events strip.
      The MVP ships ADX/DFM listed equities first; the live IPO feed is a phase-2 source adapter.</div></section>`;
  }

  // ---------- ADMIN (ingestion diagnostics) ----------
  async function viewAdmin() {
    app.innerHTML = skel();
    const [meta, uni, readiness] = await Promise.all([DATA.meta(), DATA.universe(), DATA.readiness()]);
    const demoCount = uni.filter((c) => c.data_quality === "demo").length;
    const checkStatus = (s) => ({ pass: "Pass", blocked: "Blocked", review: "Review" }[s] || s);
    const readinessCard = (c) => `<div class="readiness-card ${esc(c.status)}">
      <div class="readiness-head"><span class="status-dot"></span><strong>${esc(c.label)}</strong><span class="tag">${checkStatus(c.status)}</span></div>
      <div class="muted">${esc(c.evidence)}</div>
      <div class="next"><strong>Next:</strong> ${esc(c.next)}</div>
      <div class="owner">Owner: ${esc(c.owner)}</div>
    </div>`;
    app.innerHTML = `<section class="section"><h2>${t("admin")} — ingestion health</h2>
      <div class="panel"><div class="kv">
        <div><div class="k">Last build</div><div class="v mono">${fmtDate(meta.generated_at)} ${new Date(meta.generated_at).toLocaleTimeString("en-GB")}</div></div>
        <div><div class="k">Data provider</div><div class="v">${meta.provider}</div></div>
        <div><div class="k">AI provider</div><div class="v">${meta.ai_provider}</div></div>
        <div><div class="k">Securities</div><div class="v mono">${meta.counts.securities}</div></div>
        <div><div class="k">Events</div><div class="v mono">${meta.counts.events}</div></div>
        <div><div class="k">Demo-tagged quotes</div><div class="v mono">${demoCount}/${uni.length}</div></div>
      </div></div>
      <div class="panel readiness-panel">
        <h3>Launch readiness</h3>
        <div class="readiness-summary">
          <div><div class="k">Demo status</div><div class="v">${esc(readiness.summary.demo_status)}</div></div>
          <div><div class="k">Real launch</div><div class="v blocked">${esc(readiness.summary.real_launch_status)}</div></div>
          <div><div class="k">Live refresh</div><div class="v">${readiness.summary.live_exchange_refresh_enabled ? "enabled" : "disabled"}</div></div>
          <div><div class="k">Next decision</div><div class="v">${esc(readiness.summary.next_decision)}</div></div>
        </div>
        <div class="disclaimer">${esc(readiness.summary.blocking_reason)}</div>
        <div class="readiness-grid">${readiness.checks.map(readinessCard).join("")}</div>
      </div>
      <div class="panel"><h3>Sources</h3>${meta.sources.map((s) => `<div class="row-item">
        ${srcBadge(s.type)} <a href="${esc(s.url)}" target="_blank" rel="noopener" style="flex:1">${esc(s.name)}</a>
        <span class="tag">ok</span></div>`).join("")}</div>
      <div class="panel"><h3>Pipeline stages</h3>
        ${["ingest quotes", "ingest disclosures", "deterministic scoring", "AI narration", "emit JSON"].map((x) =>
          `<div class="row-item"><span style="flex:1">${x}</span><span class="tag">✓ ${meta.counts.securities}</span></div>`).join("")}</div>`;
  }

  // ---------- search ----------
  let UNI_CACHE = null;
  async function setupSearch() {
    const input = $("#search"), box = $("#search-results");
    input.placeholder = t("search_ph");
    const run = async () => {
      const qv = input.value.trim().toLowerCase();
      if (!qv) { box.hidden = true; return; }
      if (!UNI_CACHE) UNI_CACHE = await DATA.universe();
      const hits = UNI_CACHE.filter((c) =>
        c.symbol.toLowerCase().includes(qv) || c.name_en.toLowerCase().includes(qv) ||
        (c.name_ar || "").includes(input.value.trim())).slice(0, 8);
      box.innerHTML = hits.map((c) => `<a class="row" href="#/stock/${c.symbol}">
        <span class="sym">${esc(c.symbol)}</span><span style="flex:1">${esc(nm(c))}</span>
        <span class="exch">${c.exchange}</span></a>`).join("") || `<div class="row muted">${t("no_data")}</div>`;
      box.hidden = false;
    };
    input.addEventListener("input", run);
    input.addEventListener("focus", run);
    document.addEventListener("click", (e) => { if (!box.contains(e.target) && e.target !== input) box.hidden = true; });
    box.addEventListener("click", () => { box.hidden = true; input.value = ""; });
  }

  // ---------- shared chrome ----------
  function demoNotice(meta) {
    if (meta.provider === "live") {
      const fr = meta.counts && meta.counts.fundamentals_real ? meta.counts.fundamentals_real : null;
      return `<div class="disclaimer" style="border-color:var(--ai);color:#56e0bd">
        🟢 <strong>Real data</strong> — prices are ~15-min delayed from the ADX/DFM boards; indices (FADGI/DFMGI) are live.
        ${fr ? `Fundamentals are <strong>real reported FY figures</strong> for ${fr} of ${meta.counts.securities} names (sourced filings, via the Mizan agent)` : "Fundamentals are real for the major names"} — the rest are modeled estimates, each labelled on its stock page. House scores are computed from these by the deterministic engine.</div>`;
    }
    return `<div class="disclaimer" style="border-color:var(--demo);color:#ff9173">
      ⚠️ <strong>${t("demo")}</strong> — figures are realistic placeholders for the ADX/DFM universe. Tickers, sectors and the exposure map are real.</div>`;
  }
  function skel() {
    return `<div class="grid cards">${Array(6).fill('<div class="skel skel-card"></div>').join("")}</div>`;
  }
  function renderFooter() {
    $("#footer").innerHTML = `
      <div class="legend">
        <span class="badge official">official</span><span class="badge media">media</span>
        <span class="badge opinion">opinion</span><span class="badge ai">ai</span><span class="badge demo">demo</span>
      </div>
      <div>${t("ar_official")}</div>
      <div style="margin-top:4px">${t("not_advice")} Official exchange & issuer sources rank first; media second; opinion last. Built on Khalid's free GitHub-Pages + Mac-mini ecosystem.</div>`;
  }

  // ---------- router ----------
  function route() {
    const h = location.hash || "#/";
    renderNav();
    if (h === "#/" || h === "") return viewHome();
    if (h.startsWith("#/markets/")) return viewMarkets(h.split("/")[2]);
    if (h === "#/markets") return viewMarkets("adx");
    if (h.startsWith("#/stock/")) return viewStock(decodeURIComponent(h.split("/")[2]));
    if (h === "#/watchlist") return viewWatchlist();
    if (h === "#/alerts") return viewAlerts();
    if (h === "#/screeners") return viewScreeners();
    if (h === "#/global-factors") return viewGlobalFactors();
    if (h === "#/ipos") return viewIpos();
    if (h === "#/admin") return viewAdmin();
    return viewHome();
  }

  // ---------- boot ----------
  function boot() {
    I18N.init();
    renderFooter();
    setupSearch();
    $("#lang-btn").addEventListener("click", () => { I18N.toggle(); renderNav(); renderFooter(); route(); });
    $("#theme-btn").addEventListener("click", () => {
      const cur = document.documentElement.dataset.theme === "light" ? "dark" : "light";
      document.documentElement.dataset.theme = cur; localStorage.setItem("uae_theme", cur);
    });
    const savedTheme = localStorage.getItem("uae_theme");
    if (savedTheme) document.documentElement.dataset.theme = savedTheme;
    window.addEventListener("hashchange", route);
    window.addEventListener("watchchange", () => { if (location.hash.includes("watchlist")) route(); });
    route();
  }
  boot();
})();
