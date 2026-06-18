#!/usr/bin/env bash
# Build the static site: run the brain, copy emitted JSON into web/data, icons, and a
# self-contained dist/. Mirrors agentec's web/ -> dist/ build.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

LIVE_FLAG=""
[ "${1:-}" = "--live" ] && LIVE_FLAG="--live"

echo "[build] generating data (brain)…"
python3 -m brain.run $LIVE_FLAG

echo "[build] icons…"
python3 tools/make_icons.py

echo "[build] assembling web/data + dist/…"
rm -rf web/data dist
mkdir -p web/data
cp -R data/* web/data/
# never ship internal scrape scratch in the public site
rm -f web/data/symbols.json web/data/live_quotes.json

mkdir -p dist
cp -R web/* dist/
echo "[build] done -> web/ (preview) and dist/ (deploy)"
