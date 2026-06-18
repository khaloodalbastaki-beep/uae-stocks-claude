#!/usr/bin/env bash
# Deploy the built site to GitHub Pages (mirrors agentec/hypertrophy gh-pages deploys).
# Builds dist/, then pushes it to the PAGES_REPO. The data/ JSON is bundled into the
# site (web/data) by tools/build.sh; phase 2 can split it into a separate DATA_REPO that
# the PWA reads via raw URL + the Mac pulls via launchd.
#
#   PAGES_REPO=khaloodalbastaki-beep/uae-stocks-pages bash tools/deploy.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PAGES_REPO="${PAGES_REPO:-khaloodalbastaki-beep/uae-stocks-pages}"
LIVE_FLAG="${1:-}"

echo "[deploy] building…"
bash tools/build.sh $LIVE_FLAG

TMP="$(mktemp -d)"
echo "[deploy] cloning $PAGES_REPO -> $TMP"
if ! git clone --depth 1 "https://github.com/$PAGES_REPO.git" "$TMP" 2>/dev/null; then
  echo "[deploy] repo not found. Create it first:"
  echo "  gh repo create $PAGES_REPO --public --description 'UAE Stocks Intelligence (PWA)'"
  echo "  then enable Pages on the main branch (root)."
  exit 1
fi

# replace contents with dist/
find "$TMP" -mindepth 1 -maxdepth 1 ! -name '.git' -exec rm -rf {} +
cp -R dist/* "$TMP/"
touch "$TMP/.nojekyll"

cd "$TMP"
git add -A
if git diff --cached --quiet; then
  echo "[deploy] no changes."
else
  git commit -m "deploy: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  git push origin HEAD
  echo "[deploy] pushed -> https://$(echo $PAGES_REPO | cut -d/ -f1).github.io/$(echo $PAGES_REPO | cut -d/ -f2)/"
fi
rm -rf "$TMP"
