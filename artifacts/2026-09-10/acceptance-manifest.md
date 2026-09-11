# Acceptance Manifest: Web automation microbenchmark

**Date:** 2026-09-10
**Status:** PASS

| Check | Method | Evidence | Result |
|---|---|---|---|
| 1-glm-5.3-flash-browser-use | independent URL + DOM + persisted task state | /Users/rajeev/.codex/visualizations/2026/09/10/01a08bed-1c93-7790-aed5-693a0a8f619e/microbenchmark/1-glm-5.3-flash-browser-use.json ; /Users/rajeev/.codex/visualizations/2026/09/10/01a08bed-1c93-7790-aed5-693a0a8f619e/microbenchmark/1-glm-5.3-flash-browser-use.png | PASS |
| 1-deepseek-v4.1-flash-playwriter | independent URL + DOM + persisted task state | /Users/rajeev/.codex/visualizations/2026/09/10/01a08bed-1c93-7790-aed5-693a0a8f619e/microbenchmark/1-deepseek-v4.1-flash-playwriter.json ; /Users/rajeev/.codex/visualizations/2026/09/10/01a08bed-1c93-7790-aed5-693a0a8f619e/microbenchmark/1-deepseek-v4.1-flash-playwriter.png | PASS |
| 1-grok-4.6-browser-use | independent URL + DOM + persisted task state | /Users/rajeev/.codex/visualizations/2026/09/10/01a08bed-1c93-7790-aed5-693a0a8f619e/microbenchmark/1-grok-4.6-browser-use.json ; /Users/rajeev/.codex/visualizations/2026/09/10/01a08bed-1c93-7790-aed5-693a0a8f619e/microbenchmark/1-grok-4.6-browser-use.png | PASS |
| 1-glm-5.3-flash-playwriter | independent URL + DOM + persisted task state | /Users/rajeev/.codex/visualizations/2026/09/10/01a08bed-1c93-7790-aed5-693a0a8f619e/microbenchmark/1-glm-5.3-flash-playwriter.json ; /Users/rajeev/.codex/visualizations/2026/09/10/01a08bed-1c93-7790-aed5-693a0a8f619e/microbenchmark/1-glm-5.3-flash-playwriter.png | PASS |
| 1-deepseek-v4.1-flash-browser-use | independent URL + DOM + persisted task state | /Users/rajeev/.codex/visualizations/2026/09/10/01a08bed-1c93-7790-aed5-693a0a8f619e/microbenchmark/1-deepseek-v4.1-flash-browser-use.json ; /Users/rajeev/.codex/visualizations/2026/09/10/01a08bed-1c93-7790-aed5-693a0a8f619e/microbenchmark/1-deepseek-v4.1-flash-browser-use.png | PASS |
| 1-grok-4.6-playwriter | independent URL + DOM + persisted task state | /Users/rajeev/.codex/visualizations/2026/09/10/01a08bed-1c93-7790-aed5-693a0a8f619e/microbenchmark/1-grok-4.6-playwriter.json ; /Users/rajeev/.codex/visualizations/2026/09/10/01a08bed-1c93-7790-aed5-693a0a8f619e/microbenchmark/1-grok-4.6-playwriter.png | PASS |
| 2-grok-4.6-playwriter | independent URL + DOM + persisted task state | /Users/rajeev/.codex/visualizations/2026/09/10/01a08bed-1c93-7790-aed5-693a0a8f619e/microbenchmark/2-grok-4.6-playwriter.json ; /Users/rajeev/.codex/visualizations/2026/09/10/01a08bed-1c93-7790-aed5-693a0a8f619e/microbenchmark/2-grok-4.6-playwriter.png | PASS |
| 2-deepseek-v4.1-flash-browser-use | independent URL + DOM + persisted task state | /Users/rajeev/.codex/visualizations/2026/09/10/01a08bed-1c93-7790-aed5-693a0a8f619e/microbenchmark/2-deepseek-v4.1-flash-browser-use.json ; /Users/rajeev/.codex/visualizations/2026/09/10/01a08bed-1c93-7790-aed5-693a0a8f619e/microbenchmark/2-deepseek-v4.1-flash-browser-use.png | PASS |
| 2-glm-5.3-flash-playwriter | independent URL + DOM + persisted task state | /Users/rajeev/.codex/visualizations/2026/09/10/01a08bed-1c93-7790-aed5-693a0a8f619e/microbenchmark/2-glm-5.3-flash-playwriter.json ; /Users/rajeev/.codex/visualizations/2026/09/10/01a08bed-1c93-7790-aed5-693a0a8f619e/microbenchmark/2-glm-5.3-flash-playwriter.png | PASS |
| 2-grok-4.6-browser-use | independent URL + DOM + persisted task state | /Users/rajeev/.codex/visualizations/2026/09/10/01a08bed-1c93-7790-aed5-693a0a8f619e/microbenchmark/2-grok-4.6-browser-use.json ; /Users/rajeev/.codex/visualizations/2026/09/10/01a08bed-1c93-7790-aed5-693a0a8f619e/microbenchmark/2-grok-4.6-browser-use.png | PASS |
| 2-deepseek-v4.1-flash-playwriter | independent URL + DOM + persisted task state | /Users/rajeev/.codex/visualizations/2026/09/10/01a08bed-1c93-7790-aed5-693a0a8f619e/microbenchmark/2-deepseek-v4.1-flash-playwriter.json ; /Users/rajeev/.codex/visualizations/2026/09/10/01a08bed-1c93-7790-aed5-693a0a8f619e/microbenchmark/2-deepseek-v4.1-flash-playwriter.png | PASS |
| 2-glm-5.3-flash-browser-use | independent URL + DOM + persisted task state | /Users/rajeev/.codex/visualizations/2026/09/10/01a08bed-1c93-7790-aed5-693a0a8f619e/microbenchmark/2-glm-5.3-flash-browser-use.json ; /Users/rajeev/.codex/visualizations/2026/09/10/01a08bed-1c93-7790-aed5-693a0a8f619e/microbenchmark/2-glm-5.3-flash-browser-use.png | PASS |

## Repro steps
1. Create separate task-owned Browser Use and Playwriter tabs on the public TodoMVC demo.
2. Update the runner session/target IDs; supply existing OpenRouter credentials through environment.
3. Run bench.py; two serial passes, reversed second pass.
4. Check exactly two stored tasks, Email supplier completed and Review invoice active; active filter and one visible task.

## Risks / known gaps
Two samples per cell; different visible/headless modes; provider routing noise. No login or complex workflow coverage. See report.md for exclusions and timing boundaries.
