# Runner instructions (shared context for all contender runners)

Repo: /Users/rajeev/Code/web-automation-microbench (worktree: bench-ext/)
Contender sources cloned under bench-ext/work/<name>/
Results: bench-ext/artifacts/2026-09-12/results/{rep}-{name}.json + .png
Shared library: bench-ext/benchlib.py (import benchlib after sys.path.insert(0,'/Users/rajeev/Code/web-automation-microbench/bench-ext'))

OpenRouter key: `security find-generic-password -s codex-openrouter -w`
Run scripts with: OPENROUTER_API_KEY=$(security find-generic-password -s codex-openrouter -w) python3 <runner>.py

Model config (MUST, every call — benchlib.openrouter_call / openrouter_payload already enforce it):
  model z-ai/glm-5.3-flash, temperature 0, reasoning effort low + excluded, response_format json_object,
  provider {"sort": "latency"}. Never :nitro. Record provider per call.

Task + verification + timing + schema: DO NOT reimplement — use benchlib.
  The library is TASK-PARAMETERIZED (issue #20): a task registry holds tasks of
  {id, instruction, url, observe_js, verify_js, check, capabilities[], provenance{}}.
    benchlib.get_task(id)            -> resolve a task (None => default 'todomvc')
    benchlib.run_rep(adapter, rep, task=<id>, max_steps=..., timeout=...)
  run_rep binds the chosen task to the historical module globals (benchlib.TASK / URL_TASK /
  OBS_JS / VERIFY_JS), so adapters that read those globals keep working unchanged. It
  implements the whole loop, token accounting, diagnostics, the timer (starts at first model
  call; setup before, verify/screenshot after) and writes the JSON + prints a summary.
  Every rep JSON also carries: task, tool_calls, retries, recovery, tool_errors, provider, cost.
  Failed reps are PRESERVED — never replaced with a retry.

Reps (issue #1 topology, centralized — do not hardcode):
    benchlib.REP_TOPOLOGY = {screen: 2, promote: 5, tiebreak: 10}
    reps = benchlib.reps_from_argv(sys.argv[1:])   # explicit reps from argv, else ['1','2']
  2 reps screen everything; promote plausible candidates to 5; 10+ only for near-ties/high
  variance. A failed rep is recorded, never retried away.

Runner flags: `python3 runners/<name>.py [reps...] [--task=<task-id>]`.
  --task   select a registered task (default: todomvc); parsed by benchlib.cli_reps_and_task
  BENCH_RES=<dir>   override the results directory (default artifacts/<today>/results, derived
                  from the wall clock at import — issue #27 removed the frozen future date)
  Entrypoint helper: `benchlib.run_cli(Adapter, max_steps=N)` — one line, parses reps + --task.
  TASK-AWARE (21): BrowserSkill, agent-browser, agent-chrome-cli, bb-browser, browser-act-skills,
  browser-cli, browser-control, browser-relay, cdp-browser, chrome-cdp-skill, chrome-devtools-mcp,
  ego-browser, hyperagent, jarvis-browser, lightpanda, opencli, pinchtab, playwright-cli,
  raw-playwright, surf-cli, webctl.
  NOT YET TASK-AWARE (5): browser-agent-tb, midscene, notte, page-agent, skyvern — these ship
  their own agent loops (they do not call benchlib.run_rep), so a task id needs per-tool wiring.
  They hardcode the TodoMVC task and must not be cited for any other task until wired.

Tasks: anything other than the TodoMVC latency microbenchmark is REAL WORK and must be
  session-derived. There is no hand-authored task module any more (issue #27 removed
  tasks_v1.py / tasks_real.py): the capability suite is the vendored harvested corpus under
  bench-ext/corpus/tasks/, ingested at import by bench-ext/task_ingest.py. Every non-TodoMVC
  task carries mandatory provenance (source_session_id, source_url, verified_against) plus the
  #88 definition contract (definition_schema, capabilities, declarative pass_rule, pre_state,
  no secret_dependency/blocked_reason); task_intake.py REJECTS a task missing any of them.
  Derive session ids from the AgentSessions DB read-only — never copy them out of a doc.
  See docs/task-intake.md and docs/REAL-WORK-MANDATE.md.

  Task execution budget: a harvested task carries its own max_steps/timeout (default 14 steps /
  300 s) set by task_ingest; TodoMVC keeps the 10-step default. run_rep resolves the budget
  from the task when the caller does not pass one.

  Screening the corpus (issue #27):
    python3 bench-ext/corpus/screen.py --harness <name> --reps 1 --all
    python3 bench-ext/corpus/report.py --run-dir bench-ext/artifacts/<date>/corpus
  screen.py discovers the adapter class from the runner module (class names vary), writes one
  directory per task under the harness, and never retries a failure away.

Adapter contract (subclass or duck-type):
  .name (contender id used in filenames)
  .doc (system prompt: thin native usage of THIS tool, one logical action per step, JSON {"code":...,"done":false} or {"done":true})
  .start() -> (handle, initial_observation)   # BEFORE timer: fresh page, clear localStorage, reload task URL
  .act(handle, code) -> (observation, elapsed_seconds)
  .verify(handle) -> string containing VERIFY_JS JSON result   # AFTER timer
  .screenshot(handle, path)
  .teardown(handle)

State hygiene: fresh tab/page per rep, localStorage cleared before reload, no tab reuse.

State reset recipe (adapt per tool): goto URL_TASK, eval localStorage.removeItem('react-todos'), goto URL_TASK again, then run OBS_JS.

Chrome availability: system Chrome at /Applications/Google Chrome.app/Contents/MacOS/Google Chrome.
Use a dedicated automation profile per tool and a dedicated --remote-debugging-port per tool:
  agent-browser 9241, browser-control 9242, cdp-browser 9243, webctl 9244, browser-agent 9245,
  jarvis-browser 9246, agent-chrome-cli 9247, pinchtab 9248, raw-playwright uses its own bundled chromium.
Launch example: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --remote-debugging-port=PORT --user-data-dir=/tmp/bench-chrome-<name> --no-first-run --no-default-browser-check about:blank &

Costs: record OpenRouter usage tokens; cost = tokens * published latency-sorted provider rate
  (Makora: $0.075/M input, $0.25/M output, cached input ~half) unless the tool reports cost itself.

Reps: screen at 2 scored reps per contender, then follow the issue #1 topology (promote to 5;
10+ only for near-ties/high variance). Record failures as failures; do not substitute or retry away.

Exclusion: if a tool cannot use GLM/OpenRouter cleanly or cannot run on this machine after a genuine
attempt, do NOT run it with another model. Write bench-ext/runners/<name>-EXCLUDED.json with
{"contender": name, "excluded": true, "reason": "..."} and report it.

Deliverables per contender (worker-owned directory bench-ext/runners/):
  runner script, 2x {rep}-{name}.json in results, 2x screenshots, and a final report line:
  {contender, version_or_commit, passes "x/y", median_s, tokens_in/out per run, cost_per_run_usd, setup_notes}

## Chrome for Testing extension loading (issue #11 fix-up)

Branded Google Chrome silently ignores `--load-extension`; Chrome for Testing honours it. Use
`bench-ext/cft_chrome.py`:

```python
from cft_chrome import Chrome
c = Chrome(port=9290, extensions=['/abs/path/to/unpacked-extension'], start_url='about:blank')
c.launch()                       # waits for CDP; see c.targets() / c.extension_workers()
```

Helpers: `bench-ext/cdp.mjs <port> eval|shot <url-substring> <arg>` for targeted CDP eval/screenshot.
Gotchas: (1) hand-rolled MCP stdio clients must use `select.select` for timeouts or they hang;
(2) CDP keyboard events only reach a page whose window is foreground — browsers that press keys
(browser-relay `key`/`--submit`) need an explicit `focus` step; (3) never log seeded provider config
(contains the API key) into artifacts.

## Round 5 gotchas (2026-09-12)
- **Persistent-profile tools silently reuse a stale browser.** browser-agent's `launch()` early-returns the existing
  debug port for its profile, so a browser left over from a previous run (on the wrong page) is reused. Kill that
  profile's Chrome *before* wiping the profile, then pre-launch and assert the task URL is in front.
- **Content-script (isolated world) keyboard events do not reach React.** Mouse events do. Dispatch keys from the
  page's MAIN world (`chrome.scripting.executeScript({world:'MAIN'})` from the background) — and target the tab the
  agent is driving (`targetTabId`), never `sender.tab.id` (that injects into the agent's own UI tab).
- **Synthetic Enter commits React inputs fine** when dispatched on the focused (or last-clicked) input; `document.activeElement`
  is often `<body>` after a tool blurs between actions, and a keydown on `<body>` bubbles *up*, missing React's root listener.
- page-agent's approval gate is `chrome.storage.local.allowAllHubConnection`, seeded in the **extension's service-worker**
  context (a web page has no `chrome.storage`), and its MCP bridge auto-`open`s a launcher in the default browser → neuter
  with a no-op `open` on PATH so the user's Chrome can't race for the hub slot.

## Round 7 addendum (2026-09-13) — own-loop harnesses and Browser Use Pi (issue #34)

Contenders that ship their own agent runtime (notte, skyvern, midscene, **Browser Use Pi**) must not be
reduced to a benchlib adapter: one primitive action per model call erases the architecture under test.
Give them a runner exposing `run_native(rep, task=...)` that drives the tool's own loop once per rep,
and screen with `corpus/screen_native.py` (writes the same run JSON, so `corpus/report.py` aggregates
it unchanged).

`runners/browser-use-pi.py` + `runners/browser-use-pi.mjs`:
- Native architecture: Pi Mono agent loop -> persistent V8 REPL -> raw CDP -> Chrome. PINNED to
  `@browser_use/pi` 0.1.0 @ `fa838f3`; reproduce with `runners/browser-use-pi-setup.sh`
  (clone -> pin -> `npm install` -> `npm run build`). Needs Node >= 22.19.
- GLM 5.3 Flash is NOT in Pi's pinned catalog. The `.mjs` registers it into a custom Models collection
  with `compat.openRouterRouting = {sort:'latency'}` so the OpenRouter payload carries
  `provider:{sort:'latency'}` like every other row. Do not drop this and call the routing "compatible".
- Browser: local Chrome `Browser.chromium({headless:true, profileDir})`. **One fresh profile+workspace
  per rep** (the tool locks a profile to one owner; reusing one leaks cookies/localStorage between
  reps). Own-Chrome mode: `BUPI_MODE=chrome BUPI_CDP_URL=ws://127.0.0.1:<port>/devtools/browser/<id>`.
- Verification: after `agent.run()` and BEFORE `agent.close()`, the runner reads the profile's
  `DevToolsActivePort` and evaluates `VERIFY_JS` on the live page over CDP (Node's global WebSocket);
  pass = task rule AND the agent's own `done`. The node log is on stderr; the driver writes its result
  JSON to a per-rep subdir so `report.py`'s `*/*/*.json` glob never picks it up.
- Gotcha: background `&` jobs are reaped when the tool call returns — run the corpus screen in a
  foreground session and poll.
