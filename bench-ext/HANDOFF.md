# Round 3 handoff — benchmark extension (2026-09-12)

## Where things stand
Worktree: /Users/rajeev/Code/web-automation-microbench/bench-ext/ (uncommitted, to be committed as checkpoint)
This is an extension of the repo (Round 3). Rounds 1–2 artifacts untouched.

## Spec compliance
- docs/benchmark-spec.md followed: same TodoMVC task text (benchlib.TASK), same verification (benchlib.VERIFY_JS + check_pass), timing boundary (timer starts at first model call; setup before, verify/screenshot after), JSON schema {id, contender, rep, events[], setup_s, total_s, model_calls, tokens{input,output,cached,reasoning}, cost, verification, pass}.
- Model: z-ai/glm-5.3-flash via OpenRouter, temperature 0, reasoning low+excluded, response_format json_object, provider {"sort":"latency"} — enforced in benchlib.openrouter_payload().
- OpenRouter key: `security find-generic-password -s codex-openrouter -w`.
- OpenRouter providers observed: Together (pinchtab), Makora (raw-playwright), plus provider recorded per call in each JSON (`events[].provider`).
- Cost basis: Makora $0.075/M input (cached ≈ half), $0.25/M output.

## Shared library
- bench-ext/benchlib.py: TASK, OBS_JS, VERIFY_JS, openrouter payload/call, parse_verify, check_pass, run_rep(adapter, rep) generic loop.
- bench-ext/RUNNER_NOTES.md: full adapter contract + per-tool Chrome ports + cost rules + rep rules.

## Results so far (artifacts/2026-09-12/results/, summary.json)
| contender | reps | pass | median_s | notes |
|---|---|---|---|---|
| agent-chrome-cli (v0.1.0 @ da6edc5) | 2 | 2/2 | 17.4 | 2/2 PASS |
| jarvis-browser (v1.4.0 @ ec19a46) | 2 | 2/2 | 11.2 | 2/2 PASS |
| lightpanda (v0.4.0 @ f3a775f) | 2 | 2/2 | 22.7 | 2/2 PASS |
| cdp-browser (@ 857a8ba) | 2 | 2/2 | 10.7 | 2/2 PASS |
| browser-control (@ b352a1a) | 2 | 1/2 | 5.5 | rep1 step-limit fail |
| agent-browser (@ 8c15ff9) | 2 | 0/2 | 13.7 | state reached, model never signalled done |
| raw-playwright (npm 1.63.0) | 4 | 3/4 | 42.7 | baseline; rep2 model error |
| pinchtab (@ 3771028) | 6 | 0/6 | 75.4 | literal-type quoting bug + step limits |
| webctl (@ a03aa7b) | 2 | 0/2 | 60.7 | adapter bugs found mid-flight; rerun in progress |
| browser-agent (@ a7a6169) | 2 | 0/2 | 240.8 | BROKEN runs: OpenRouter adapter not wired (240s timeouts, ~174 tok, one 401) |
| page-agent (npm 1.12.4 @ 9eb6b66) | 0 | — | — | EXCLUDED: hub approval gate + Chrome hub-slot race |
| browser-cli (@ cb39806) | 0 | — | — | EXCLUDED: extension install not automatable headlessly |
| sitegeist (@ 104788c) | 0 | — | — | NOT RUN: built OK (build in work/sitegeist/dist-chrome, needs pi-ai npm 0.73.1 not pi-mono HEAD), extension loaded in Chrome on port 9252, model config not yet wired |
| BrowserSkill (@ 7dc8b01) | 0 | — | — | NOT RUN: agent 2 pending |
| browser-relay (@ a147768) | 0 | — | — | NOT RUN: agent 2 pending |

## Known adapter gotchas (do not rediscover)
- pinchtab `type` treats text literally → quoted strings become todo titles. Also stderr leaks into CLI output; parse stdout only.
- jarvis-browser: JARVIS_WORKER_ID isolation; screenshots restricted to /tmp; evaluate --isolated returns wrapper JSON (unwrap .data).
- lightpanda: WS rejects Origin headers → websocket-client suppress_origin=True; prebuilt 0.4.0 arm64 binary, CDP on 9249.
- agent-chrome-cli: tab id comes from `tab new` stdout, not tab list order; needs seeded snapshot.
- raw-playwright: wrap model JS in async IIFE; never top-level return.
- browser-agent: providers registry is mutable; custom 'openrouter' adapter must be registered (lib/providers/index.js); openai-compat via OPENAI_BASE_URL works but agent's own loop needs the provider.sort body injected — UNRESOLVED (this is the broken piece).

## Remaining work to finish Round 3
1. webctl rerun (adapter bugs fixed; in flight at checkpoint time) OR record as failure/exclude.
2. browser-agent: fix OpenRouter provider adapter OR exclude.
3. BrowserSkill, browser-relay: attempt or exclude (extension-based; use rajeev.sgill@gmail.com profile / native computer use if needed).
4. sitegeist: wire GLM key via its chrome.storage providerKeys + select model, run 2 reps (extension build done).
5. Notte: pip install in py3.12 venv, litellm openrouter/z-ai/glm-5.3-flash, 2 reps. NOT STARTED.
6. README: append all Round 3 contenders to the comparison table (same columns), short Pareto/verdict update, round report in artifacts/2026-09-12/report.md.
7. Commit (git add bench-ext minus node_modules/work) and push.

## Subagent state at checkpoint
- Agent 1 (Linnaeus, 01a091cf-f8e2-7871-8a1e-d533850b3824): agent-browser/browser-control/cdp-browser DONE; webctl rerun in flight.
- Agent 2 (Huygens, 01a091d0-4311-74a2-9c2d-806eaba99609): browser-agent broken (2 runs recorded), browser-cli excluded; BrowserSkill/browser-relay unattempted at checkpoint.
- Agent 3 (Fermat, 01a091d0-806a-7721-9230-35470238a173): CLOSED after delivering agent-chrome-cli, jarvis-browser, lightpanda scored + page-agent excluded.
