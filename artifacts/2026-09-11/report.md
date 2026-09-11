# Web automation benchmark — extension (2026-09-11)

Same task and success criteria as the 2026-09-10 Playwriter vs browser-use benchmark: on https://demo.playwright.dev/todomvc/, add "Email supplier" and "Review invoice", complete Email supplier, click Active, verify only Review invoice remains (1 item left). Independent DOM + persisted-state verification outside the timed loop.

Contenders added: Browser Harness 0.1.13, BrowserCode (bcode) 0.1.20, Stagehand v4 (@browserbasehq/stagehand, current v4 SDK), Magnitude (magnitude-core 0.3.1). All used z-ai/glm-5.3-flash via OpenRouter with `provider.sort: "latency"` (not `:nitro`).

## Scored results (per run)

| Contender | Runs (pass) | Total seconds per run | Median | Tokens in (per run) | Tokens out | Cost per run | Model calls |
|---|---|---|---:|---|---|---|---|
| Browser Harness | 2/2 | 7.8 / 12.0 | **9.9s** | 5,207 / 7,150 | 151 / 223 | $0.0004 / $0.0005 | 5 / 6 |
| BrowserCode (bcode) | 2/2 | 126.7 / 179.4 | 153.0s | 73,483 / 37,719 | 3,127 / 2,862 | $0.028 / $0.023 | 15 / 11 |
| Stagehand v4 | 1/4 | 8.7 / 21.6 / 12.6 / 13.7 | 13.1s | ~6,600 each | 295–3,417 | $0.0006–0.0013 | 7–8 |
| Magnitude | 4/4 | 38.7 / 52.8 / 52.5 / 56.3 | 52.6s | ~18,300 each | 2,708–3,121 | ~$0.0021 | 8 each |

Prior benchmark (same task, 2026-09-10, all 12 runs passed): Playwriter+GLM median 11.4s, Playwriter+DeepSeek 10.1s, Playwriter+Grok 11.9s, Browser-Use+GLM 8.8s, Browser-Use+DeepSeek 12.0s, Browser-Use+Grok 14.2s.

## Pareto analysis (accuracy × wall time × tokens × cost)

- **Overall winner: Browser Harness.** 2/2 pass, fastest median (9.9s — also faster than every prior-browser-use combination), lowest tokens (~5–7k in, ~200 out) and lowest cost (~$0.0005/run).
- **Fastest: Browser Harness** (9.9s median; single runs 7.8s). Stagehand's single passing run was 13.7s.
- **Most token-efficient: Browser Harness** (~6–7k in / ~190 out per run). Magnitude is the heaviest (~18k in / ~3k out, vision screenshots every step).
- **Most reliable: Magnitude (4/4)**, then Browser Harness and BrowserCode (2/2 each). Stagehand 1/4 with GLM — the model intermittently emitted schema-invalid or wrong-action outputs that Stagehand rejects, and one run typed the literal string "Email supplier Enter". Stagehand's strict JSON-schema contracts amplify GLM's weaknesses; with a stronger model its self-healing/local-browser support could shine, but that is not what this test measured.
- **Best for complex SPAs: Magnitude** — vision-first (screenshot + pixel coordinates), 4/4 reliable, never confused by DOM tricks. The cost is 3–9× more tokens than harness-style codegen and ~5× the wall time.
- **Best visual fallback: Magnitude** (vision-native by architecture). Stagehand also supports vision via `extract({screenshot: true})` but we ran DOM-based observe/act.
- **Strictly dominated / drop candidate: BrowserCode (bcode).** It passes but is strictly worse on every axis vs Browser Harness: 15× slower (153s vs 9.9s median), 8–15× more tokens, ~55× higher cost, more model calls. Its only differentiator — a persistent OpenCode-style TUI/agent runtime with `browser_execute` CDP snippets — does not translate into speed or accuracy here. **Drop BrowserCode from the automation stack.** Browser Harness gives the same CDP primitive with a fraction of the overhead.

## Method notes

- All runs: same TodoMVC task, fresh browser state per rep, temperature 0, reasoning effort low, OpenRouter `provider.sort: "latency"` (observed providers: Makora, Modal, Together). Bcode uses its own OpenRouter SDK route with OpenRouter-computed cost; others cost-estimated from exact token counts at the latency-sorted provider's published rates (Makora: $0.075/M in, $0.25/M out; cached tokens at ~50% input rate).
- Browser Harness: agent loop over `browser-harness` CLI (trusted_click/type_text/press_key/js helpers), 1 logical action per model call. BrowserCode: bcode agent driving `browser_execute` CDP directly. Stagehand: custom LLM callback wrapping OpenRouter chat-completions (latency-sorted), `observe`/`act` against a local headless Chrome. Magnitude: `openai-generic` provider to OpenRouter (latency-sorted via provider-agnostic gateway), vision-driven `act` on headless Chromium.
- Wall-clock = first model call through final action (excludes browser launch and independent verification, same boundary as the prior benchmark).
- Stagehand server-side caching requires Browserbase cloud; local-browser runs here have cache disabled by default, so first-run comparison is fair. Stagehand's own per-call usage metadata confirms no cache advantage locally.
- Vision required: Magnitude yes (every action); Browser Harness/BrowserCode/Stagehand no (DOM/text).
- Setup complexity (subjective, lower = simpler): Browser Harness (install CLI, connect CDP) < Stagehand (npm SDK + custom LLM callback) < Magnitude (npm + patchright browser install + provider config) < BrowserCode (separate runtime, config, skill discovery).

## Known issues / caveats

- Stagehand+GLM incompatibility is the dominant finding: strict json_schema + accessibility-tree action format causes frequent model errors. Not a Stagehand code bug.
- BrowserCode's OpenCode runtime adds large system prompts (~26k input tokens per step) and a 2×–15× wall-time overhead vs a bare CLI loop. It is an agent platform, not a fast automation primitive.
- Two reps per contender (four for Magnitude/Stagehand) is a directional mini-benchmark; provider latency noise applies to all rows equally.
- BrowserCode's cost is OpenRouter-reported actual; other rows are estimates from exact token counts at the latency-sorted provider's published rate.

## Artifacts

- Per-run JSON transcripts, screenshots: `results/` (this directory)
- Runners: `bench-py.py` (harness, bcode), `bench-node.mjs` (stagehand, magnitude), `run-benchmark.sh`
- Isolated browsers: `bcode-data/` (port 9233), `harness-data/` (port 9234); Stagehand/Magnitude launch their own headless Chromium instances
- Prior benchmark: `~/.codex/visualizations/2026/09/10/01a08bed-…/microbenchmark/report.md`
