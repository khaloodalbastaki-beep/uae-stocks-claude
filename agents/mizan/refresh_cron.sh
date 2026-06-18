#!/usr/bin/env bash
# Hourly cron entrypoint: refresh the N stalest fundamentals (Mizan) + M stalest news (GDELT),
# staleness-rotated so neither repeats a freshly-touched name and both stay inside free limits.
# Updates data/fundamentals/ + data/news/; the 15-min price refresh rebuilds+deploys them.
set -uo pipefail
cd "$(cd "$(dirname "$0")/../.." && pwd)"
PY=/opt/homebrew/bin/python3
"$PY" agents/mizan/mizan.py --stale "${1:-4}" || true       # Mizan (gpt-oss): fundamentals
"$PY" -m brain.news --stale "${2:-6}" || true                # news (GDELT): live media
"$PY" -m brain.analyst --stale "${3:-4}" || true             # Analyst (nemotron): AI-tab prose
