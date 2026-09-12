# Round 6 brief — issue #17 remaining contenders

Repo (real path): `/Users/rajeev/Code/web-automation-microbench`  · bench-ext worktree: `bench-ext/`
Shared lib: `bench-ext/benchlib.py` (task text, observation JS, verify JS, model payload, pass predicate, `run_rep`).
Round 6 results dir: `bench-ext/artifacts/2026-09-14/results/`  · Round report: `bench-ext/artifacts/2026-09-14/report.md`

## Hard rules
- Model is fixed: `z-ai/glm-5.3-flash` via OpenRouter, temp 0, reasoning low+excluded, `response_format json_object`, `provider {"sort":"latency"}`. `benchlib.openrouter_payload()` already enforces it. Never `:nitro`. Never substitute another model.
- OpenRouter key: `export OPENROUTER_API_KEY=$(security find-generic-password -s codex-openrouter -w)`
- **Do NOT reimplement** the task, observation JS, verification, timing, schema or token accounting — import `benchlib` and use `run_rep`.
- Native-interface rule: drive each tool through its own intended interface; do NOT hand-write TodoMVC selectors/action sequences the tool would not get from a generic user, and do NOT split a code-mode tool into artificial single calls. But DO give the tool its normal generic capability (a generic CLI may use CSS selectors the way a normal agent would after `snapshot`).
- Timing boundary: setup/reset before the timer, verify+screenshot after. `run_rep` already does this.
- Every runnable contender: ≥2 scored reps, rep ids `1` and `2`. Keep failures as failures.
- If a tool genuinely cannot be installed/configured/run after a reasonable attempt, write `bench-ext/runners/<name>-EXCLUDED.json` = `{"contender":name,"excluded":true,"reason":"...","version":"...","commands":"...","error":"..."}` and report it. That satisfies the acceptance criterion ("scored or evidenced as blocked").
- No fabricated numbers. Every reported number must be derivable from a real result JSON in `artifacts/2026-09-14/results/`.
- Never log the OpenRouter key into any artifact (CI scans for `sk-or-v1-`).

## How to write a runner
Copy the shape of an existing runner (best references):
- extension-backed CLI: `bench-ext/runners/browser-cli.py`, `bench-ext/runners/agent-chrome-cli.py`
- direct-CDP CLI: `bench-ext/runners/cdp-browser.py`
- self-contained native binary: `bench-ext/runners/agent-browser.py`
- own agent runtime: `bench-ext/runners/notte.py`

Skeleton:
```python
import sys, time, pathlib
sys.path.insert(0, '/Users/rajeev/Code/web-automation-microbench/bench-ext')
import benchlib
benchlib.RES = pathlib.Path('/Users/rajeev/Code/web-automation-microbench/bench-ext/artifacts/2026-09-14/results')
benchlib.RES.mkdir(parents=True, exist_ok=True)

class MyTool:
    name = 'mytool'
    doc = ('Drive the browser ONLY with <native interface>. One logical action per step. '
           'Respond as JSON {"code":"..."} for each step and {"done":true} once the final state '
           '(Active filter showing only "Review invoice", 1 item left) is observed. Strict JSON only.')
    def start(self):  # BEFORE timer: fresh page, clear localStorage('react-todos'), reload task URL, return (handle_dict_with_, obs)
        ...
    def act(self, handle, code): ...          # -> (observation_string, elapsed_s)
    def verify(self, handle): ...             # -> stdout of VERIFY_JS result (benchlib.VERIFY_JS)
    def screenshot(self, handle, path): ...
    def teardown(self, handle): ...

if __name__ == '__main__':
    for rep in ['1','2']:
        benchlib.run_rep(MyTool(), rep)
```
`benchlib.run_rep` writes `{rep}-{name}.json` + `.png`, prints a one-line summary. `handle` should be a dict; put `setup_s` in it if you want it logged.

## Chrome
- Chrome for Testing (honours `--load-extension`): `bench-ext/cft_chrome.py` → `Chrome(port, extensions=[...], start_url=...)`. CFT binary at `~/Library/Caches/ms-playwright/chromium-1243/chrome-mac-arm64/Google Chrome for Testing.app/...`.
- Branded Chrome path: `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`.
- Targeted CDP eval/screenshot helper: `bench-ext/cdp.mjs <port> eval|shot <urlSub> <arg>`.
- Gotcha: CDP keyboard events only reach a page whose window is foreground — call the tool's own focus/screenshot first if it presses keys.

## Cost
Cost = tokens × published latency-sorted provider rate (Makora: $0.075/M input, cached ≈ half, $0.25/M output) unless the tool reports its own cost. Record `cost` in the JSON if the tool reports it.

## Deliverable per contender
Runner script in `bench-ext/runners/`, ≥2 result JSONs + PNGs in `artifacts/2026-09-14/results/`, and a final one-line record:
`{contender, version_or_commit, passes "x/y", median_s, tokens_in/out per run, cost_per_run_usd, setup_notes}`
plus any blocked JSON. Report the exact install commands and version/commit SHA you used.
