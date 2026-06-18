#!/usr/bin/env bash
# Hourly cron entrypoint for the Mizan launchd job. Refreshes the N stalest names.
set -uo pipefail
cd "$(cd "$(dirname "$0")/../.." && pwd)"
exec /opt/homebrew/bin/python3 agents/mizan/mizan.py --stale "${1:-4}"
