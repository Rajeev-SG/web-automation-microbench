# Web automation microbenchmark — 2026-09-10

Task: in https://demo.playwright.dev/todomvc/, add Email supplier and Review invoice, complete Email supplier, select Active, verify only Review invoice remains with one item left.

12/12 scored runs passed independent DOM/URL/persisted-state checks. Two runs per combination, serial, reversed order for second repetition.

## End-to-end seconds (each run)

| Model | Browser Use | Playwriter |
|---|---:|---:|
| z-ai/glm-5.3-flash | 7.4 / 10.1 | 17.4 / 5.3 |
| deepseek/deepseek-v4.1-flash | 10.4 / 13.6 | 10.6 / 9.6 |
| x-ai/grok-4.6 | 14.2 / 14.2 | 12.1 / 11.6 |

## Timing decomposition

- browser-use: median total browser-operation time per task 4.12s.
- playwriter: median total browser-operation time per task 0.76s.
- deepseek/deepseek-v4.1-flash: median model API round-trip 1.40s across 20 calls; maximum 4.65s.
- x-ai/grok-4.6: median model API round-trip 1.84s across 22 calls; maximum 2.75s.
- z-ai/glm-5.3-flash: median model API round-trip 0.90s across 21 calls; maximum 12.59s.

## Method and limits

- Stopwatch: first model request through final model confirmation; includes model/network/provider latency and native browser CLI calls with post-action observations. Excludes browser launch, initial navigation/reset, independent final verification and evidence screenshot.
- Same lightweight JSON-code agent loop, temperature 0, requested reasoning low, max_tokens 2200, OpenRouter default provider routing with provider fallback allowed; no model substitution. Four logical actions, observing between each. Models generated native Python or JavaScript, not a pre-written task replay.
- Browser Use installed local harness (browser-use CLI 0.1.10), NOT browser_use.Agent; dedicated visible Chrome for Testing. Playwriter 0.5.0 with isolated headless Chrome, not the extension path. Therefore this compares practical local routes, not identical rendering modes or unmodified end-user Codex task runtimes.
- Browser Use trusted_click includes a default 0.6s verification wait plus snapshots. This is included in its operation timing. Playwriter uses native locators and accessibility snapshots.
- GLM routed through Together/Parasail; DeepSeek through DeepSeek; Grok through xAI. GLM had a 12.59s final-confirmation API outlier in the first Playwriter run. Provider effects are part of end-to-end results.
- Grok initially emitted literal placeholder code in both Playwriter runs and recovered after receiving the syntax error; those retries remain included.
- Pilot runs excluded: Browser Use briefing incorrectly capitalized Enter as ENTER. Corrected and manually verified input before scored runs; initial no-fallback GLM requests also hit HTTP 429. One interrupted restart was unscored. Scored runs all used the corrected same harness.
- Small public demo: no authentication, uploads, real-world menus, visual reasoning, or complex navigation tested. Two repetitions are directional, not statistically robust.
- Raw model call round-trip timings are directly measured benchmark workload evidence; not Codex session telemetry or pure server inference latency. No cost/token claim.
- Final screenshots saved per run; representative Browser Use and Playwriter screenshots visually inspected. Demo origin initially had empty localStorage in Browser Use; benchmark-created storage removed and only benchmark-created pages closed.

## Evidence

- results.json: scored transcripts, actual response model/provider/request IDs, per-step timings, final assertions.
- Individual run JSON and PNG files: model commands, observations and screenshots.
- bench.py: minimal runner; credentials read from the existing environment, never saved in artifacts. Its session/target identifiers must be replaced with new task-owned ones for reproduction.
