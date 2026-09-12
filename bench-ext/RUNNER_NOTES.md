# Round 3 runner instructions (shared context for all contender runners)

Repo: /Users/rajeev/Code/web-automation-microbench (worktree: bench-ext/)
Contender sources cloned under bench-ext/work/<name>/
Results: bench-ext/artifacts/2026-09-12/results/{rep}-{name}.json + .png
Shared library: bench-ext/benchlib.py (import benchlib after sys.path.insert(0,'/Users/rajeev/Code/web-automation-microbench/bench-ext'))

OpenRouter key: `security find-generic-password -s codex-openrouter -w`
Run scripts with: OPENROUTER_API_KEY=$(security find-generic-password -s codex-openrouter -w) python3 <runner>.py

Model config (MUST, every call — benchlib.openrouter_call / openrouter_payload already enforce it):
  model z-ai/glm-5.3-flash, temperature 0, reasoning effort low + excluded, response_format json_object,
  provider {"sort": "latency"}. Never :nitro. Record provider per call.

Task + verification + timing + schema: DO NOT reimplement — use benchlib:
  benchlib.TASK (verbatim instruction), benchlib.OBS_JS (post-action observation JS),
  benchlib.VERIFY_JS (post-run verification JS), benchlib.check_pass, benchlib.parse_verify,
  benchlib.run_rep(adapter, rep) — implements the whole loop, token accounting, timer
  (starts at first model call, setup before, verify/screenshot after), and writes the JSON + prints summary.

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

Reps: minimum 2 scored reps per contender (rep '1' and rep '2'). Record failures as failures; do not substitute.

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
