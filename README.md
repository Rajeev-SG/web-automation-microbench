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
This table is the **fast-path latency/cost** claim only; the separate **real-work capability** claim
is the next table.

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
| **Browser Use Pi** | [browser-use/browser-use-pi](https://github.com/browser-use/browser-use-pi) | 7 | 7/10 | 53.5s | ~6.6k / ~0.7k | ~$0.0010 |
| **BrowserCode** | [uuuuytgg/browser-code](https://github.com/uuuuytgg/browser-code) | 2 | 2/2 | 153.0s | ~55.6k / ~3.0k | ~$0.026 |
| **notte** | [nottelabs/notte](https://github.com/nottelabs/notte) | 3 | 2/2 | 171.8s | n/a | n/a |
| **skyvern** | [Skyvern-AI/skyvern](https://github.com/Skyvern-AI/skyvern) | 6 | 2/2 | 186.5s | ~29.0k / ~4.2k | ~$0.0055 |
| **browser-agent** (Taylor-Bayouth) | [Taylor-Bayouth/browser-agent](https://github.com/Taylor-Bayouth/browser-agent) | 5 | 1/2 | 200.1s | ~19k–782k / ~0.5k–25k | n/a |

### Real-work capability leaderboard

The table above ranks the **latency microbenchmark** (TodoMVC, one controlled instrument). It says
nothing about whether a harness can do real work, and the two orderings genuinely disagree. Below is
the same harness set scored on the **harvested browser corpus** — 11 real, provenance-backed browser
tasks vendored from `codex-session-orchestration-analysis#88` (issue #27). Full per-task scoreboard
and the defects the runs exposed:
[`bench-ext/artifacts/2026-09-12/corpus/report.md`](bench-ext/artifacts/2026-09-12/corpus/report.md).

| Harness | Repo | Fast-path (TodoMVC) | Real-work capability | Capability reps | Note |
|---|---|---|---|---|---|
| **browser-relay** | [reliefeai/browser-relay](https://github.com/reliefeai/browser-relay) | 2/2 · 4.3s | **22/33** | 1, 2, 3 | strongest on real work; promoted past screening |
| **raw-playwright baseline** | [microsoft/playwright](https://github.com/microsoft/playwright) | 3/4 · 42.7s | 17/33 | 1, 2, 3 | promoted past screening |
| **agent-browser** | [vercel-labs/agent-browser](https://github.com/vercel-labs/agent-browser) | 2/2 · 10.1s | 6/11 | 1 | |
| **cdp-browser** | [sids/cdp-browser](https://github.com/sids/cdp-browser) | 2/2 · 10.7s | 6/11 | 1 | |
| **browser-use-pi** | [browser-use/browser-use-pi](https://github.com/browser-use/browser-use-pi) | 7/10 · 53.5s | 4/11 | 1 | own-loop (Pi Mono + V8 REPL); the only harness to pass `chanel-gb-pdp-tag-inspection` |
| **BrowserSkill** | [Tencent/BrowserSkill](https://github.com/Tencent/BrowserSkill) | 2/2 · **4.1s** | 2/11 | 1 | **fastest fast-path, weakest real work** — the orderings invert |

Six harness architectures, 110 runs, model `z-ai/glm-5.3-flash`. Cells are `passes / reps`; every
number is recomputed from the per-rep JSON in `bench-ext/artifacts/2026-09-12/corpus/`, and nothing is
retried away. Screening was 1 rep per task; the two leaders were then promoted to 3 reps, which
exposed failures a single rep understated.

| Task | Capability | Passes (all harnesses) |
|---|---|---|
| `allbirds-uk-add-to-cart-tag-check` | consent → add to cart → tags | 0/10 |
| `gymshark-uk-add-to-cart-tag-check` | consent → add to cart → tags | 1/10 |
| `puma-uk-seo-metadata-audit` | SEO / structured data | 1/10 |
| `tldraw-three-shape-diagram` | canvas UI creation | 2/10 |
| `chanel-gb-pdp-tag-inspection` | tag inspection (anti-bot boundary) | 3/10 |
| `rajeevg-crawlability-audit` | robots.txt + sitemap | 8/10 |
| `porsche-uk-script-inventory` | third-party script inventory | 8/10 |
| `puma-uk-script-inventory` | third-party script inventory | 8/10 |
| `puma-uk-tag-inspection` | tag inspection | 8/10 |
| `porsche-uk-tag-inspection` | tag inspection | 9/10 |
| `rajeevg-seo-metadata-audit` | SEO / structured data | 9/10 |

**Read it as:** the one-shot "inspect the live page and report" audits converge on any harness
that can evaluate JS in the page; the multi-step journeys (add-to-cart) and canvas construction sit
above the current frontier. `puma-uk-seo-metadata-audit` fails because models over-report
nested JSON-LD types. Discriminating difficulty, not broken tasks.

## Round 7 — 13 Sep 2026: Browser Use Pi (issue #34)

[Browser Use Pi](https://github.com/browser-use/browser-use-pi) is not another thin CLI. Its
architecture is **Pi Mono agent loop → persistent V8 REPL → raw CDP → Chrome**, with AX-tree and
screenshot observations: the model writes JavaScript cells against a browser API it builds for itself
as it goes. That is genuinely different from every row above, so it clears the §10 admission bar — and
its claim is not fast-path latency but long-horizon **code batching**.

Pin: `@browser_use/pi` **0.1.0** at git `fa838f3`; Node 22.19+; `bench-ext/runners/browser-use-pi-setup.sh`
reproduces the install. GLM 5.3 Flash via OpenRouter with `provider.sort: "latency"` — the model is
registered into Pi's pinned catalog with `compat.openRouterRouting`, so the same latency-sorted
routing the other rows use is passed through. Browser: **local Chrome** (`Browser.chromium`, headless),
not Browser Use Cloud. It ships its own agent loop, so it is timed as one `agent.run()` per rep —
exactly like notte/skyvern/midscene.

| Round | Reps | Pass | Median time | Tokens in/out | Cost per run |
|---|---:|---:|---:|---:|---:|
| 7 | 10 | **7/10** | **53.5s** | ~6.6k / ~0.7k | ~$0.0010 |

- **TodoMVC 7/10 @ 53.5s** (reps 1–5 screened clean 5/5; reps 6–10 exposed three false successes —
  the reason 2-rep screening is not trusted here). Slower and less reliable than the thin leaders
  (BrowserSkill 4.1s): on a three-action task, code batching does not beat one native command per step
  — it pays a larger prompt and AX/tool plumbing per turn. The three failures are all **false
  successes**: both todos added and the right one toggled, but the view never left `#/` for `#/active`
  and the agent reported done. The independent verifier caught all three.
- **Real work 4/11 (1-rep screening).** The headline inverts the ordering: **browser-use-pi is the only
  harness in the whole set to pass `chanel-gb-pdp-tag-inspection`** — the anti-bot boundary where the
  thin CLIs score 2/9. It also passes `rajeevg-crawlability-audit`, `rajeevg-seo-metadata-audit` and
  `porsche-uk-tag-inspection`. It fails the add-to-cart journeys (never publishes `window.__bench_finding`,
  although allbirds' cart is mutation-correct) and the script inventories (under- or double-encoded
  findings) — honest capability failures, the same near-misses the thin harnesses make.
- **Pareto impact: no new fast-path frontier.** On (speed, cost) it is dominated by every thin CLI in
  the 4–15s block. Its distinct value is capability, not speed — the first harness past the CHANEL
  anti-bot boundary, which is exactly the messy, long-horizon workload the next phase targets.
- **Does the persistent code-execution model get more competitive as tasks get longer?** Partly, and
  only up to a point. It is weakest exactly where it should be strongest on paper: the short,
  deterministic TodoMVC task (53.5s vs 4.1s). On the corpus its **round-trip count** is low (3–6 steps
  for the one-shot audits) but wall time is high (up to 153s on CHANEL) — each cell round-trip is heavy
  and it re-derives helpers. At this sample size it has not converted code batching into either speed
  or reliability. The honest read: the architecture *permits* larger composed actions, but on this
  corpus the model mostly used it as a slower one-command-per-step loop. Evidence, not a verdict.

Full evidence: [bench-ext/artifacts/2026-09-13-round7/report.md](bench-ext/artifacts/2026-09-13-round7/report.md);
per-rep JSON in `bench-ext/artifacts/2026-09-13/results/` (TodoMVC) and
`bench-ext/artifacts/2026-09-12/corpus/browser-use-pi/` (corpus).

## Round 6 — 12 Sep 2026: remaining high-value contenders (issue #17)

Eleven further contenders, all on GLM 5.3-Flash with latency-sorted routing where the tool permits it.
Full screening table, Pareto analysis, architecture classification, block/defect evidence and
reproducibility notes: [bench-ext/artifacts/2026-09-12-round6/report.md](bench-ext/artifacts/2026-09-12-round6/report.md).

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
artifacts/                 Round 1-2 and Round 4 raw evidence
  2026-09-10/              Round 1: per-run JSON + screenshots, results.json,
                           bench.py (runner), report.md, acceptance-manifest.md
  2026-09-11/
    results/               Round 2 per-run JSON + screenshots
    bench-py.py            Round 2 runner (Browser Harness, BrowserCode)
    bench-node.mjs         Round 2 runner (Stagehand, Magnitude)
    report.md              Round 2 full report + Pareto analysis
    acceptance-manifest.md

bench-ext/                 everything from Round 3 on
  benchlib.py              shared library: task registry, model payload, run_rep loop,
                           token/cost accounting, artifact paths
  runners/                 one adapter per contender (~30), each driven by benchlib.run_cli
  tests/                   unit suite + golden TodoMVC fixture
  pass_rule.py             declarative pass-rule interpreter for harvested tasks
  task_intake.py           validates a task spec against the #88 contract
  task_ingest.py           validate -> register as benchlib.Task (no per-task code)
  corpus/
    SOURCE.json            producer revision + per-file sha256 pin
    tasks/*.json           vendored harvested browser tasks (read-only)
    refresh.py             re-vendor / drift-check against the producer checkout
    screen.py              screen a harness across the corpus
    report.py              aggregate runs into the capability scoreboard
  delivery/                the issue #20 worked example spec
  docs/                    benchmark-spec.md, task-intake.md, REAL-WORK-MANDATE.md
  artifacts/
    2026-09-11-round4/     Round 4: visnia-ai/browser-agent re-score
    2026-09-12/            Round 3, plus pareto-corpus envelopes
    2026-09-12-round6/     Round 6: remaining high-value contenders
    2026-09-12-delivery/   issue #20 delivery run (top-2 on a real task)
    2026-09-12/corpus/     harvested-corpus screening + capability scoreboard

docs/
  benchmark-spec.md        the TodoMVC round contract
.github/workflows/ci.yml   JSON artifacts, bench-ext unit tests, synthetic-fixture guard,
                           corpus validation/ingestion, secret scan, README publishing rule
```

New artifacts derive their folder from the wall clock (`benchlib.run_date()`), so a run never
writes into a future-dated directory; `BENCH_RES` overrides it.

## Reproducing a round

**A scored microbenchmark round** (TodoMVC, one controlled instrument):

```bash
export OPENROUTER_API_KEY=$(security find-generic-password -s codex-openrouter -w)   # never committed
python3 bench-ext/runners/<harness>.py 1 2                    # rep 1,2 = the screening plan
python3 bench-ext/runners/<harness>.py 1 2 3 4 5 --task=<id>  # promote, and/or run another task
```

`benchlib.run_cli` parses reps and `--task=<id>`; the library owns the task text, the timing
boundary, token accounting and the schema, so a runner only supplies the adapter. Rounds 1–2
predate `benchlib` and still use their own runners:
`python3 artifacts/2026-09-11/bench-py.py <rep> harness|bcode` and
`node artifacts/2026-09-11/bench-node.mjs stagehand|magnitude <rep>` (two isolated Chrome
instances, ports 9233/9234). Round 1 needs Browser Use + Playwriter sessions with fresh task tabs.

**A real-work capability screen** (the harvested corpus):

```bash
python3 bench-ext/corpus/screen.py --harness <harness> --reps 1 --all          # benchlib adapters
python3 bench-ext/corpus/screen_native.py --harness <harness> --reps 1 --all   # own-loop harnesses
python3 bench-ext/corpus/report.py --run-dir bench-ext/artifacts/<run date>/corpus
```

Every run writes `<rep>-<harness>.json` plus a screenshot and prints a one-line summary; failed
reps are kept, never retried away.

## Adding a new tool

Read [docs/benchmark-spec.md](docs/benchmark-spec.md) first — it defines the exact task text, pass
criteria, provider config, timing boundary, required measurements, and the JSON transcript shape.
Then add `bench-ext/runners/<tool>.py`: an adapter with `name`, `doc`, `start()`, `act()`,
`verify()`, `screenshot()` and `teardown()`, ending in `benchlib.run_cli(Adapter)`. Do not
reimplement the task, the timer, the token accounting or the schema — `benchlib` owns those, and
`bench-ext/tests/test_runner_task_flag.py` fails a runner that bypasses them.

Score at least two reps of the TodoMVC microbenchmark, then screen the harvested corpus
(`bench-ext/corpus/screen.py`) to see where it lands on real work. Update both tables in this
README, and add a short Pareto note.

**A tool that ships its own agent loop** (notte, skyvern, midscene, Browser Use Pi) is different:
do **not** reduce it to a benchlib adapter, because one primitive action per model call erases the
architecture under test. Give it a runner exposing `run_native(rep, task=...)` that drives the tool's
own loop once per rep, then screen it with `bench-ext/corpus/screen_native.py` (it writes the same run
JSON, so `corpus/report.py` aggregates it unchanged).

## Task parameterization — 12 Sep 2026

The benchmark is no longer TodoMVC-only. `bench-ext/benchlib.py` now holds a **task
registry** and `run_rep(adapter, rep, task=…)`; TodoMVC stays the latency microbenchmark
(byte-identical, golden-tested). Rep counts are centralized with the issue #1 topology
(2 screen → 5 promote → 10+ tiebreak), and a task must carry session provenance
(`source_session_id`, `source_url`, `verified_against`) or the intake validator rejects it.

Delivery evidence: the top two harnesses were run on a real, auth-free, session-derived task
(`chanel-gb-tag-check` — inspect the CHANEL UK homepage for its marketing tags), each screened
at 2 reps then promoted to 5. **browser-relay screened 1/2 then scored 4/5; BrowserSkill
screened 2/2 then scored 3/5.** The promotion is the point: 2 reps understated browser-relay
and overstated BrowserSkill, so screening alone would have mis-ordered them.
Report: [bench-ext/artifacts/2026-09-12-delivery/delivery/report.md](bench-ext/artifacts/2026-09-12-delivery/delivery/report.md).

## Status

Two separate claims, from two separate task sets:

- **Fast-path latency/cost** — the TodoMVC microbenchmark (one controlled instrument, golden-tested).
  Good enough to rank tools for speed and cost, and to rule out clear losers.
- **Real-work capability/reliability** — the harvested browser corpus below. This is the capability
  claim; TodoMVC never feeds it.

## The harvested browser corpus (issue #27)

The capability suite is **not written here**. It is harvested from real AgentSessions work in
[`Rajeev-SG/codex-session-orchestration-analysis`](https://github.com/Rajeev-SG/codex-session-orchestration-analysis)
(issue #88) and vendored read-only into `bench-ext/corpus/` with a producer revision + per-file
sha256 pin. Only `task_class == "web-automation"` tasks are consumed — coding/desktop/document
tasks the harvester also emits are out of scope.

**11 browser tasks**, each auth-free with a deterministic page-recomputed verifier and a declarative
pass rule: marketing-tag inspection (CHANEL PDP, Porsche UK, PUMA UK), third-party script
inventory (Porsche UK, PUMA UK), SEO/structured-data audit (rajeevg.com, PUMA UK), crawlability
(rajeevg.com), canvas diagram creation (tldraw), and consent → find product → add to cart → tag
check (Allbirds UK, Gymshark UK). There is no fixed suite size: the corpus is however many
browser tasks the producer has admitted.

```bash
# re-vendor / drift-check the corpus against the producer checkout
python3 bench-ext/corpus/refresh.py --from ./codex-session-orchestration-analysis
# validate + register every task as a benchlib.Task, then screen the representative harness set
python3 bench-ext/task_ingest.py
python3 bench-ext/corpus/screen.py --harness raw-playwright --reps 1 --all
python3 bench-ext/corpus/report.py --run-dir bench-ext/artifacts/2026-09-12/corpus
```

Scored results — 5 harness architectures x 11 tasks, 99 runs — are in the
**Real-work capability leaderboard** above. Full per-task scoreboard, the three harness defects
the runs exposed, and the promotion evidence:
[bench-ext/artifacts/2026-09-12/corpus/report.md](bench-ext/artifacts/2026-09-12/corpus/report.md)
· [capability-scoreboard.json](bench-ext/artifacts/2026-09-12/corpus/capability-scoreboard.json).

Provenance rules, the ingestion contract and admission gates:
[`bench-ext/docs/task-intake.md`](bench-ext/docs/task-intake.md) and the producer's
`docs/implementation/task-harvesting-v1.md`.
