# Acceptance Manifest: Web automation benchmark extension

**Date:** 2026-09-11
**Status:** PASS (with documented caveats)

| Check | Method | Evidence | Result |
|---|---|---|---|
| Browser Harness rep 1 | independent DOM + persisted state after agent run | results/1-harness.json + 1-harness.png | PASS |
| Browser Harness rep 2 | same | results/2-harness.json + png | PASS |
| BrowserCode rep 1 | same (direct CDP multi-tab scan) | results/1-bcode.json | PASS (state verified; timing/cost recorded) |
| BrowserCode rep 2 | same | results/2-bcode.json | PASS |
| Stagehand rep 1 | same | results/1-stagehand.json | FAIL (literal "Email supplier Enter" title) |
| Stagehand rep 2 | same | results/2-stagehand.json | FAIL (schema-invalid model output) |
| Stagehand rep 3 | same | results/3-stagehand.json | FAIL (same class) |
| Stagehand rep 4 | same | results/4-stagehand.json | PASS |
| Magnitude reps 1–4 | same | results/N-magnitude.json + png | PASS 4/4 |

## Repro
1. `source /Users/rajeev/.config/claude-openrouter/env.sh`
2. Ensure isolated Chrome on 9233 (bcode-data) and 9234 (harness-data) are running.
3. `python3 bench-py.py <rep> harness|bcode` and `node bench-node.mjs stagehand|magnitude <rep>`.
4. Verify `results/<rep>-<contender>.json` → pass field, and per-event transcripts.

## Risks / known gaps
- Two reps per contender (4 for Magnitude/Stagehand) — directional.
- Stagehand+GLM schema mismatch dominated its failure mode; no stronger-model control run.
- bcode cost is OpenRouter-reported; others estimated from exact tokens at latency-provider rates.
