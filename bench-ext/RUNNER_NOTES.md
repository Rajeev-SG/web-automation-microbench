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
