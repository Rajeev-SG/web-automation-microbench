#!/bin/bash
# Extended benchmark: Browser Harness, BrowserCode, Stagehand v4, Magnitude
# Same task/methodology as the 2026-09-10 Playwriter vs browser-use benchmark.
set -uo pipefail
BASE=/Users/rajeev/.codex/visualizations/2026/09/11/01a09153-79f1-7be2-bf68-f8d575dbcc84/extend-benchmark
RES=$BASE/results
mkdir -p "$RES"
source /Users/rajeev/.config/claude-openrouter/env.sh
export OPENROUTER_API_KEY
cd "$BASE"
REPS="${REPS:-2}"
python3 "$BASE/bench.py" "$REPS" 2>&1
