"""
Global factor / commodity driver definitions — the "global factor box".

The blueprint: "Every stock should have an exposure map that links it to inputs and
global drivers ... energy names connect to oil and gas, food names connect to wheat
and input costs, builders connect to metals, cement, freight, and rates."

Each driver has:
  - a human label (EN/AR),
  - the World Bank commodity series it maps to (where one exists), and
  - the GDELT theme/query hint for event detection.

`exposure_factors` keys on each Security (registry.py) reference these keys, so the
Global Factors tab can render a real, explainable exposure graph rather than a vibe.
"""
from __future__ import annotations

# key -> metadata
FACTORS: dict[str, dict] = {
    # --- commodities (World Bank Pink Sheet series in parentheses) ---
    "oil":               {"label_en": "Crude oil (Brent)", "label_ar": "النفط الخام", "wb_series": "CRUDE_BRENT", "unit": "USD/bbl", "gdelt": "ENERGY oil"},
    "natural_gas":       {"label_en": "Natural gas", "label_ar": "الغاز الطبيعي", "wb_series": "NGAS_EUR", "unit": "USD/mmbtu", "gdelt": "natural gas"},
    "lng":               {"label_en": "LNG", "label_ar": "الغاز المسال", "wb_series": "NGAS_JP", "unit": "USD/mmbtu", "gdelt": "LNG"},
    "urea":              {"label_en": "Urea", "label_ar": "اليوريا", "wb_series": "UREA_EE_BULK", "unit": "USD/mt", "gdelt": "fertilizer urea"},
    "ammonia":           {"label_en": "Ammonia", "label_ar": "الأمونيا", "wb_series": "iNATGAS", "unit": "USD/mt", "gdelt": "ammonia fertilizer"},
    "polyethylene":      {"label_en": "Polyethylene / plastics", "label_ar": "البولي إيثيلين", "wb_series": None, "unit": "USD/mt", "gdelt": "polyethylene petrochemical"},
    "construction_metals": {"label_en": "Steel & aluminium", "label_ar": "الصلب والألمنيوم", "wb_series": "ALUMINUM", "unit": "USD/mt", "gdelt": "steel aluminium construction"},
    "wheat":             {"label_en": "Wheat", "label_ar": "القمح", "wb_series": "WHEAT_US_HRW", "unit": "USD/mt", "gdelt": "wheat grain"},
    "chicken":           {"label_en": "Poultry / feed", "label_ar": "الدواجن والأعلاف", "wb_series": "CHICKEN", "unit": "USD/kg", "gdelt": "poultry feed prices"},
    "jet_fuel":          {"label_en": "Jet fuel", "label_ar": "وقود الطائرات", "wb_series": "CRUDE_BRENT", "unit": "USD/bbl", "gdelt": "jet fuel airline"},
    "fuel_demand":       {"label_en": "Fuel demand", "label_ar": "الطلب على الوقود", "wb_series": None, "unit": "idx", "gdelt": "fuel demand mobility"},
    "freight":           {"label_en": "Freight & shipping rates", "label_ar": "أسعار الشحن", "wb_series": None, "unit": "idx", "gdelt": "shipping freight container rates"},
    # --- macro / rates / fx ---
    "rates":             {"label_en": "US / UAE interest rates", "label_ar": "أسعار الفائدة", "wb_series": None, "unit": "%", "gdelt": "Federal Reserve interest rate"},
    "usd":               {"label_en": "US dollar (AED peg)", "label_ar": "الدولار الأمريكي", "wb_series": None, "unit": "idx", "gdelt": "US dollar"},
    "em_fx":             {"label_en": "Emerging-market FX", "label_ar": "عملات الأسواق الناشئة", "wb_series": None, "unit": "idx", "gdelt": "emerging market currency"},
    "uae_credit":        {"label_en": "UAE credit demand", "label_ar": "الطلب على الائتمان", "wb_series": None, "unit": "idx", "gdelt": "UAE lending credit growth"},
    "uae_equity":        {"label_en": "UAE equity market", "label_ar": "سوق الأسهم الإماراتي", "wb_series": None, "unit": "idx", "gdelt": "UAE stock market ADX DFM"},
    # --- structural / demand ---
    "tourism":           {"label_en": "Tourism & visitors", "label_ar": "السياحة", "wb_series": None, "unit": "idx", "gdelt": "Dubai tourism visitors"},
    "population":        {"label_en": "Population growth", "label_ar": "النمو السكاني", "wb_series": None, "unit": "idx", "gdelt": "UAE population residents"},
    "traffic":           {"label_en": "Road traffic volume", "label_ar": "حركة المرور", "wb_series": None, "unit": "idx", "gdelt": "Dubai traffic congestion"},
    "trade":             {"label_en": "Trade flows", "label_ar": "التجارة", "wb_series": None, "unit": "idx", "gdelt": "global trade exports imports"},
    "power_demand":      {"label_en": "Power & cooling demand", "label_ar": "الطلب على الطاقة", "wb_series": None, "unit": "idx", "gdelt": "electricity cooling demand"},
    "consumer_demand":   {"label_en": "Consumer spending", "label_ar": "الإنفاق الاستهلاكي", "wb_series": None, "unit": "idx", "gdelt": "UAE consumer spending"},
    "ecommerce":         {"label_en": "E-commerce volume", "label_ar": "التجارة الإلكترونية", "wb_series": None, "unit": "idx", "gdelt": "ecommerce delivery"},
    "construction":      {"label_en": "Construction activity", "label_ar": "نشاط البناء", "wb_series": None, "unit": "idx", "gdelt": "UAE construction projects"},
    "occupancy":         {"label_en": "Office / property occupancy", "label_ar": "الإشغال العقاري", "wb_series": None, "unit": "idx", "gdelt": "office occupancy real estate"},
    "health_spend":      {"label_en": "Healthcare spend", "label_ar": "الإنفاق الصحي", "wb_series": None, "unit": "idx", "gdelt": "healthcare spending"},
    "data_demand":       {"label_en": "Data & connectivity demand", "label_ar": "الطلب على البيانات", "wb_series": None, "unit": "idx", "gdelt": "mobile data 5G demand"},
    "ai_capex":          {"label_en": "AI / data-centre capex", "label_ar": "إنفاق الذكاء الاصطناعي", "wb_series": None, "unit": "idx", "gdelt": "AI data center capex"},
    "uae_gov_spend":     {"label_en": "UAE government spending", "label_ar": "الإنفاق الحكومي", "wb_series": None, "unit": "idx", "gdelt": "UAE government budget spending"},
    "satellite_capex":   {"label_en": "Satellite / space capex", "label_ar": "إنفاق الفضاء", "wb_series": None, "unit": "idx", "gdelt": "satellite space investment"},
    "rig_demand":        {"label_en": "Drilling rig demand", "label_ar": "الطلب على الحفر", "wb_series": None, "unit": "idx", "gdelt": "oil drilling rig demand"},
    "oil_services":      {"label_en": "Oilfield services", "label_ar": "خدمات النفط", "wb_series": None, "unit": "idx", "gdelt": "oilfield services"},
}


def factor_meta(key: str) -> dict:
    return FACTORS.get(key, {"label_en": key, "label_ar": key, "wb_series": None, "unit": "idx", "gdelt": key})
