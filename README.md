# Web Automation Microbenchmarks

Short, practical head-to-head races between browser automation tools. Every tool gets the same task, the same browser situation, and the same success test — then we measure who finishes reliably, quickly, cheaply, and with the least AI overhead.

**Read this if you want the one-paragraph answer:** a thin harness that lets the model write code against the browser (Browser Harness) beats everything else on speed and cost. A vision-first agent (Magnitude) is the most reliable and the best choice for messy, JavaScript-heavy sites — but it costs more tokens and is slower. Anything that ships its own heavyweight agent runtime (BrowserCode) costs 10–100× more for no accuracy gain. Two of the six tools tested dominate the practical frontier; two are dominated and can be dropped.

## The test task

Every round uses the same job on a public demo app (TodoMVC):

1. Add two to-dos: "Email supplier" and "Review invoice".
2. Tick off only "Email supplier".
3. Switch to the "Active" filter.
4. Confirm only "Review invoice" is showing, with "1 item left".

Passing is checked by independent code reading the page and the app's saved data — not by the agent's own say-so. The stopwatch covers just the model+browser work (from first model call to the agent saying "done"), not browser startup or the checking step. Full contract: [docs/benchmark-spec.md](docs/benchmark-spec.md).

## Round 1 — 10 Sep 2026: Playwriter vs Browser Use

Three cheap OpenRouter models, two browser harnesses, two runs each. **All 12 runs passed.**

| Model | Browser Use | Playwriter |
|---|---|---|
| GLM 5.3 Flash | 7.4s / 10.1s | 17.4s / 5.3s |
| DeepSeek V4.1 Flash | 10.4s / 13.6s | 10.6s / 9.6s |
| Grok 4.6 | 14.2s / 14.2s | 12.1s / 11.6s |

What mattered:
- **Playwriter's browser actions were ~5× faster** than Browser Use's (0.76s vs 4.12s per task) because it runs one code snippet instead of many round-trips.
- GLM was the fastest model per call (0.90s median) but had a 12.6s provider hiccup once. DeepSeek was the steadiest. Grok was never the fastest.
- Browser Use's verification-wait adds real time per click.

Details: [artifacts/2026-09-10/report.md](artifacts/2026-09-10/report.md)

## Round 2 — 11 Sep 2026: four new contenders

All on GLM 5.3-Flash via OpenRouter with **latency-sorted provider routing** (not throughput-sorted "nitro").

| Contender | What it is | Pass | Median time | Tokens in/out | Cost per run |
|---|---|---|---:|---:|---:|
| **Browser Harness** | Thin CLI that lets the model write browser code via one CDP connection | 2/2 | **9.9s** | ~6.2k / ~190 | **$0.0005** |
| **Stagehand v4** | SDK with observe/act/extract and strict JSON contracts | 1/4 | 13.1s | ~6.6k / 300–3,400 | ~$0.0007 |
| **Magnitude** | Vision-first agent; looks at screenshots, clicks pixel coordinates | 4/4 | 52.6s | ~18.3k / ~3.0k | ~$0.0021 |
| **BrowserCode** | Full OpenCode-style agent runtime with browser tools | 2/2 | 153.0s | ~55k / ~3.0k | ~$0.026 |

For comparison, the prior round's best times: browser-use+GLM 8.8s, Playwriter+DeepSeek 10.1s, Playwriter+GLM 11.4s.

Details: [artifacts/2026-09-11/report.md](artifacts/2026-09-11/report.md)

## Round 3 — 12 Sep 2026: the lightweight field, plus a raw code-mode baseline

Sixteen more contenders, same task, same GLM 5.3-Flash on OpenRouter with latency-sorted routing. Scored: ten (results below). Excluded after genuine attempts (documented, no model substitution): browser-agent (our adapter loop never wired its tool calls), BrowserSkill and browser-relay (extension install/attachment), browser-cli (extension install not scriptable headlessly), page-agent (hub approval gate). Not yet run: sitegeist (built, awaiting model wiring), Notte. Full handoff: [bench-ext/HANDOFF.md](bench-ext/HANDOFF.md).

| Contender | What it is | Pass | Median time | Tokens in/out | Cost per run |
|---|---|---|---:|---:|---:|
| **browser-control** | Rust CLI driving its own Chrome; ref-based a11y actions | 1/2 | **5.5s** | ~13.2k / ~180 | ~$0.0014 |
| **cdp-browser** | Minimal CDP CLI: nav/eval/screenshot over raw Chrome DevTools | 2/2 | **10.7s** | ~6.3k / ~250 | ~$0.0007 |
| **jarvis-browser** | Daemon-backed ref CLI over CDP (snapshot → act → verify) | 2/2 | **11.2s** | ~8.5k / ~100 | ~$0.0005 |
| **agent-browser** | Vercel's native Rust CLI; a11y refs, early-fail clicks | 0/2 | 13.7s | ~23.1k / ~210 | ~$0.0019 |
| **agent-chrome-cli** | Stateless CDP CLI with snapshot refs | 2/2 | 17.4s | ~7.6k / ~180 | ~$0.0004 |
| **lightpanda** | Zig headless browser with native CDP server | 2/2 | 22.7s | ~7.1k / ~590 | ~$0.0006 |
| **webctl** | Python CLI daemon; snapshot + text-driven click, no JS eval | 0/2 | 19.1s | ~5.8k / ~280 | ~$0.0006 |
| **raw-playwright baseline** | Model writes Playwright code against a persistent page | 3/4 | 42.7s | ~18.1k / ~410 | ~$0.0016 |
| **pinchtab** | Go control-plane HTTP server managing Chrome instances | 0/6 | 75.4s | ~7.4k / ~1550 | ~$0.0037 |
| **browser-agent** | Chrome-map agent loop (broken adapter — excluded) | 0/2* | 240.8s* | — | — |

\* broken harness runs kept as failure evidence; contender itself excluded.

### Round 3 verdict so far

- **New frontier candidate: browser-control** at 5.5s — faster than Browser Harness's 9.9s, though only 1/2 pass (one step-limit miss after reaching correct state). If its pass rate firms up with more reps it takes the speed crown.
- **cdp-browser** is the value pick: 2/2 pass, 10.7s, cheapest per run (~$0.0007), and the simplest possible interface (raw CDP commands).
- **jarvis-browser** (11.2s) and **agent-chrome-cli** (17.4s, $0.0004/run) are both solid 2/2 picks in the Browser Harness class.
- **lightpanda** is interesting — a non-Chrome browser (Zig, headless) passing 2/2 with no Chrome at all, at ~$0.0006/run.
- **Nothing beat the frontier on reliability**: the four 2/2 tools all sit in the 10–23s band; Browser Harness (9.9s) remains the fastest 100% pass rate.
- **pinchtab, webctl, agent-browser**: promising mechanics, but friction (literal-argument quoting, ambiguous toggles, missed done-signals) needs fixing before they're competitive.
- **Cost floor moved**: agent-chrome-cli at ~$0.0004/run undercuts Browser Harness's ~$0.0005.

Details: [bench-ext/artifacts/2026-09-12/summary.json](bench-ext/artifacts/2026-09-12/summary.json) and per-run transcripts in [bench-ext/artifacts/2026-09-12/results/](bench-ext/artifacts/2026-09-12/results/).

## Combined verdict

| Question | Answer |
|---|---|
| **Overall winner** | **Browser Harness** — fastest (9.9s median, faster than every Round 1 combination), cheapest (~$0.0005/run), 2/2 reliable. |
| Fastest | Browser Harness. Its 7.8s best run beat everything, including browser-use's 7.4s (which used default, not latency-sorted, routing). |
| Most token-efficient | Browser Harness (~6k input / ~190 output tokens per run — roughly 3× cheaper on tokens than Magnitude, 9× cheaper than BrowserCode). |
| Most reliable | **Magnitude** — 4/4 across four runs, zero flaky behaviour. |
| Best for complex SPAs | **Magnitude** — screenshot-driven actions never get confused by odd DOM or shadow DOM; it costs more tokens but doesn't break. |
| Best visual fallback | Magnitude (vision-native by design). Stagehand supports vision too, but it wasn't needed in these DOM-based runs. |
| **Drop from the stack** | **BrowserCode.** It passed the task but was 15× slower, used 8–15× more tokens, and cost ~55× more than Browser Harness — with no capability advantage to justify it. Its heavyweight agent runtime adds ~26k prompt tokens per call and minutes of overhead. |

### Notable failure patterns

- **Stagehand + GLM don't mix.** Stagehand demands strict JSON-schema responses; GLM-5.3-Flash intermittently returns malformed output or misfires actions (in one run it literally typed "Email supplier Enter" as a todo title). This is a model-schema mismatch, not a Stagehand bug — with a stronger model, Stagehand's self-healing local-browser support could do much better. Until then, don't pair them.
- **Browser Harness gotchas we fixed during the runs:** pressing `Enter` needs exact case (`press_key('Enter')`, not `'ENTER'`), and re-navigating with `goto_url()` can leave CDP input pointed at a stale session — use `new_tab()` for resets. Both documented in the spec so future runners don't rediscover them.

## What "cost" means here

- BrowserCode's cost is OpenRouter's own reported number.
- Everything else is calculated from exact token counts at the latency-sorted provider's published rate (Makora: $0.075 per million input, $0.25 per million output; cached input ≈ half price).
- No run exceeded a few cents total.

## Repo layout

```
artifacts/
  2026-09-10/            Round 1: per-run JSON + screenshots, results.json,
                         bench.py (runner), report.md, acceptance-manifest.md
  2026-09-11/
    results/             Round 2 per-run JSON + screenshots
    bench-py.py          Round 2 runner (Browser Harness, BrowserCode)
    bench-node.mjs       Round 2 runner (Stagehand, Magnitude)
    report.md            Round 2 full report + Pareto analysis
    acceptance-manifest.md
docs/
  benchmark-spec.md      The contract any future round must follow
.github/workflows/ci.yml  Validates JSON artifacts, screenshot presence, secret scan
```

## Reproducing a round

1. `export OPENROUTER_API_KEY=...` (never committed; CI scans for leaks).
2. Round 1 runner needs Browser Use + Playwriter sessions running with fresh task tabs — edit the session/target IDs at the top of `artifacts/2026-09-10/bench.py`, then `python3 bench.py`.
3. Round 2 runners need two isolated headless Chrome instances:
   - port 9233 with `--user-data-dir=<repo>/bcode-data` (for BrowserCode)
   - port 9234 with `--user-data-dir=<repo>/harness-data` (for Browser Harness)
   Then: `python3 artifacts/2026-09-11/bench-py.py <rep> harness|bcode` and `node artifacts/2026-09-11/bench-node.mjs stagehand|magnitude <rep>`.
4. Each script writes `results/<rep>-<contender>.json` plus a screenshot, and prints a one-line summary.

## Adding a new tool

Read [docs/benchmark-spec.md](docs/benchmark-spec.md) first — it defines the exact task text, pass criteria, provider config, timing boundary, required measurements, and the JSON transcript shape. Then follow the runner pattern in `artifacts/2026-09-11/` and add at least two scored reps. Update the README table and add a short Pareto note.

## Status

These are directional mini-benchmarks on one demo task. They're good enough to rank tools for practical automation work and to rule out clear losers, but they are not the scored real-world corpus benchmark. That larger effort (real sites, login flows, uploads, multi-tab journeys) lives in a separate project and will use this repo's methodology as its starting point.
