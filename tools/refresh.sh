#!/usr/bin/env bash
# Live refresh (Claude instance): scrape real ADX/DFM delayed quotes -> rebuild -> deploy.
# This is the DECOUPLED copy (~/Projects/uae-stocks-claude) — separate repo, Pages target
# and LaunchAgent from the parallel Codex copy, so the two never collide.
# Khalid explicitly authorised live delayed data here ("make it real time data, read from
# websites, I want you to do it"), so live is the default; set UAE_DISABLE_LIVE=1 to pause.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export UAE_AI_PROVIDER="${UAE_AI_PROVIDER:-stub}"
PAGES_REPO="${PAGES_REPO:-khaloodalbastaki-beep/uae-stocks-live}"

if [ "${UAE_DISABLE_LIVE:-0}" = "1" ]; then
  echo "[refresh] paused via UAE_DISABLE_LIVE=1"; exit 0
fi
export UAE_PROVIDER=live

# Market-hours guard (skip overnight/weekend churn). ADX/DFM trade Mon–Fri ~10:00–15:00 GST.
FORCE="${FORCE:-0}"; NO_DEPLOY=0
for arg in "$@"; do
  [ "$arg" = "--force" ] && FORCE=1
  [ "$arg" = "--no-deploy" ] && NO_DEPLOY=1
done
if [ "$FORCE" != "1" ]; then
  H=$(date +%H); D=$(date +%u)
  if [ "$D" -gt 5 ] || [ "$H" -lt 9 ] || [ "$H" -gt 16 ]; then
    echo "[refresh] $(date '+%a %H:%M') — UAE market closed; skip"; exit 0
  fi
fi

echo "[refresh] export registry symbols…"
python3 -m brain.symbols > data/symbols.json

echo "[refresh] scrape real ADX/DFM delayed quotes…"
( cd scraper && node scrape.mjs ) || echo "[refresh] scrape failed — brain falls back to demo per-symbol"

echo "[refresh] rebuild data (live)…"
python3 -m brain.run --live

echo "[refresh] icons + assemble web/data + dist…"
python3 tools/make_icons.py
rm -rf web/data dist
mkdir -p web/data && cp -R data/* web/data/
rm -f web/data/symbols.json web/data/live_quotes.json   # keep internal scratch out of public site
mkdir -p dist && cp -R web/* dist/
# stamp a per-build cache id into the service worker so deploys supersede stale caches
BUILD_ID="$(date -u +%Y%m%d%H%M%S)"
if [ -f dist/sw.js ]; then sed -i '' "s/__BUILD_ID__/$BUILD_ID/g" dist/sw.js 2>/dev/null || sed -i "s/__BUILD_ID__/$BUILD_ID/g" dist/sw.js; fi

if [ "$NO_DEPLOY" = "1" ]; then echo "[refresh] built; skipping deploy"; exit 0; fi

echo "[refresh] deploy -> $PAGES_REPO…"
TMP="$(mktemp -d)"
if git clone --depth 1 "https://github.com/$PAGES_REPO.git" "$TMP" 2>/dev/null; then
  find "$TMP" -mindepth 1 -maxdepth 1 ! -name '.git' -exec rm -rf {} +
  cp -R dist/* "$TMP/"; touch "$TMP/.nojekyll"
  ( cd "$TMP" && git add -A && (git diff --cached --quiet || git commit -q -m "live refresh $(date -u +%Y-%m-%dT%H:%M:%SZ)") && git push -q origin HEAD )
  echo "[refresh] deployed -> https://$(echo $PAGES_REPO|cut -d/ -f1).github.io/$(echo $PAGES_REPO|cut -d/ -f2)/"
else
  echo "[refresh] could not clone $PAGES_REPO — skipping deploy"
fi
rm -rf "$TMP"
