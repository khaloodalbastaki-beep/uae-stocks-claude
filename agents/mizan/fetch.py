"""
Gemini-free grounding for Mizan: gather REAL page text for a company so the gpt-oss:120b
extractor works from sourced text, not from memory. No API key, no Gemini quota.

Two sources, combined:
  1. The company's known filing/IR URL (from its existing fundamentals record's source_url),
     rendered with headless Chromium (scraper/fetch_page.mjs) — gets past JS/Cloudflare.
  2. Wikipedia plain-text extract (urllib, no key) — a reliable fallback that carries
     revenue/net-income for most large UAE listcos.

Returns combined text (capped) or None. The extractor then transcribes only what's in the
text and cites it — and returns found=false if the figures aren't there (never fabricates).
"""
from __future__ import annotations

import json
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
FETCH_JS = ROOT / "scraper" / "fetch_page.mjs"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def _render_url(url: str, timeout: float = 50) -> str | None:
    if not url or not FETCH_JS.exists():
        return None
    try:
        res = subprocess.run(["node", str(FETCH_JS), url], capture_output=True, text=True, timeout=timeout)
        out = (res.stdout or "").strip()
        return out if len(out) > 120 else None
    except Exception as e:  # noqa: BLE001
        print(f"[mizan.fetch] render failed ({e})")
        return None


def _wikipedia(name: str, timeout: float = 12) -> str | None:
    try:
        # resolve the best title
        s = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(name)}&format=json&srlimit=1"
        req = urllib.request.Request(s, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            hits = json.loads(r.read().decode("utf-8", "replace")).get("query", {}).get("search", [])
        if not hits:
            return None
        title = hits[0]["title"]
        e = (f"https://en.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext=1"
             f"&titles={urllib.parse.quote(title)}&format=json&exsectionformat=plain")
        req = urllib.request.Request(e, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            pages = json.loads(r.read().decode("utf-8", "replace")).get("query", {}).get("pages", {})
        for _, p in pages.items():
            ext = p.get("extract", "")
            if ext:
                return f"[Wikipedia: {title}]\n{ext[:5000]}"
    except Exception as e:  # noqa: BLE001
        print(f"[mizan.fetch] wikipedia failed ({e})")
    return None


def gather_text(name_en: str, source_url: str | None = None) -> str | None:
    parts = []
    rendered = _render_url(source_url) if source_url else None
    if rendered:
        parts.append(f"[Source filing/IR page: {source_url}]\n{rendered[:6000]}")
    wiki = _wikipedia(name_en)
    if wiki:
        parts.append(wiki)
    if not parts:
        return None
    return "\n\n---\n\n".join(parts)[:9000]
