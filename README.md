# ⚠️ REAL WORK ONLY

**Every task in this benchmark must come from real recorded session history —
never invented, never approximated, never hand-authored.** We have a rich corpus
of genuinely messy, authenticated, multi-tab, recovery-heavy browser work
(Pinterest Ads Manager across US/UK/MENA accounts, GA4/Google Ads property and
conversion-config flows, CHANEL tag QA via authenticated Chrome, Amazon UK
defect-case handling). There is no excuse for synthetic benchmark tasks while
that corpus exists. Full rule, sources and mandatory provenance fields:
[`bench-ext/docs/REAL-WORK-MANDATE.md`](bench-ext/docs/REAL-WORK-MANDATE.md).
Tracked in issue #12.

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

## Master leaderboard — every benchmarked tool

One row per harness × best-model combination. `Median time` is the median across all scored reps of that row; `Pass` is the aggregate over the same reps. Sorted by median time. Costs: OpenRouter-reported for BrowserCode; else tokens × the latency-sorted provider's published rate (Makora: $0.075/M in, cached ≈ half, $0.25/M out). Round 1 rows are timing-only (token counts were not recorded); Round 4 browser-agent ran default routing (no latency pass-through in that CLI — see its report).

| Harness | Repo | Round | Pass | Median time | Tokens in/out | Cost per run |
|---|---|---|---:|---:|---:|---:|
| **browser-control** | [keon/browser-control](https://github.com/keon/browser-control) | 3 | 1/2 | **5.5s** | ~13.2k / ~180 | ~$0.0007 |
| **pinchtab** | [pinchtab/pinchtab](https://github.com/pinchtab/pinchtab) | 3 | 2/2 | 8.3s | ~5.1k / ~200 | ~$0.0003 |
| **browser-use** | [browser-use/browser-use](https://github.com/browser-use/browser-use) | 1 | 2/2 | 8.7s | n/a | n/a |
| **Browser Harness** | [in-repo (artifacts/2026-09-11)](https://github.com/Rajeev-SG/web-automation-microbench/tree/main/artifacts/2026-09-11) | 2 | 2/2 | 9.9s | ~6.2k / ~190 | ~$0.0005 |
| **agent-browser** | [vercel-labs/agent-browser](https://github.com/vercel-labs/agent-browser) | 3 | 2/2 | 10.1s | ~20.8k / ~120 | ~$0.0010 |
| **cdp-browser** | [sids/cdp-browser](https://github.com/sids/cdp-browser) | 3 | 2/2 | 10.7s | ~6.3k / ~250 | ~$0.0003 |
| **jarvis-browser** | [bridge25/jarvis-browser](https://github.com/bridge25/jarvis-browser) | 3 | 2/2 | 11.2s | ~8.5k / ~100 | ~$0.0005 |
| **Stagehand v4** | [browserbase/stagehand](https://github.com/browserbase/stagehand) | 2 | 1/4 | 13.1s | ~6.6k / 300–3,400 | ~$0.0007 |
| **webctl** | [cosinusalpha/webctl](https://github.com/cosinusalpha/webctl) | 3 | 2/2 | 14.5s | ~8.2k / ~100 | ~$0.0006 |
| **agent-chrome-cli** | [gxbvc/agent-chrome-cli](https://github.com/gxbvc/agent-chrome-cli) | 3 | 2/2 | 17.4s | ~7.6k / ~180 | ~$0.0004 |
| **lightpanda** | [lightpanda-io/browser](https://github.com/lightpanda-io/browser) | 3 | 2/2 | 22.7s | ~7.1k / ~590 | ~$0.0006 |
| **browser-agent** | [visnia-ai/browser-agent](https://github.com/visnia-ai/browser-agent) | 4 | 2/2 | 32.5s | ~43.1k / ~1,360 | ~$0.0036 |
| **raw-playwright baseline** | [microsoft/playwright](https://github.com/microsoft/playwright) | 3 | 3/4 | 42.7s | ~18.1k / ~410 | ~$0.0010 |
| **Magnitude** | [magnitudedev/magnitude](https://github.com/magnitudedev/magnitude) | 2 | 4/4 | 52.6s | ~18.3k / ~2.9k | ~$0.0021 |
| **Playwriter** | [remorses/playwriter](https://github.com/remorses/playwriter) | 1 | 2/2 | 10.1s | n/a | n/a |
| **BrowserCode** | [uuuuytgg/browser-code](https://github.com/uuuuytgg/browser-code) | 2 | 2/2 | 153.0s | ~55.6k / ~3.0k | ~$0.026 |

### Excluded after genuine attempts

| Tool | Repo | Reason |
|---|---|---|
| browser-agent (Taylor-Bayouth) | [Taylor-Bayouth/browser-agent](https://github.com/Taylor-Bayouth/browser-agent) | OpenRouter adapter loop never wired its tool calls (2 runs recorded as evidence); tool was rewritten as [visnia-ai/browser-agent](https://github.com/visnia-ai/browser-agent) and re-scored in Round 4 above |
| page-agent | [alibaba/page-agent](https://github.com/alibaba/page-agent) | Hub approval gate + Chrome hub-slot race; no provider.sort pass-through |
| browser-cli | [six-ddc/browser-cli](https://github.com/six-ddc/browser-cli) | Extension install not automatable headlessly |
| BrowserSkill | [Tencent/BrowserSkill](https://github.com/Tencent/BrowserSkill) | Extension install not completed in budget |
| browser-relay | [reliefeai/browser-relay](https://github.com/reliefeai/browser-relay) | No attached tab; extension never loaded |
| sitegeist | [badlogic/sitegeist](https://github.com/badlogic/sitegeist) | Not scored. Root causes: branded Google Chrome silently ignores `--load-extension` (verbose log: "--load-extension is not allowed in Google Chrome, ignoring"); Chrome for Testing loads the extension fine, but the sidepanel first-run (userscripts-permission dialog + full agent init) needs an interactive pass. GLM key pre-seeded in its IndexedDB — pending |
| Notte | [nottelabs/notte](https://github.com/nottelabs/notte) | Not started — pending (next step: py3.12 venv + litellm openrouter/z-ai/glm-5.3-flash) |

## What "cost" means here

- BrowserCode's cost is OpenRouter's own reported number.
- Everything else is calculated from exact token counts at the latency-sorted provider's published rate (Makora: $0.075 per million input, $0.25 per million output; cached input ≈ half price). Round 4 browser-agent used default routing (no latency pass-through); its cost uses the same published rate for comparability.
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
  2026-09-12/           Round 3: per-run JSON + screenshots, summary.json (in bench-ext)
  2026-09-13/
    report.md           Round 4 report (visnia-ai/browser-agent re-score)
    results/            Round 4 per-run JSON + step transcripts
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
