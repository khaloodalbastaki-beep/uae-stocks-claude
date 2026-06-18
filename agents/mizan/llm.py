"""
Mizan's free-cloud-LLM client. Provider-agnostic, stdlib-only (urllib), no SDK.

Recommended lane = GEMINI with Google-Search grounding: gemini-2.0-flash can run a live
web search and extract figures grounded in real sources — so Mizan transcribes what was
actually reported, not what the model "remembers". Free tier, no card.
Fallback lane = GROQ (llama-3.3-70b): fast + free, but NOT grounded — use only with
already-fetched filing text passed in `source_text`.

Select with MIZAN_PROVIDER = gemini (default) | groq | openrouter.
Keys: GEMINI_API_KEY | GROQ_API_KEY | OPENROUTER_API_KEY (whichever provider is active).
"""
from __future__ import annotations

import json
import os
import re
import urllib.request


def _extract_json(text: str) -> dict | None:
    if not text:
        return None
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    start = text.find("{")
    if start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i + 1])
                    except Exception:
                        break
    return None


def _post(url: str, body: dict, headers: dict, timeout: float = 60) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def complete(system: str, user: str, *, grounded: bool = True) -> dict | None:
    """Return a parsed JSON object from the active provider, or None on failure."""
    provider = os.environ.get("MIZAN_PROVIDER", "gemini").lower()
    if provider == "gemini":
        return _gemini(system, user, grounded)
    if provider == "groq":
        return _groq(system, user)
    if provider == "openrouter":
        return _openrouter(system, user)
    print(f"[mizan.llm] unknown provider {provider}")
    return None


def _gemini(system: str, user: str, grounded: bool) -> dict | None:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        print("[mizan.llm] GEMINI_API_KEY missing — add it to agents/mizan/.env")
        return None
    model = os.environ.get("MIZAN_MODEL", "gemini-2.0-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    body = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 2048},
    }
    if grounded:
        body["tools"] = [{"google_search": {}}]  # live grounding
    try:
        resp = _post(url, body, {})
        parts = resp["candidates"][0]["content"]["parts"]
        text = "".join(p.get("text", "") for p in parts)
        return _extract_json(text)
    except Exception as e:  # noqa: BLE001
        print(f"[mizan.llm] gemini error: {e}")
        return None


def _groq(system: str, user: str) -> dict | None:
    key = os.environ.get("GROQ_API_KEY", "").strip()
    if not key:
        print("[mizan.llm] GROQ_API_KEY missing — add it to agents/mizan/.env")
        return None
    model = os.environ.get("MIZAN_MODEL", "llama-3.3-70b-versatile")
    body = {
        "model": model, "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
    }
    try:
        resp = _post("https://api.groq.com/openai/v1/chat/completions", body,
                     {"Authorization": f"Bearer {key}"})
        return _extract_json(resp["choices"][0]["message"]["content"])
    except Exception as e:  # noqa: BLE001
        print(f"[mizan.llm] groq error: {e}")
        return None


def _openrouter(system: str, user: str) -> dict | None:
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        print("[mizan.llm] OPENROUTER_API_KEY missing — add it to agents/mizan/.env")
        return None
    model = os.environ.get("MIZAN_MODEL", "meta-llama/llama-3.3-70b-instruct:free")
    body = {"model": model, "temperature": 0.1,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    try:
        resp = _post("https://openrouter.ai/api/v1/chat/completions", body,
                     {"Authorization": f"Bearer {key}"})
        return _extract_json(resp["choices"][0]["message"]["content"])
    except Exception as e:  # noqa: BLE001
        print(f"[mizan.llm] openrouter error: {e}")
        return None
