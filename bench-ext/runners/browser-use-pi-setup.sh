#!/usr/bin/env bash
# Reproducible install + version pin for Browser Use Pi (issue #34).
# Result: bench-ext/work/browser-use-pi at the pinned commit below, built (dist/), Node 22.19+.
set -euo pipefail
BASE=/Users/rajeev/code/web-automation-microbench/bench-ext
CLONE="$BASE/work/browser-use-pi"
PIN=fa838f3298673950923bdaf12bd3c1b6279cd119   # @browser_use/pi 0.1.0 (2026-09-13)

if [ ! -d "$CLONE/.git" ]; then
  git clone https://github.com/browser-use/browser-use-pi.git "$CLONE"
fi
cd "$CLONE"
git fetch --quiet origin "$PIN" 2>/dev/null || true
git checkout --quiet "$PIN"
npm install --no-audit --no-fund
npm run build
echo "browser-use-pi ready: $(git rev-parse HEAD) / npm $(node -p "require('./package.json').version") / node $(node -v)"
