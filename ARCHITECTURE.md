# Architecture — and why it differs from the Codex build brief

The blueprint ends with a Codex prompt that hardcodes **Next.js + App Router + TypeScript
+ PostgreSQL + Prisma + a queue + Docker + OpenAI Structured Outputs/embeddings.** That is
a fine *enterprise SaaS* spec. It is the wrong spec for **this owner and this moment**, and
it even violates one of the blueprint's own rules ("do not hardcode a single data
provider"). This build keeps the entire *product vision* and re-expresses it on the rails
Khalid actually runs.

## The two architectures side by side

| | Codex literal build | This build (Khalid's ecosystem) |
|---|---|---|
| Frontend | Next.js SSR app | Static PWA (vanilla, no build step) |
| Hosting | Paid Node host | **GitHub Pages — free** |
| Database | PostgreSQL + Prisma | **JSON files in a GitHub repo (GitHub-as-DB)** |
| Jobs | Queue worker service | **launchd on the Mac mini** (`com.bastaki.*`) |
| AI | OpenAI (needs paid key) | **`claude` CLI (Claude Max, free) / stub / openai** |
| Numbers | Mixed model/code | **Deterministic Python only; LLM narrates** |
| Runs offline / AED 0 | No | **Yes** |
| Boot prerequisites | DB + Docker + API key | `python3` (stdlib only) |
| Matches the owner's other apps | No | **Yes — finance, agentec, hypertrophy** |

Both produce: a card-first home, a deep 8-tab stock page, disclosures with bilingual
summaries + materiality/sentiment, board/AGM timelines, dividend intelligence, an exposure
map, watchlist/alerts, an admin/ingestion page, and an explainable short/long-term AI view.

## Data flow

```
                 ┌──────────────────── Mac mini (the "brain") ────────────────────┐
                 │  registry → adapters(ingest) → scoring(deterministic) →         │
   launchd ──▶   │  ai.narrate(LLM prose only) → pipeline.emit → data/*.json       │
   (15 min)      └───────────────────────────────┬────────────────────────────────┘
                                                  │ push (GitHub Contents API)
                                                  ▼
                                   GitHub data repo  (GitHub-as-DB)
                                                  │ read (fetch / raw)
                                                  ▼
                 GitHub Pages static PWA  ──▶  phone / desktop (offline-first, installable)
```

This is byte-for-byte the agentec / hypertrophy pattern: a deterministic Python brain on
the Mac emits plain JSON; a free static PWA reads it; launchd keeps it fresh; the user just
opens it on their phone.

## The deterministic / AI split (the important one)

Khalid's hard rule: *numbers from code, never the LLM.* So:

- **`brain/scoring.py`** computes Growth / Stability / Dividend (0-100), archetype-weighted,
  with a transparent sub-factor breakdown the UI renders as evidence. A bank is scored
  differently from a developer (the blueprint's explicit requirement).
- **`brain/ai/narrate.py` → `compute_signals()`** derives the AI **stance + confidence**
  deterministically from momentum, disclosure novelty, events, and the house scores.
- The AI provider (`claude` / `openai` / `stub`) is handed the *fixed* stance and may only
  **rewrite the prose** of reasons/risks. Turn the AI off entirely and every number and
  every call is identical — you just get template prose instead of model prose. That is the
  whole point, and it's what keeps the app compliant (explainability, not a black-box
  recommendation) and trustworthy.

## Provider-agnostic by construction

`brain/adapters/base.py` defines interfaces + a `Provenance` model; the pipeline composes
implementations. Today: `mock` (demo), `gdelt` (free live), `worldbank` (free live/cached),
and license-gated `exchanges` stubs. Swapping in a licensed ADX/DFM vendor is a one-file
change, never a refactor — satisfying "do not hardcode a provider" properly instead of
hardcoding OpenAI.

## Why this wins for *this* owner

1. **It ships tonight for AED 0** and he can add-to-home-screen it immediately.
2. **It's operationally identical to his other three apps**, so it inherits his deploy
   muscle memory, his launchd conventions, and his free GitHub-Pages route.
3. **It's honest by construction** — deterministic numbers, source provenance, demo
   labelling, SCA-safe framing — which is exactly how he ships to real institutional
   audiences (DP World, RTA, live finance).
4. **The licensed real-time feed is a later switch**, not a launch blocker — matching the
   blueprint's own staged rollout and his free-by-default / paid-path-parked instinct.
