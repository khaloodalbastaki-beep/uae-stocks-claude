"""
JSON schemas for the AI layer. The blueprint mandates structured JSON for every
extraction ("Use structured JSON outputs for all extraction ... event classification,
summary, materiality, and impact assessment").

These schemas are shared by every provider (claude CLI / OpenAI / stub), so output shape
is identical regardless of which lane is active — the UI never sees a provider-specific
quirk.
"""
from __future__ import annotations

EVENT_TYPES = [
    "results", "board_meeting", "agm_invitation", "agm_resolution", "dividend",
    "acquisition", "capital_raise", "governance", "subsidiary", "other",
]
SENTIMENTS = ["positive", "neutral", "cautious", "negative"]
STANCES = ["Bullish", "Neutral", "Cautious"]
CONFIDENCE = ["low", "medium", "high"]

DISCLOSURE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["event_type", "summary_en", "summary_ar", "why_it_matters",
                 "materiality", "sentiment", "linked_entities"],
    "properties": {
        "event_type": {"type": "string", "enum": EVENT_TYPES},
        "summary_en": {"type": "string"},
        "summary_ar": {"type": "string"},
        "why_it_matters": {"type": "string"},
        "materiality": {"type": "integer", "minimum": 0, "maximum": 100},
        "sentiment": {"type": "string", "enum": SENTIMENTS},
        "linked_entities": {"type": "array", "items": {"type": "string"}},
    },
}

# AI Analysis — note: it must NOT invent house scores; those are passed in from the
# deterministic engine and the model may only reason over them.
ANALYSIS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["short_term", "long_term"],
    "properties": {
        "short_term": {
            "type": "object", "additionalProperties": False,
            "required": ["stance", "confidence", "reasons", "risks", "what_would_change_view"],
            "properties": {
                "stance": {"type": "string", "enum": STANCES},
                "confidence": {"type": "string", "enum": CONFIDENCE},
                "reasons": {"type": "array", "items": {"type": "string"}, "maxItems": 5},
                "risks": {"type": "array", "items": {"type": "string"}, "maxItems": 5},
                "what_would_change_view": {"type": "string"},
            },
        },
        "long_term": {
            "type": "object", "additionalProperties": False,
            "required": ["stance", "confidence", "reasons", "risks", "what_would_change_view"],
            "properties": {
                "stance": {"type": "string", "enum": STANCES},
                "confidence": {"type": "string", "enum": CONFIDENCE},
                "reasons": {"type": "array", "items": {"type": "string"}, "maxItems": 5},
                "risks": {"type": "array", "items": {"type": "string"}, "maxItems": 5},
                "what_would_change_view": {"type": "string"},
            },
        },
    },
}
