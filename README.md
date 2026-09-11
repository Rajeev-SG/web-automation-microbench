# Web Automation Microbenchmarks

Mini-benchmarks of practical browser automation harnesses on the same task, same success criteria, same measurement boundaries. These are directional comparisons that feed the future real-corpus benchmark; raw run artifacts are preserved for audit.

## Contenders covered so far

### Round 1 — 2026-09-10 (Playwriter vs Browser Use)

| Harness | Models | Pass | Median task time |
|---|---|---|---:|
| Browser Use 0.1.10 | GLM-5.3-Flash, DeepSeek-V4.1-Flash, Grok-4.6 | 12/12 | 8.8–14.2s |
| Playwriter 0.5.0 | same | 12/12 | 10.1–11.9s |

Tool verdict: Playwriter browser ops ~5.4× faster. Model: GLM fastest typical response but noisy; DeepSeek steadier.

### Round 2 — 2026-09-11 (Browser Harness, BrowserCode, Stagehand v4, Magnitude)

| Contender | Pass | Median time | Tokens in/out | Cost/run |
|---|---|---:|---:|---:|
| Browser Harness 0.1.13 | 2/2 | 9.9s | ~6.2k / ~190 | $0.0005 |
| Stagehand v4 | 1/4 | 13.1s | ~6.6k / 295–3,417 | ~$0.0007 |
| Magnitude 0.3.1 | 4/4 | 52.6s | ~18.3k / ~3.0k | ~$0.0021 |
| BrowserCode 0.1.20 | 2/2 | 153.0s | ~55k / ~3.0k | ~$0.026 |

All on z-ai/glm-5.3-flash via OpenRouter with `provider.sort: "latency"` (not `:nitro`).

## Combined Pareto verdict (across both rounds)

| Verdict | Winner |
|---|---|
| Overall winner | **Browser Harness** (fastest, cheapest, 2/2) |
| Fastest | Browser Harness (9.9s median) |
| Most token-efficient | Browser Harness (~6k in / 190 out per run) |
| Most reliable | Magnitude (4/4) |
| Best for complex SPAs | Magnitude (vision-first) |
| Best visual fallback | Magnitude |
| Strictly dominated — drop | **BrowserCode** (15× slower, ~55× cost vs Harness, no offsetting capability) |

Known caveat: Stagehand's strict JSON-schema contracts expose GLM-5.3-Flash's schema-reliability weakness — not a Stagehand bug, but don't pair them without a stronger model.

## Task

On https://demo.playwright.dev/todomvc/: add "Email supplier" and "Review invoice", complete ONLY "Email supplier", click Active, verify only "Review invoice" remains (1 item left). Independent DOM + persisted-state verification outside the timed loop.

## Method highlights

- Temperature 0, reasoning effort low, one logical UI action per model call.
- `provider.sort: "latency"` on OpenRouter for all Round 2 runs (not `:nitro`); default routing in Round 1.
- Wall-clock: first model call through final action; excludes browser launch, navigation, independent verification.
- Stagehand's server-side cache is Browserbase-cloud-only, so local first-run comparisons are un-warmed by construction.
- Two reps per cell (four for Magnitude/Stagehand in Round 2) — directional mini-benchmark, not a scored corpus run.

## Repo layout

- `artifacts/2026-09-10/` — Round 1 raw run JSON, screenshots, results.json, report, acceptance manifest, runner (bench.py).
- `artifacts/2026-09-11/` — Round 2 per-run JSON + screenshots (results/), runners (bench-py.py, bench-node.mjs, run-benchmark.sh), report, acceptance manifest.

## Reproducing

1. `export OPENROUTER_API_KEY=...` (never commit).
2. Round 1: edit session/target IDs in `artifacts/2026-09-10/bench.py`, ensure Browser Use + Playwriter sessions exist, run `python3 bench.py`.
3. Round 2: ensure isolated Chrome on ports 9233 (bcode) and 9234 (harness); `source` credentials; `python3 bench-py.py <rep> harness|bcode`; `node bench-node.mjs stagehand|magnitude <rep>`.
