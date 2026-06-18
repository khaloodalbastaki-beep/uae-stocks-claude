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


def text(provider: str, system: str, user: str, *, grounded: bool = True) -> str | None:
    """Return raw TEXT from a named provider (used by the hybrid fetch step). Only gemini
    supports live grounding; others answer from training."""
    provider = (provider or "gemini").lower()
    if provider == "gemini":
        return _gemini_text(system, user, grounded)
    # non-gemini: reuse the JSON lanes but ask for prose (wrap as a 'text' field)
    out = complete_with(provider, system, user + "\n\nReturn JSON {\"text\": \"<your findings>\"}.", grounded=False)
    return (out or {}).get("text") if isinstance(out, dict) else None


def complete_with(provider: str, system: str, user: str, *, grounded: bool = True) -> dict | None:
    """complete() but with an explicit provider (used by hybrid mode)."""
    provider = (provider or "gemini").lower()
    if provider == "gemini":
        return _gemini(system, user, grounded)
    if provider == "groq":
        return _groq(system, user)
    if provider == "openrouter":
        return _openrouter(system, user)
    if provider == "ollama":
        return _ollama(system, user)
    print(f"[mizan.llm] unknown provider {provider}")
    return None


def complete(system: str, user: str, *, grounded: bool = True) -> dict | None:
    """Return a parsed JSON object from the active provider, or None on failure."""
    provider = os.environ.get("MIZAN_PROVIDER", "gemini").lower()
    if provider == "gemini":
        return _gemini(system, user, grounded)
    if provider == "groq":
        return _groq(system, user)
    if provider == "openrouter":
        return _openrouter(system, user)
    if provider == "ollama":
        return _ollama(system, user)
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


def _gemini_text(system: str, user: str, grounded: bool) -> str | None:
    """Grounded gemini call returning raw TEXT (for the hybrid fetch step)."""
    key = os.environ.get("GEMINI_API_KEY", "").strip() or os.environ.get("MIZAN_FETCH_KEY", "").strip()
    if not key:
        print("[mizan.llm] GEMINI_API_KEY (fetch) missing")
        return None
    model = os.environ.get("MIZAN_FETCH_MODEL", "gemini-2.0-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    body = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 2048},
    }
    if grounded:
        body["tools"] = [{"google_search": {}}]
    try:
        resp = _post(url, body, {})
        parts = resp["candidates"][0]["content"]["parts"]
        return "".join(p.get("text", "") for p in parts) or None
    except Exception as e:  # noqa: BLE001
        print(f"[mizan.llm] gemini(text) error: {e}")
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


def _ollama(system: str, user: str) -> dict | None:
    """Ollama lane — OpenAI-compatible. Two modes via OLLAMA_HOST:
      * Ollama Cloud (default, stronger models): OLLAMA_HOST=https://ollama.com + OLLAMA_API_KEY
        (free tier; models like gpt-oss:120b, qwen3-coder:480b, deepseek-v3.1:671b).
      * Local Ollama: OLLAMA_HOST=http://localhost:11434 (no key) — uses your local qwen3 etc.
    Both expose <host>/v1/chat/completions."""
    host = os.environ.get("OLLAMA_HOST", "https://ollama.com").rstrip("/")
    key = os.environ.get("OLLAMA_API_KEY", "").strip()
    if "ollama.com" in host and not key:
        print("[mizan.llm] OLLAMA_API_KEY missing for Ollama Cloud — add it to agents/mizan/.env "
              "(get one at https://ollama.com/settings/keys)")
        return None
    model = os.environ.get("MIZAN_MODEL", "gpt-oss:120b" if "ollama.com" in host else "qwen3:8b")
    body = {
        "model": model, "temperature": 0.1, "stream": False,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
    }
    headers = {}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    try:
        resp = _post(f"{host}/v1/chat/completions", body, headers, timeout=120)
        return _extract_json(resp["choices"][0]["message"]["content"])
    except Exception as e:  # noqa: BLE001
        print(f"[mizan.llm] ollama error: {e}")
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
