/* Bilingual EN/AR layer. The blueprint makes Arabic a product principle, not an
   afterthought: source-language documents are preserved and translation is marked
   app-generated. Here we localise the UI chrome and flip to RTL for Arabic. */
(function () {
  const STR = {
    en: {
      tagline: "ADX · DFM · explainable, source-first",
      home: "Home", markets: "Markets", watchlist: "Watchlist", alerts: "Alerts",
      screeners: "Screeners", global_factors: "Global Factors", ipos: "IPOs", admin: "Admin",
      market_pulse: "Market Pulse", favorites: "Your Watchlist", upcoming_events: "Upcoming Events",
      latest_disclosures: "Latest Meaningful Disclosures", macro: "Macro & Commodities",
      adx_index: "ADX (proxy)", dfm_index: "DFM (proxy)", advancers: "advancers", decliners: "decliners",
      overview: "Overview", news: "News & Disclosures", meetings: "Meetings", financials: "Financials",
      dividends: "Dividends", ownership: "Ownership", ai_analysis: "AI Analysis",
      growth: "Growth", stability: "Stability", dividend: "Dividend", headline: "Overall",
      why_it_matters: "Why it matters", materiality: "Materiality", sentiment: "Sentiment",
      short_term: "Short term", long_term: "Long term", reasons: "Key reasons", risks: "Key risks",
      confidence: "Confidence", change_view: "What would change the view",
      business_summary: "Business summary", quick_stats: "Quick stats", top_catalysts: "Top catalysts",
      top_risks: "Top risks", market_cap: "Market cap", volume: "Volume", yield_: "Dividend yield",
      add_watch: "Add to watchlist", in_watch: "In watchlist", no_watch: "No favorites yet — tap ☆ on any stock.",
      ex_date: "Ex-date", payment: "Payment", entitlement: "Entitlement", agm: "AGM",
      foreign_own: "Foreign ownership", permitted: "Permitted", actual: "Actual", available: "Available",
      free_float: "Free float", top_holders: "Top shareholders",
      delayed: "Delayed", realtime: "Real-time", demo: "Demo data", updated: "Updated",
      not_advice: "Research support, not personalised investment advice.",
      ar_official: "Arabic is the official text; English is an app-generated translation.",
      no_data: "No data available.", view_stock: "Open stock",
      exposure_map: "Exposure map", est_impact: "Estimated impact", upcoming: "Upcoming", held: "Held",
      search_ph: "Search symbol or company…",
    },
    ar: {
      tagline: "أبوظبي · دبي · شفّاف ومن المصدر",
      home: "الرئيسية", markets: "الأسواق", watchlist: "المفضلة", alerts: "التنبيهات",
      screeners: "الفرز", global_factors: "العوامل العالمية", ipos: "الاكتتابات", admin: "الإدارة",
      market_pulse: "نبض السوق", favorites: "قائمتك", upcoming_events: "الأحداث القادمة",
      latest_disclosures: "أحدث الإفصاحات المهمة", macro: "الاقتصاد الكلي والسلع",
      adx_index: "أبوظبي (تقديري)", dfm_index: "دبي (تقديري)", advancers: "مرتفعة", decliners: "منخفضة",
      overview: "نظرة عامة", news: "الأخبار والإفصاحات", meetings: "الاجتماعات", financials: "المالية",
      dividends: "التوزيعات", ownership: "الملكية", ai_analysis: "تحليل الذكاء الاصطناعي",
      growth: "النمو", stability: "الاستقرار", dividend: "التوزيعات", headline: "الإجمالي",
      why_it_matters: "لماذا يهم", materiality: "الأهمية", sentiment: "التوجّه",
      short_term: "المدى القصير", long_term: "المدى الطويل", reasons: "أهم الأسباب", risks: "أهم المخاطر",
      confidence: "مستوى الثقة", change_view: "ما الذي قد يغيّر الرأي",
      business_summary: "نبذة عن الشركة", quick_stats: "إحصائيات سريعة", top_catalysts: "أهم المحفزات",
      top_risks: "أهم المخاطر", market_cap: "القيمة السوقية", volume: "حجم التداول", yield_: "عائد التوزيع",
      add_watch: "أضف إلى المفضلة", in_watch: "في المفضلة", no_watch: "لا توجد مفضلة بعد — اضغط ☆ على أي سهم.",
      ex_date: "تاريخ الاستحقاق", payment: "الدفع", entitlement: "الأحقية", agm: "الجمعية العمومية",
      foreign_own: "الملكية الأجنبية", permitted: "المسموح", actual: "الفعلي", available: "المتاح",
      free_float: "الأسهم الحرة", top_holders: "كبار المساهمين",
      delayed: "مؤجّل", realtime: "لحظي", demo: "بيانات تجريبية", updated: "تم التحديث",
      not_advice: "دعم بحثي وليس نصيحة استثمارية شخصية.",
      ar_official: "النص العربي هو الرسمي؛ الإنجليزية ترجمة من التطبيق.",
      no_data: "لا تتوفر بيانات.", view_stock: "فتح السهم",
      exposure_map: "خريطة التعرّض", est_impact: "التأثير المقدّر", upcoming: "قادم", held: "منعقد",
      search_ph: "ابحث عن رمز أو شركة…",
    },
  };

  const I18N = {
    lang: localStorage.getItem("uae_lang") || "en",
    t(key) { return (STR[this.lang] && STR[this.lang][key]) || STR.en[key] || key; },
    isAr() { return this.lang === "ar"; },
    toggle() { this.set(this.lang === "en" ? "ar" : "en"); },
    set(lang) {
      this.lang = lang;
      localStorage.setItem("uae_lang", lang);
      document.documentElement.lang = lang;
      document.body.dir = lang === "ar" ? "rtl" : "ltr";
      document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = this.t(el.dataset.i18n); });
      const s = document.getElementById("search");
      if (s) s.placeholder = this.t("search_ph");
      window.dispatchEvent(new CustomEvent("langchange"));
    },
    init() { this.set(this.lang); },
  };
  window.I18N = I18N;
})();
