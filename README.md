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
**Exception, narrow and explicit**: the TodoMVC round stays as a *latency
microbenchmark* (controlled instrument, deterministic harness check) — it is
not real work, not capability evidence, and must never be cited as such.

# Web Automation Microbenchmarks

Short, practical head-to-head races between browser automation tools. Every tool gets the same task, the same browser situation, and the same success test — then we measure who finishes reliably, quickly, cheaply, and with the least AI overhead.

**Read this if you want the one-paragraph answer:** thin harnesses that let the model issue one native command per step — now the extension-backed CLIs too (BrowserSkill 4.1s, browser-relay 4.3s, browser-cli 6.2s) — beat everything else on speed and cost. Round 6 tested eleven more contenders (the official Microsoft and Chrome DevTools CLIs, ego-browser, browser-act, surf, bb-browser, opencli, chrome-cdp-skill, hyperagent, midscene, skyvern) and **none displaced the front**: the fastest new arrival (chrome-cdp-skill, 11.5s) was also the least reliable (3/5), and the best new row once reliability is counted was chrome-devtools-mcp (5/5 @ 11.8s). A vision-first agent (Magnitude) is the most reliable on messy, JavaScript-heavy sites but costs more tokens and is slower. An agent runtime with only a narrow action set can lose outright: page-agent ships no key-press action, so it cannot commit a TodoMVC todo at all — and Round 6 found two more tools (opencli, bb-browser) that fail the same way because their key events carry no `keyCode`, so React never commits the todo. Anything running its own heavyweight agent loop (BrowserCode, notte, skyvern, midscene) costs 10–100× more wall-clock for no accuracy gain.

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

One row per harness × best-model combination. `Median time` is the median across all scored reps of that row; `Pass` is the aggregate over the same reps. Sorted by median time. Costs: OpenRouter-reported for BrowserCode; else tokens × the latency-sorted provider's published rate (Makora: $0.075/M in, cached ≈ half, $0.25/M out). Round 1 rows are timing-only (token counts were not recorded); Round 4 browser-agent ran default routing (no latency pass-through in that CLI — see its report). Round 3 fix-up rows: browser-cli, browser-relay and BrowserSkill run the shared benchlib GLM loop (latency-sorted); notte and page-agent ship their own agent runtimes, so their tokens/cost are not observable to the harness — and page-agent's LLM client cannot take latency routing. Round 5 page-agent is a **patched build**, not the stock release: stock page-agent scores 0/2 (it ships no key-press action, so it can never commit a TodoMVC todo). The patch adds `send_keys` and dispatches the key from the page's MAIN world — see the Round 5 section below. Taylor-Bayouth `browser-agent` is one of two unrelated same-name projects; its 1/2 is stock upstream code plus an OpenRouter adapter. **Round 6 rows are mostly 2-rep screening results**, with four promoted to 5 reps (chrome-cdp-skill, chrome-devtools-mcp, ego-browser, playwright-cli) because the 8–16s block was a near-tie and the issue requires promoting plausible frontier candidates. That promotion mattered: **chrome-cdp-skill screened 2/2 at 8.8s and then scored 3/5 over five reps** (reps 4–5 ended at the right persisted state but the wrong URL/filter, and the model reported "done" anyway) — 2-rep screening overstates reliability. Similarly, round-6 rows with only 2 reps should not be ordered finely against each other. Round 6 cost/routing: midscene and skyvern costs are tool-reported and both use default OpenRouter routing (no `provider.sort` pass-through); everything else is latency-sorted. opencli (0/2) and bb-browser (0/2) are **scored tool failures**, not exclusions — both reach the page but their native key event never commits the React todo (see the Round 6 section).

| Harness | Repo | Round | Pass | Median time | Tokens in/out | Cost per run |
|---|---|---|---:|---:|---:|---:|
| **BrowserSkill** | [Tencent/BrowserSkill](https://github.com/Tencent/BrowserSkill) | 3 | 2/2 | **4.1s** | ~6.2k / ~97 | ~$0.0005 |
| **browser-relay** | [reliefeai/browser-relay](https://github.com/reliefeai/browser-relay) | 3 | 2/2 | 4.3s | ~5.9k / ~95 | ~$0.0005 |
| **browser-control** | [keon/browser-control](https://github.com/keon/browser-control) | 3 | 1/2 | 5.5s | ~13.2k / ~180 | ~$0.0007 |
| **browser-cli** | [six-ddc/browser-cli](https://github.com/six-ddc/browser-cli) | 3 | 2/2 | 6.2s | ~8.6k / ~128 | ~$0.0007 |
| **pinchtab** | [pinchtab/pinchtab](https://github.com/pinchtab/pinchtab) | 3 | 2/2 | 8.3s | ~5.1k / ~200 | ~$0.0003 |
| **browser-use** | [browser-use/browser-use](https://github.com/browser-use/browser-use) | 1 | 2/2 | 8.7s | n/a | n/a |
| **Browser Harness** | [browser-use/browser-harness](https://github.com/browser-use/browser-harness) v0.1.13 | 2 | 2/2 | 9.9s | ~6.2k / ~190 | ~$0.0005 |
| **agent-browser** | [vercel-labs/agent-browser](https://github.com/vercel-labs/agent-browser) | 3 | 2/2 | 10.1s | ~20.8k / ~120 | ~$0.0010 |
| **Playwriter** | [remorses/playwriter](https://github.com/remorses/playwriter) | 1 | 2/2 | 10.1s | n/a | n/a |
| **cdp-browser** | [sids/cdp-browser](https://github.com/sids/cdp-browser) | 3 | 2/2 | 10.7s | ~6.3k / ~250 | ~$0.0003 |
| **jarvis-browser** | [bridge25/jarvis-browser](https://github.com/bridge25/jarvis-browser) | 3 | 2/2 | 11.2s | ~8.5k / ~100 | ~$0.0005 |
| **chrome-cdp-skill** | [pasky/chrome-cdp-skill](https://github.com/pasky/chrome-cdp-skill) | 6 | 3/5 | 11.5s | ~21.1k / ~323 | ~$0.0083 |
| **chrome-devtools-mcp** | [ChromeDevTools/chrome-devtools-mcp](https://github.com/ChromeDevTools/chrome-devtools-mcp) | 6 | 5/5 | 11.8s | ~12.6k / ~89 | ~$0.0048 |
| **Stagehand v4** | [browserbase/stagehand](https://github.com/browserbase/stagehand) | 2 | 1/4 | 13.1s | ~6.6k / 300–3,400 | ~$0.0007 |
| **ego-browser** | [citrolabs/ego-lite](https://github.com/citrolabs/ego-lite) | 6 | 5/5 | 14.2s | ~12.3k / ~99 | ~$0.0048 |
| **webctl** | [cosinusalpha/webctl](https://github.com/cosinusalpha/webctl) | 3 | 2/2 | 14.5s | ~8.2k / ~100 | ~$0.0006 |
| **playwright-cli** | [microsoft/playwright-cli](https://github.com/microsoft/playwright-cli) | 6 | 5/5 | 14.7s | ~21.7k / ~113 | ~$0.0083 |
| **agent-chrome-cli** | [gxbvc/agent-chrome-cli](https://github.com/gxbvc/agent-chrome-cli) | 3 | 2/2 | 17.4s | ~7.6k / ~180 | ~$0.0004 |
| **browser-act-skills** | [browser-act/skills](https://github.com/browser-act/skills) | 6 | 2/2 | 18.5s | ~6.0k / ~76 | ~$0.0009 |
| **lightpanda** | [lightpanda-io/browser](https://github.com/lightpanda-io/browser) | 3 | 2/2 | 22.7s | ~7.1k / ~590 | ~$0.0006 |
| **page-agent** (patched: `send_keys`) | [alibaba/page-agent](https://github.com/alibaba/page-agent) | 5 | 2/2 | 25.3s | n/a | n/a |
| **hyperagent** (perform) | [hyperbrowserai/HyperAgent](https://github.com/hyperbrowserai/HyperAgent) | 6 | 3/4 | 28.3s | ~20.8k / ~3.4k | ~$0.0096 |
| **opencli** | [jackwener/OpenCLI](https://github.com/jackwener/OpenCLI) | 6 | 0/2 | 30.4s | ~20.8k / ~234 | ~$0.0032 |
| **surf-cli** | [nicobailon/surf-cli](https://github.com/nicobailon/surf-cli) | 6 | 2/2 | 31.8s | ~28.6k / ~519 | ~$0.0046 |
| **browser-agent** | [visnia-ai/browser-agent](https://github.com/visnia-ai/browser-agent) | 4 | 2/2 | 32.5s | ~43.1k / ~1,360 | ~$0.0036 |
| **bb-browser** | [epiral/bb-browser](https://github.com/epiral/bb-browser) | 6 | 0/2 | 32.7s | ~12.6k / ~380 | ~$0.0021 |
| **midscene** | [web-infra-dev/midscene](https://github.com/web-infra-dev/midscene) | 6 | 2/2 | 33.4s | ~444k / ~62k | ~$0.074 |
| **raw-playwright baseline** | [microsoft/playwright](https://github.com/microsoft/playwright) | 3 | 3/4 | 42.7s | ~18.1k / ~410 | ~$0.0010 |
| **Magnitude** | [magnitudedev/magnitude](https://github.com/magnitudedev/magnitude) | 2 | 4/4 | 52.6s | ~18.3k / ~2.9k | ~$0.0021 |
| **BrowserCode** | [uuuuytgg/browser-code](https://github.com/uuuuytgg/browser-code) | 2 | 2/2 | 153.0s | ~55.6k / ~3.0k | ~$0.026 |
| **notte** | [nottelabs/notte](https://github.com/nottelabs/notte) | 3 | 2/2 | 171.8s | n/a | n/a |
| **skyvern** | [Skyvern-AI/skyvern](https://github.com/Skyvern-AI/skyvern) | 6 | 2/2 | 186.5s | ~29.0k / ~4.2k | ~$0.0055 |
| **browser-agent** (Taylor-Bayouth) | [Taylor-Bayouth/browser-agent](https://github.com/Taylor-Bayouth/browser-agent) | 5 | 1/2 | 200.1s | ~19k–782k / ~0.5k–25k | n/a |

## Round 6 — 14 Sep 2026: remaining high-value contenders (issue #17)

Eleven further contenders, all on GLM 5.3-Flash with latency-sorted routing where the tool permits it.
Full screening table, Pareto analysis, architecture classification, block/defect evidence and
reproducibility notes: [bench-ext/artifacts/2026-09-14/report.md](bench-ext/artifacts/2026-09-14/report.md).

- **No contender extended the fast-path frontier.** Every Round 6 row is dominated by an existing row on
  (speed, cost). The closest new arrival, **chrome-cdp-skill**, lands at 11.5s *and only 3/5*; the new
  official baselines (**chrome-devtools-mcp** 5/5 @ 11.8s, **playwright-cli** 5/5 @ 14.7s) and
  **ego-browser** (5/5 @ 14.2s) are competitive and reliable but not faster than BrowserSkill.
- **The near-tie block resolved to: chrome-devtools-mcp 5/5 @ 11.8s, chrome-cdp-skill 3/5 @ 11.5s,
  ego-browser 5/5 @ 14.2s, playwright-cli 5/5 @ 14.7s.** On 5 reps the fastest new tool is also the
  least reliable — chrome-devtools-mcp is the strongest new row once reliability is counted.
- **Two more genuine tool failures: opencli (0/2) and bb-browser (0/2).** Both reach the page and
  report success, but their native key event carries no `keyCode`/`windowsVirtualKeyCode`, so React
  never commits the todo. Root cause confirmed by direct probe (a `keyCode: 13` dispatch via the same
  tool commits correctly). Upstream defect in each, not a harness limitation.
- **Capability rows, not fast-path rows:** **midscene** (vision, 2/2 @ 33.4s, ~$0.074/run) and
  **skyvern** (autonomous multi-agent, 2/2 @ 186.5s) preserve their native architectures and belong to
  the real-work/capability suite, not the latency ranking.
- **Tier D (nanobrowser, browserable, BrowserOS, steel/pi-steel) was reviewed and not promoted** — none
  adds an architecture the benchmark lacks, and none has credible Pareto-improvement evidence.
- With Tier A/B/C covered, the benchmark adopts the admission rule in §10 of the round report: a new
  tool enters only with a genuinely different architecture, credible Pareto evidence, or a missing capability.

### Excluded after genuine attempts

| Tool | Repo | Reason |
|---|---|---|
| sitegeist | [badlogic/sitegeist](https://github.com/badlogic/sitegeist) | Unscoreable at this commit (104788c) — dependency set is not reproducible. **Build** works after pinning `@mariozechner/pi-{ai,agent-core,web-ui}` to the published **0.73.1** family and adding the missing `@opentelemetry/api` peer. **Runtime** then fails: `TypeError: agent.appendMessage is not a function` — sitegeist's code needs `pi-agent-core` 0.85.x, which is published nowhere (`@mariozechner` tops out at 0.73.1). The 0.85.1 sources only exist in the vendored `pi-mono` clone, whose `packages/web-ui` is **absent** and which cannot build here (`tsgo` missing; unbuilt `pi-telemetry`). So there is no combination of published + vendored packages that both builds and runs. Verified 2026-09-12; extension loading itself is solved (Chrome for Testing `--load-extension`). |

## Round 3 extension fix-up — 12 Sep 2026

The extension-backed contenders that Round 3 could not load are now scored. The root cause of every "extension install not automatable headlessly" exclusion was one thing: **branded Google Chrome silently ignores `--load-extension`, but Chrome for Testing honours it** (`bench-ext/cft_chrome.py`). With that solved:

| Contender | What unblocked it | Result |
|---|---|---|
| BrowserSkill (Tencent) | wxt build of `apps/extension` loaded into Chrome for Testing; `bsk` daemon (`ws 127.0.0.1:52800`) then sees it | **2/2, 4.1s** |
| browser-relay (reliefeai) | bundled unpacked extension loaded directly; relay on `127.0.0.1:18795`; needs `focus` so CDP key events land (its `key` builds an invalid Enter event otherwise) | **2/2, 4.3s** |
| browser-cli (six-ddc) | prebuilt `chrome-mv3` extension loaded; daemon moved to port 9333 (9222 is the user's own Chrome) with the extension rebuilt against it | **2/2, 6.2s** |
| page-agent (alibaba) | hub gate is `chrome.storage.local.allowAllHubConnection`, seeded in the extension's own service-worker context over CDP; the MCP bridge's auto-`open` is neutered so the user's Chrome can't race for the hub slot | 0/2 — see below |
| notte (nottelabs) | Python 3.12 uv venv + `notte`; agent pointed at OpenRouter/GLM via `NOTTE_CONFIG_PATH` (`reasoning_model = openrouter/z-ai/glm-5.3-flash`) | **2/2, 171.8s** |

**page-agent scores 0/2, and the reason is the tool, not the harness.** After clearing the approval gate, its built-in action set is `click_element_by_index`, `input_text`, `select_dropdown_option`, `scroll`, `scroll_horizontally`, `execute_javascript`, `wait`, `ask_user`, `done` — there is no key-press action. The TodoMVC task cannot be finished without pressing Enter after typing, and the model filled the field across ~16 attempts on 5 tabs without ever committing a todo (rep 1: 527s, "Task failed"; rep 2: same, cut at the 900s budget).

The **Taylor-Bayouth `browser-agent`** and **[visnia-ai/browser-agent](https://github.com/visnia-ai/browser-agent)** entries are **two unrelated projects that share a name**, not a rewrite: neither is a GitHub fork of the other (`fork: false, parent: null`), the contributors and authors are disjoint, and they publish different npm packages. Both are now scored separately on the leaderboard — visnia-ai in Round 4 (2/2, 32.5s) and Taylor-Bayouth in Round 5 (1/2, 200.1s). The earlier claim that Taylor-Bayouth's adapter "never wired its tool calls" was wrong — Round 5 traced its real blocker to a stale persistent Chrome profile (see the Round 5 section).

## Round 5 — 12 Sep 2026: the two `browser-agent` projects, page-agent and sitegeist

Four rows that were open after Round 3, worked with Chrome for Testing + the shared helpers (`bench-ext/cft_chrome.py`, `bench-ext/cdp.mjs`).

| Tool | Result | What was actually wrong |
|---|---|---|
| **browser-agent** (Taylor-Bayouth) | **1/2**, median 200.1s | Not an adapter bug: its tool calls parse fine. Its Chrome uses a **persistent isolated profile**, so a stale browser from a previous run was silently reused (it worked a Grafana tab). Fixed by killing that profile's Chrome, wiping the profile, and pre-loading the task URL. Rep 2 then passed in 9.2s; rep 1 thrashed to 391s and left **4 todos** while reporting "Task complete" — a false success claim the shared verifier catches. |
| **page-agent** (alibaba) | **2/2**, median 25.3s — *patched* | Two real defects. (1) No key-press action at all (upstream `// @todo send_keys`), so it can never commit a TodoMVC todo — stock build scores 0/2. (2) Even once added, key events dispatched from the extension's **isolated** content-script world never reach React; the dispatch has to run in the page's MAIN world via `chrome.scripting.executeScript`. Patch: `send_keys` tool + MAIN-world dispatch + `scripting` permission. |
| **browser-agent** (visnia-ai) | already scored | Round 4, 2/2 @ 32.5s. Unrelated same-name project. |
| **sitegeist** (badlogic) | still excluded, new evidence | Builds after pinning the `pi-*` family to 0.73.1, then dies at runtime on `agent.appendMessage` — it needs an unpublished `pi-agent-core` 0.85.x whose sibling `pi-web-ui` is missing from the vendored monorepo, which also won't build here. Not a local fix. |

**page-agent patch** (kept as a bench-local fork; the stock 0/2 is recorded above):
1. `packages/core/src/tools/index.ts` — add a `send_keys` tool (key + optional element index).
2. `packages/extension/src/agent/RemotePageController.background.ts` — handle `press_key` by running the key dispatch in the page's **MAIN** world via `chrome.scripting.executeScript`, targeting `targetTabId` (not the caller's tab).
3. `packages/extension/wxt.config.js` — add the `scripting` permission.

The isolated-vs-main-world finding is the general lesson: a synthetic `KeyboardEvent` from a content script does **not** reach the page's React listener, while the identical dispatch from the main world commits correctly.

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

## Task parameterization — 15 Sep 2026

The benchmark is no longer TodoMVC-only. `bench-ext/benchlib.py` now holds a **task
registry** and `run_rep(adapter, rep, task=…)`; TodoMVC stays the latency microbenchmark
(byte-identical, golden-tested). Rep counts are centralized with the issue #1 topology
(2 screen → 5 promote → 10+ tiebreak), and a task must carry session provenance
(`source_session_id`, `source_url`, `verified_against`) or the intake validator rejects it.

Delivery evidence: the top two harnesses were run on a real, auth-free, session-derived task
(`chanel-gb-tag-check` — inspect the CHANEL UK homepage for its marketing tags). **BrowserSkill
screened 2/2, was promoted to 5 reps, and scored 3/5; browser-relay screened 1/2.** The
promotion is the point: 2-rep screening overstates reliability, exactly as Round 6 found.
Report: [bench-ext/artifacts/2026-09-15/delivery/report.md](bench-ext/artifacts/2026-09-15/delivery/report.md).

## Status

These are directional mini-benchmarks on one demo task. They're good enough to rank tools for practical automation work and to rule out clear losers, but they are not the scored real-world corpus benchmark. That larger effort (real sites, login flows, uploads, multi-tab journeys) lives in a separate project and will use this repo's methodology as its starting point.
