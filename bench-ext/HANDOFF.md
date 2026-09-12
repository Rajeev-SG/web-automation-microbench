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
| cdp-browser (@ 857a8ba, npm 0.1.3) | 2 | 2/2 | 10.7 | PASS |
| jarvis-browser (v1.4.0 @ ec19a46) | 2 | 2/2 | 11.2 | PASS |
| agent-chrome-cli (v0.1.0 @ da6edc5) | 2 | 2/2 | 17.4 | PASS |
| lightpanda (v0.4.0 @ f3a775f) | 2 | 2/2 | 22.7 | PASS |
| browser-control (@ b352a1a) | 2 | 1/2 | 5.5 | rep1 step-limit fail |
| raw-playwright (npm 1.63.0) | 4 | 3/4 | 42.7 | baseline; rep2 model error |
| agent-browser (npm 0.37.1 @ 8c15ff9) | 2 | 0/2 | 13.7 | state reached, done-signal missed |
| webctl (0.4.2 @ a03aa7b) | 2 | 0/2 | 19.1 | toggle ambiguity, step limits |
| pinchtab (@ 3771028) | 6 | 0/6 | 75.4 | literal-type quoting + step limits |
| browser-agent (@ a7a6169) | 2 | 0/2 | 240.8 | BROKEN adapter loop; EXCLUDED via browser-agent-EXCLUDED.json |
| page-agent (npm 1.12.4 @ 9eb6b66) | 0 | — | — | EXCLUDED: hub approval gate + Chrome hub-slot race |
| browser-cli (@ cb39806) | 0 | — | — | EXCLUDED: extension install not automatable headlessly |
| BrowserSkill (@ 7dc8b01) | 0 | — | — | EXCLUDED: extension install not completed in budget |
| browser-relay (@ a147768) | 0 | — | — | EXCLUDED: no attached tab, extension never loaded |
| sitegeist (@ 104788c) | 0 | — | — | NOT RUN: built OK (dist-chrome ready, pi-ai must be npm 0.73.1), extension in Chrome port 9252, model config not wired |
| Notte (@ 9e8915c) | 0 | — | — | NOT STARTED |

## Known adapter gotchas (do not rediscover)
- pinchtab `type` treats text literally → quoted strings become todo titles. Also stderr leaks into CLI output; parse stdout only.
- jarvis-browser: JARVIS_WORKER_ID isolation; screenshots restricted to /tmp; evaluate --isolated returns wrapper JSON (unwrap .data).
- lightpanda: WS rejects Origin headers → websocket-client suppress_origin=True; prebuilt 0.4.0 arm64 binary, CDP on 9249.
- agent-chrome-cli: tab id comes from `tab new` stdout, not tab list order; needs seeded snapshot.
- raw-playwright: wrap model JS in async IIFE; never top-level return.
- browser-agent: providers registry is mutable; custom 'openrouter' adapter must be registered (lib/providers/index.js); openai-compat via OPENAI_BASE_URL works but agent's own loop needs the provider.sort body injected — UNRESOLVED (this is the broken piece).

## Remaining work to finish Round 3
1. sitegeist: wire GLM key via its chrome.storage providerKeys + select model, run 2 reps (extension build done, Chrome on port 9252).
2. Notte: pip install in py3.12 venv, litellm openrouter/z-ai/glm-5.3-flash, 2 reps. NOT STARTED.
3. README: append all Round 3 contenders to the comparison table (same columns), short Pareto/verdict update, round report in artifacts/2026-09-12/report.md.
4. Commit final artifacts and push.

## Final subagent outcomes
- Agent 1 (Linnaeus) CLOSED: agent-browser 0/2 (done-signal missed), browser-control 1/2, cdp-browser 2/2, webctl 0/2. Versions pinned in runner headers.
- Agent 2 (Huygens) CLOSED: browser-agent EXCLUDED (adapter loop never wired; 2 broken runs kept as evidence), BrowserSkill EXCLUDED (extension install), browser-relay EXCLUDED (no attached tab), browser-cli EXCLUDED (extension install).
- Agent 3 (Fermat) CLOSED: agent-chrome-cli 2/2, jarvis-browser 2/2, lightpanda 2/2, page-agent EXCLUDED.

## Subagent state at checkpoint
- Agent 1 (Linnaeus, 01a091cf-f8e2-7871-8a1e-d533850b3824): agent-browser/browser-control/cdp-browser DONE; webctl rerun in flight.
- Agent 2 (Huygens, 01a091d0-4311-74a2-9c2d-806eaba99609): browser-agent broken (2 runs recorded), browser-cli excluded; BrowserSkill/browser-relay unattempted at checkpoint.
- Agent 3 (Fermat, 01a091d0-806a-7721-9230-35470238a173): CLOSED after delivering agent-chrome-cli, jarvis-browser, lightpanda scored + page-agent excluded.


## Round 3 completion addendum (2026-09-12, gh-6-round3-rebench)

Failing-but-scored contenders fixed and re-scored (2 reps each, GLM 5.3-Flash, latency-sorted):

| contender | before | after | root causes fixed |
|---|---|---|---|
| agent-browser | 0/2 (13.7s) | 2/2 (10.1s median) | adapter doc now forces snapshot @refs for the per-todo checkbox + Active filter (CSS `.toggle` and `text=` selectors unreliable); benchlib.parse_verify peels the quoted/escaped JSON string that `agent-browser eval` returns |
| webctl | 0/2 (19.1s) | 2/2 (14.5s median) | observation snapshot must run non-quiet + `--format full` or @refs are hidden; `check` rejects @refs — needs `role=checkbox name~="Toggle Todo" nth=0`; verify() reads completed flags from the profile state.json and the URL from `reload --format kv` (webctl has no JS eval) |
| pinchtab | 0/6 (75.4s) | 2/2 (8.3s median) | pinchtab `type <ref> <text>` is LITERAL — adapter strips the model's wrapping quotes and never sends quote chars; also required a fresh pinchtab server instance (the old one OOM'd on new-tab) |

Exclusions stand, all with evidence JSON in bench-ext/runners/*-EXCLUDED.json: browser-agent (broken Taylor-Bayouth adapter; re-scored Round 4 as visnia-ai/browser-agent), page-agent (hub approval gate), BrowserSkill / browser-cli / browser-relay (extension install not automatable headlessly).

sitegeist: NOT SCORED. Root causes documented in summary.json — branded Chrome silently ignores `--load-extension` (the smoking gun is in the verbose log: "--load-extension is not allowed in Google Chrome, ignoring"); Chrome for Testing loads the extension fine; sidepanel boot needs an interactive first-run (userscripts permission dialog + full agent init) before reps can run. GLM key + model preference are pre-seeded in its IndexedDB.

Notte: NOT RUN (budget closed); next step is a py3.12 venv + litellm openrouter/z-ai/glm-5.3-flash.

Slick solutions worth remembering:
1. Chrome's "Developer mode" tooltip claiming admin management is a red herring — no policy blocks dev mode; the real blocker is the branded-Chrome --load-extension removal. Check for a Chrome for Testing binary (agent-browser ships one) before debugging extension load failures.
2. MV3 extension dialogs can be dismissed headlessly by calling the Lit component's own methods over CDP (e.g. `document.querySelector('userscripts-permission-dialog').handleDeny()`), no OS automation needed.
3. A stuck "Loading..." extension page can mask a pending IDB versionchange lock — deleting the database while blocked, then reopening in a fresh tab, recovers cleanly.

Branch: gh-6-round3-rebench. Artifacts rewritten in place (results 1/2 per contender; stale pinchtab reps 3–8 removed).

## Round 3 fix-up addendum (2026-09-12, issue #11) — extension tools scored

**Root cause of every "extension install not automatable headlessly" exclusion:** branded Google
Chrome silently ignores `--load-extension`; **Chrome for Testing honours it**. New shared helper
`bench-ext/cft_chrome.py` launches CFT (`~/Library/Caches/ms-playwright/chromium-1243/`) with one or
more unpacked extensions; `bench-ext/cdp.mjs` does targeted CDP eval/screenshot against a target
matched by URL (used for page-agent seeding + verification).

| Contender | Runner | Reps | Median | What actually unblocked it |
|---|---|---:|---:|---|
| BrowserSkill | `runners/BrowserSkill.py` | 2/2 | 4.1s | wxt build of `apps/extension` (`dist/chrome-mv3`) loaded into CFT; `bsk` daemon `ws 127.0.0.1:52800` sees it. `bsk` needs a session first (`bsk session start`), then `fill/press/click/evaluate/screenshot --session <id>`. |
| browser-relay | `runners/browser-relay.py` | 2/2 | 4.3s | bundled `extension/` loaded directly; relay on `127.0.0.1:18795`. **Gotcha:** its `key` builds an invalid Enter event (`code:""`, `windowsVirtualKeyCode:69`) and CDP key events only reach the page when its window is foreground — `browser-relay focus --tab <id>` in setup fixes it. |
| browser-cli | `runners/browser-cli.py` | 2/2 | 6.2s | prebuilt `apps/extension/.output/chrome-mv3` loaded; daemon on **9333** (9222 is the user's own Chrome debug port) and the extension rebuilt with `VITE_WS_PORT=9333`. `tab list --json` is the reliable way to read the tab id. |
| page-agent | `runners/page-agent.py` | 0/2 | ~527s | Approval gate = `chrome.storage.local.allowAllHubConnection`, seeded in the **extension's own service-worker** context over CDP (a web page has no `chrome.storage`, which is why earlier seeds no-op'd). MCP bridge auto-`open`s the launcher in the default browser → neutered with a no-op `open` on PATH so the user's Chrome cannot race for the hub slot. **Second bug:** sending LLM config over the wire makes `useHubWs` call `configure()` → `useAgent` re-renders → the running agent is disposed ("Task aborted"). Seeding `llmConfig` into `chrome.storage.local` and sending **no** config avoids it. Result: the agent runs, but page-agent has **no key-press action**, so it cannot commit a TodoMVC todo → 0/2. |
| notte | `runners/notte.py` | 2/2 | 171.8s | Python 3.12 uv venv (`/tmp/notte-venv`) + `notte` 1.9.0; agent on OpenRouter/GLM via `NOTTE_CONFIG_PATH` → `reasoning_model = "openrouter/z-ai/glm-5.3-flash"` + `ENABLE_OPENROUTER=true`. Screenshot bytes are `session.screenshot().raw`. High variance (116–228s). |

**Taylor-Bayouth browser-agent:** exclusion row removed — tool rewritten as `visnia-ai/browser-agent`
and re-scored 2/2 @ 32.5s in Round 4 (`bench-ext/artifacts/2026-09-13/`).

**Still excluded:** sitegeist. Build blocked upstream — `@mariozechner/pi-agent-core@0.85.1` imports
`DEFAULT_MAX_AGENT_RETRY_DELAY_MS` / `retryDelayMs` from `@earendil-works/pi-ai@0.85.1`, which exports
neither (neither the nested npm copy nor the vendored `pi-mono/packages/ai/dist`). No `dist-chrome` ⇒
the sidepanel-first-run patch can't be applied. Needs a pi-ai/pi-agent-core version realignment upstream.

**Harness gotchas worth keeping:**
1. Hand-rolled MCP stdio clients must not use a bare blocking `readline()` for timing out — use
   `select.select` on the pipe, or the runner hangs past its own budget (hit twice).
2. Background `nohup ... &` processes are reaped when the tool call returns; run long installs in a
   foreground session instead.
3. Never log the seeded `llmConfig` — it carries the OpenRouter key (CI scans artifacts for `sk-or-v1-`).

## Correction + recipe: sitegeist builds (2026-09-12, end of session)

The earlier "build blocked upstream / needs dependency realignment" reading in the README was **wrong**.
sitegeist's `dist-chrome` builds in this clone after two changes:

1. Pin the pi-* packages to the self-consistent **published 0.73.1** family instead of the broken mix:
   ```json
   "@mariozechner/pi-agent-core": "0.73.1",
   "@mariozechner/pi-ai": "0.73.1",
   "@mariozechner/pi-web-ui": "0.73.1"
   ```
   Why the mix breaks: sitegeist points `pi-agent-core` at the vendored `../pi-mono/packages/agent`
   (0.85.1), whose `dist/harness/config.js` imports `DEFAULT_MAX_AGENT_RETRY_DELAY_MS` /
   `retryDelayMs` from `@earendil-works/pi-ai` — and **no published `pi-ai` exports those symbols**
   (the vendored `pi-mono/packages/ai/dist/utils/retry.js` does, at lines 78-79, but npm resolves the
   stale nested copy instead). `pi-web-ui` additionally points at `file:../pi-mono/packages/web-ui`,
   which **does not exist** in the vendored tree at all. Aligning all three to npm 0.73.1 removes both.
2. `npm i @opentelemetry/api` — required by `@mistralai/mistralai` (transitive via `pi-web-ui`).

Then `npm run build:chrome` succeeds (`Built for chrome in .../dist-chrome`).

**Still unscored** (the only remaining work): the sidepanel first-run. Needs `src/sidepanel.ts`'s
`if (!chrome.userScripts) await UserScriptsPermissionDialog.request()` replaced with warn+continue for
headless, the OpenRouter key + `z-ai/glm-5.3-flash` seeded (`sitegeist-storage` → `provider-keys` → openrouter,
and `DEFAULT_MODELS` at `src/sidepanel.ts:108`), and the sidepanel driven headlessly (open
`chrome-extension://<id>/sidepanel.html` as a tab and drive the Lit UI over CDP). Cache-bust with
`rm -rf` is avoided; the clone's `package.json` is tracked, so `git checkout -- package.json` restores it.

**page-agent**: would pass if it had a key-press action — its source even carries `// @todo send_keys`
next to the tool table (`packages/core/src/tools/index.ts`). Two reportable upstream findings:
(a) missing `send_keys` tool (its `execute_javascript` could dispatch the key, but the model never tried);
(b) sending LLM `config` over the hub wire makes `useHubWs` call `configure()` → `useAgent` re-renders →
the in-flight agent is disposed ("Task aborted"); seed `chrome.storage.local.llmConfig` and send no config.

## Round 5 addendum (2026-09-12) — the two browser-agents, page-agent, sitegeist

| Tool | Result | Root cause found |
|---|---|---|
| browser-agent (Taylor-Bayouth) | **1/2**, median 200.1s | NOT an adapter bug (tool calls parse fine). Its Chrome uses a PERSISTENT isolated profile (`~/.browser-agent/profile`); `launch()` early-returns the existing port, so a stale browser from a previous run was silently reused (it was working a Grafana tab). Fix: kill that profile's Chrome, wipe the profile, pre-launch via the tool's own `launch()`, assert the task URL is in front. Rep 2 = 9.2s clean pass; rep 1 = 391s, left **4 todos** but reported "Task complete" (false success, caught by the shared verifier). Its OpenAI-tuned 10s per-call timeout was raised to 30s for OpenRouter. |
| page-agent | **2/2**, median 25.3s (**patched**) | Two real defects: (1) no key-press action (upstream `// @todo send_keys`) so it can never commit a TodoMVC todo — stock = 0/2; (2) key events dispatched from the extension's isolated content-script world never reach React. |
| browser-agent (visnia-ai) | already scored R4 2/2 @ 32.5s | unrelated same-name project |
| sitegeist | **unscoreable** at 104788c | Builds with `pi-*`@0.73.1 + `@opentelemetry/api`, then `TypeError: agent.appendMessage is not a function` — needs pi-agent-core 0.85.x (unpublished); vendored pi-mono has no `packages/web-ui` and won't build (`tsgo` missing, `pi-telemetry` unbuilt). |

### page-agent patch (bench-local fork; stock 0/2 recorded separately)
1. `packages/core/src/tools/index.ts` — new `send_keys` tool (key + optional index), replacing the `// @todo send_keys`.
2. `packages/page-controller/src/{actions,PageController}.ts` — `pressKeyElement` / `resolveKeyTargetElement` / `pressKey`.
3. `packages/extension/src/agent/RemotePageController.background.ts` — handle `press_key` by dispatching in the page's **MAIN** world via `chrome.scripting.executeScript`, targeting **`targetTabId`** (using `sender.tab.id` injects into the agent's own UI tab and silently no-ops — that mistake cost a run).
4. `packages/extension/wxt.config.js` — add `scripting` permission.

**General lesson worth keeping:** a synthetic `KeyboardEvent` dispatched from a content script (isolated world) does NOT reach the page's React listener; the identical dispatch from the MAIN world commits fine. Mouse events are unaffected. Probe it by dispatching from the main world via CDP before blaming the tool.

### sitegeist recipe (for whoever retries)
`@mariozechner/pi-agent-core` + `pi-ai` + `pi-web-ui` all `file:../pi-mono/packages/*` (sitegeist's shipped deps) is unreproducible: `packages/web-ui` does not exist in the vendored clone, and the monorepo build fails on a missing `tsgo`. Pinning all three to the published 0.73.1 family builds but lacks `agent.appendMessage`. Needs upstream to publish a consistent 0.85.x set (incl. web-ui).
Also patched for headless: `src/sidepanel.ts` must NOT call `UserScriptsPermissionDialog.request()` (it only settles on a human click, so first-run blocks forever) — warn + continue.
