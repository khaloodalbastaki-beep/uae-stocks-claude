# UAE Stocks Intelligence — Agent Fleet (manager: Claude Code)

The app delegates the *narration/classification* work (never the numbers) to Khalid's local
CLI agents. Each has a defined role, a detailed task, a cadence, and a clear boundary.
All are invoked as `<agent> chat -Q -q "<prompt>"`; the brain wraps them via
`brain/ai/provider.py:CliAgentProvider` (`UAE_AI_PROVIDER=cli:<agent>`).

**Hard boundary for every agent:** numbers, scores, stance and confidence come from the
deterministic engine. Agents only write prose / classify / review. They never invent a
figure and never change a stance.

## Active (working today — Nous, free)

| Agent | Model | Role in this project | Task | Cadence | Status |
|---|---|---|---|---|---|
| **nemotron** | nvidia/nemotron-3-ultra:free | **Analyst** | Write the AI-Analysis tab reasons/risks/what-would-change prose around the FIXED deterministic stance, qualitative only. `python3 -m brain.analyst --stale 4` → `data/ai/<SYM>.json`; build overlays it; UI shows "narrated by nemotron". | hourly (cron, 4 stalest) | ✅ live & verified |
| **freeagent** | stepfun/step-3.7-flash:free | **News editor / backup analyst** | Classify a headline's sentiment + one-line "why it matters"; or stand in as Analyst (`ANALYST_AGENT=freeagent`). | on demand / standby | ✅ tested, ready |
| **robin** | stepfun/step-3.7-flash:free | **Watcher / QA** | Khalid's existing fleet watcher; here: sanity-check a deployed build (counts, no-fabrication, staleness) and flag anomalies. | on demand | ✅ tested |

## Assigned but BLOCKED on the ZenMux key

Run `~/.hermes/scripts/set_zenmux_key.sh` on the Mac and paste the ZenMux API key (writes
`ZENMUX_API_KEY` into the three profiles). Until then these exit without a key.

| Agent | Model | Role assigned | Task (once unblocked) |
|---|---|---|---|
| **glm52** | z-ai/glm-5.2 | **Deep reviewer** | Adversarial second-opinion: read a stock's scores + analysis and flag where the deterministic read looks weak or the prose overreaches. `cli:glm52`. |
| **kimi27** | moonshotai/kimi-k2.7-code | **Code/structured** | Generate/repair source adapters + do strict structured extraction (it's a code model) — e.g. parse a new IR page format into the `reported{}` schema. |
| **step37** | stepfun/step-3.7-flash | **Fast classifier** | Bulk news/disclosure tagging (event_type, materiality) at speed. Note: the same model is free via Nous (`freeagent`), so this role runs on freeagent until the ZenMux key lands. |

## How the manager (Claude Code) follows up
- **nemotron** runs hourly via `com.bastaki.mizan-refresh` (alongside Mizan fundamentals +
  GDELT news), staleness-rotated 4/run so it never re-narrates a fresh name and stays in the
  free rate limit. Logs: `data/mizan.log`.
- Verify any agent quickly: `nemotron chat -Q -q "Reply ok"`.
- Re-narrate one name now: `python3 -m brain.analyst --symbols EMAAR`.
- Bus dispatch (Hermes): drop a request in `_Bus/inbox/mizan/` (Mizan) — analyst/news are
  cron-driven; add a bus hook if on-demand dispatch is wanted.
- When the ZenMux key is set, flip glm52/kimi27 on by setting their role env (e.g.
  `ANALYST_AGENT=glm52` for a stronger narrator, or wire glm52 as a review pass).

## Why these and not the `claude` CLI
The local `claude` CLI lane returns 401 (not signed in for headless), so the fleet's free
Nous agents (nemotron/freeagent/robin) are the working narration lane — no Claude-Max quota,
no keys. gpt-oss:120b (Ollama Cloud) stays the fundamentals extractor; nemotron is the prose.
