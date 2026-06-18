"""
Provider-agnostic AI layer.

Khalid's ecosystem rules drive the design:
  - Free-by-default; paid path built-but-parked. -> default provider is the FREE owned
    lane (the `claude` CLI he already runs on the Mac, authenticated with Claude Max),
    or the deterministic `stub` when offline. OpenAI is supported but never the default
    and never hardcoded with a key.
  - Numbers from code, never the LLM. -> this layer is forbidden from producing house
    scores; it only narrates structured inputs (see narrate.py).
  - Robust/idempotent + honest reporting. -> forced JSON, schema-validated, retried; the
    provider that actually produced each field is recorded in provenance.

Select with env var:
    UAE_AI_PROVIDER = stub (default) | claude | openai

`stub` is fully deterministic and needs no network/key, so the whole app builds offline
for AED 0. `claude` shells out to `claude -p ... --output-format json`. `openai` calls
the Responses API with response_format=json_schema (only if OPENAI_API_KEY is set).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.request


class AIProvider:
    name = "base"

    def complete_json(self, system: str, user: str, schema: dict) -> dict | None:
        raise NotImplementedError


def _extract_json(text: str) -> dict | None:
    """Best-effort: parse the first JSON object found in a text blob."""
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    # strip code fences
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    # first balanced-looking object
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


class StubProvider(AIProvider):
    """Deterministic narration produced by narrate.py's fallbacks — no model call.

    The stub returns None so callers use their deterministic fallback path. This keeps the
    'no key, no network, still works' guarantee while being fully honest that no LLM ran.
    """
    name = "stub"

    def complete_json(self, system: str, user: str, schema: dict) -> dict | None:
        return None


class ClaudeCliProvider(AIProvider):
    """Free owned lane: drives the local `claude` CLI headlessly with forced JSON.

    Verified traps baked in (grounding research §5):
      * `claude -p --output-format json` returns an ENVELOPE; the model text is the
        `result` field, itself a serialized string → parse twice.
      * The CLI exits 0 EVEN ON AUTH FAILURE → branch on the envelope's `is_error`,
        never on the exit code.
      * NEVER set ANTHROPIC_API_KEY here — that silently switches the Max subscription
        to paid metered billing. Unattended auth uses CLAUDE_CODE_OAUTH_TOKEN
        (`claude setup-token`), set in the launchd plist, not an API key.
    """
    name = "claude"

    def __init__(self, model: str | None = None, timeout: float = 90.0):
        self.model = model or os.environ.get("UAE_AI_MODEL", "sonnet")
        self.timeout = timeout

    def complete_json(self, system: str, user: str, schema: dict) -> dict | None:
        prompt = (
            f"{system}\n\n"
            "Respond with a SINGLE JSON object and nothing else. It MUST validate against "
            "this JSON schema:\n"
            f"{json.dumps(schema)}\n\n"
            f"INPUT:\n{user}\n\nJSON:"
        )
        # keep this lane free: strip any inherited paid-API key for the subprocess
        env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
        cmd = ["claude", "-p", prompt, "--output-format", "json"]
        if self.model:
            cmd += ["--model", self.model]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True,
                                 timeout=self.timeout, env=env)
            envelope = _extract_json(res.stdout) or {}
            # branch on is_error, NOT the exit code (it stays 0 on auth failure)
            if envelope.get("is_error") or envelope.get("api_error_status"):
                print(f"[ai:claude] envelope error: {envelope.get('api_error_status') or envelope}")
                return None
            inner = envelope.get("result", res.stdout)
            return _extract_json(inner if isinstance(inner, str) else json.dumps(inner))
        except FileNotFoundError:
            print("[ai:claude] `claude` CLI not found; falling back to stub")
            return None
        except subprocess.TimeoutExpired:
            print("[ai:claude] timed out; falling back to stub")
            return None
        except Exception as e:  # noqa: BLE001
            print(f"[ai:claude] error {e}; falling back to stub")
            return None


class OpenAIProvider(AIProvider):
    """Optional paid lane — only active if OPENAI_API_KEY is present. Never default."""
    name = "openai"

    def __init__(self, model: str | None = None, timeout: float = 60.0):
        self.key = os.environ.get("OPENAI_API_KEY", "")
        self.model = model or os.environ.get("UAE_AI_MODEL", "gpt-4o-mini")
        self.timeout = timeout

    def complete_json(self, system: str, user: str, schema: dict) -> dict | None:
        if not self.key:
            print("[ai:openai] no OPENAI_API_KEY; falling back to stub")
            return None
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "extraction", "schema": schema, "strict": False},
            },
        }
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(body).encode(),
            headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                payload = json.loads(r.read().decode())
            content = payload["choices"][0]["message"]["content"]
            return _extract_json(content)
        except Exception as e:  # noqa: BLE001
            print(f"[ai:openai] error {e}; falling back to stub")
            return None


def get_provider() -> AIProvider:
    choice = os.environ.get("UAE_AI_PROVIDER", "stub").lower()
    if choice == "claude":
        return ClaudeCliProvider()
    if choice == "openai":
        return OpenAIProvider()
    return StubProvider()
