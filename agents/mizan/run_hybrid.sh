#!/usr/bin/env bash
# One command: after you paste a free Gemini key into agents/mizan/.env (and uncomment the
# two MIZAN_FETCH_PROVIDER / GEMINI_API_KEY lines), this runs the HYBRID extraction over the
# whole universe (Gemini grounds the real sourced figures → gpt-oss:120b structures them)
# and deploys. Mizan only writes a symbol when it has sourced revenue+net_income, so it never
# downgrades a good record to a guess.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
if ! grep -Eq '^GEMINI_API_KEY=.+' agents/mizan/.env; then
  echo "✗ No Gemini key yet. In agents/mizan/.env, uncomment these two lines and paste your key:"
  echo "    MIZAN_FETCH_PROVIDER=gemini"
  echo "    GEMINI_API_KEY=AIza...   (free: https://aistudio.google.com/apikey)"
  exit 1
fi
if ! grep -Eq '^MIZAN_FETCH_PROVIDER=gemini' agents/mizan/.env; then
  echo "✗ Add this line to agents/mizan/.env to turn on hybrid:  MIZAN_FETCH_PROVIDER=gemini"
  exit 1
fi
echo "[hybrid] Gemini-grounded fetch → gpt-oss:120b extract, over the whole universe…"
python3 agents/mizan/mizan.py --all
echo "[hybrid] deploying live…"
PAGES_REPO=khaloodalbastaki-beep/uae-stocks-live bash tools/refresh.sh --force
echo "[hybrid] done → https://khaloodalbastaki-beep.github.io/uae-stocks-live/"
