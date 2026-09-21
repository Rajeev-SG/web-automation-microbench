# adaptive-ui-runtime — microbench contender notes

Adapter: `bench-ext/runners/adaptive-ui-runtime.py` (own-loop) +
`bench-ext/runners/adaptive-ui-runtime-driver.py` (in-runtime driver).

## What is being measured

`adaptive-ui-runtime` is an **own-loop** contender, like `notte` / `skyvern` /
`browser-use-pi`. It ships its own `plan -> route -> act -> verify` engine
(`Engine.execute`), so **one runtime run is timed per rep**, never one primitive
action per model call (issue #34 fairness rule). The runtime is invoked exactly as
the CLI/MCP invoke it — one `Engine.execute` — from its own venv
(`.venv/bin/python`), and the contender wall time is that single process call
(plus Chrome attach/reset, which is untimed setup).

## Version / commit pin

| | |
|---|---|
| runtime | `/Users/rajeev/Code/adaptive-ui-runtime` |
| commit | `2c6276ce1fa86e7d2dabbf90e343f885cc07a5ef` (`2c6276c`) |
| `src/**/*.py` code digest (sha256) | `8205f1f69e3124fdc8d6d19c0142b29a14febb74486b12619a6e7ddde789593d` |
| venv | `.venv` (Python 3.12) |
| transport used | `cdp-attached` — the runtime's own `IsolatedBrowserTransport` with **only** the browser launcher replaced by `playwright.chromium.connect_over_cdp(...)` |

## Model config

- Strong manager: `openrouter:z-ai/glm-5.3-flash` (runtime default `AUR_MANAGER_MODEL`),
  temperature 0, `max_tokens` 200 for a single action decision.
- Jev fast path: `classifier.dev` (`jev-1.13.0`) — **not** an OpenRouter call.
- Fara / ShowUI: not invoked on these task classes (DOM-addressable).
- The runtime does **not** pass OpenRouter `provider: {"sort": "latency"}` through.
  Every other benchlib contender that calls OpenRouter directly does (spec §Model
  config). This is a real, recorded deviation: the runtime's manager calls use
  OpenRouter **default routing**, so its wall time is not latency-optimised the way
  `browser-relay` / `raw-playwright` are.

## How it is driven

1. The microbench launches Chrome for Testing (`cft_chrome.py`) and, untimed, clears
   state and writes a request JSON (goal + success criteria + start URL + budget).
2. The driver subclasses the runtime's `IsolatedBrowserTransport` and replaces
   **only** the launcher with `connect_over_cdp("http://127.0.0.1:<port>")`, then runs
   one `Engine.execute`. The runtime ships **no** CDP transport (`isolated` launches
   its own browser), so this subclass is the adapter's bridge — the microbench is
   never forked and the runtime is never modified.
3. The success criterion is the task's own verifier: `verify_js` +
   declarative `pass_rule` ride on the criterion as `{js, microbench_pass_rule}`,
   mirroring `adaptive_ui_runtime.microbench.build`. So the runtime's verifier applies
   the task's real rule with its own code, and reports its own `verified` flag.
4. Untimed, the microbench verifies **independently** over CDP with the task's own
   `verify_js` + `pass_rule` (`benchlib` / `pass_rule.py`). Pass = independent
   evidence only; the runtime's own verdict is recorded separately as
   `runtime_verified` so any disagreement is visible.

## Model engagement across the screened runs (honest reading)

The manager and Jev **did** engage on the decision classes — they are not uniformly
zero. Across the 24 screened runs:

| task | manager_calls (rep1/rep2) | jev_calls | manager tokens in/out |
|---|---:|---:|---:|
| `todomvc` | 6 / 7 | 0 | 2,814–3,283 / 171–204 |
| `porsche-uk-script-inventory` | 3 / 7 | 5 | 3,497–8,957 / 838–1,730 |
| `porsche-uk-tag-inspection` | 0 / 3 | 5 | 0–1,839 / 0–325 |
| `chanel-gb-pdp-tag-inspection` | 0 / 1 | 0 | 0–1,077 / 0–270 |
| `tldraw-three-shape-diagram` | 1 / 1 | 0–1 | 454 / 86–199 |
| the 7 single-page audit tasks | 0 | 0 | 0 |

So the configured manager/Jev paths executed and are reflected in the tokens/cost.
The **single-page DOM/eval audit tasks made zero model calls** because the runtime's
router sends them straight to its structured route ("structured target resolved
unambiguously") and then fails there — no manager decision is ever requested for
those classes. That is a routing outcome, not a credential failure: the same env
produced manager calls on `todomvc` in the same screening pass. The token columns
are therefore the manager usage only (Jev is classifier.dev, no tokens), as stated
above.

## Comparability caveats (explicit)

- **Manager calls go to OpenRouter; Jev calls go to classifier.dev.** `tokens` /
  `cost` here are the runtime's manager usage only. Jev is a classifier.dev call the
  runtime does not expose token counts for, so token/cost are a **lower bound** and
  are not directly comparable to a contender that puts every decision through one
  OpenRouter model (`browser-relay`, `raw-playwright`).
- **No window-resume semantics.** The CLIs (`browser-relay`, `raw-playwright`) hold a
  warm browser/REPL across the loop; the runtime here attaches fresh per rep and runs
  one execute. Wall time therefore includes attach + reset setup that the
  thin-CLI contenders amortise.
- **Wall time includes manager decision latency on decision classes.** A class that
  needs a manager decision pays one OpenRouter round-trip (observed manager latency
  ~1–28 s per rep) inside the timed window; deterministic/structured classes pay 0.
- **Different model roles than the shared benchlib GLM loop.** The shared contenders
  use one `z-ai/glm-5.3-flash` chat loop (temperature 0, reasoning low, latency
  routing). The runtime uses a typed planner (`ManagerPlanOut` / `ActionDecisionOut`)
  plus a `classifier.dev` fast path plus a rule-based router. Same instrument, same
  task, same verifier — different agent architecture, which is the point of an
  own-loop row.
- **The runtime's own published TodoMVC result is not comparable.** Its `results/RESULTS.md`
  reports `deterministic_dom_two_todos` 5/5 — but with **benchmark-authored structured
  `steps`** (`[{type, target_any:textbox, value}, {key, Enter}, ...]`). The microbench hands
  every contender only the instruction text and lets it decide its own actions; this adapter
  therefore supplies **no** hand-authored steps (doing so would be forcing the answer). Under
  that same contract the runtime scores 0/2 here. The two numbers measure different things.
- **`stale_target` failures are the runtime's own logic.** The runtime's `structured_browser`
  route resolves a target from one observation and acts on it without re-observing; when the
  first click navigates (e.g. accepting a consent banner on a real site), the next action's
  stamped node is gone and the action fails closed. This is `IsolatedBrowserTransport`'s own
  behaviour, inherited unchanged — the adapter only replaces the browser launcher.

- **No page-eval action.** The runtime's action vocabulary is
  click / type / key / select / scroll / wait / focus / inspect (`Engine._act`); every
  harvested corpus audit task requires the agent to **write** `window.__bench_finding`
  with one eval. The runtime has no action that can do this, so audit tasks are
  structurally unreachable for it (see results). This is a runtime capability gap,
  recorded, not a harness defect.

### `stale_target` is the runtime's own binding, established by a reference-transport control

The top failure class on the corpus (`stale_target`, e.g. 16 identical `click` attempts
on node `n3` for `allbirds-uk-add-to-cart-tag-check`) is **not** an artifact of the
adapter's CDP bridge. Control: re-running the same tasks through the runtime's **own
native `IsolatedBrowserTransport`** (real launched Chromium, no CDP subclass, no adapter
code at all) reproduces the same classes:

```
allbirds-uk-add-to-cart-tag-check  → status=failed  failure_class=stale_target        (12.0s, mgr=0 jev=0)
porsche-uk-tag-inspection          → status=failed  failure_class=repeated_action_loop (32.6s, mgr=0 jev=5)
```

That is the same code path the runtime runs anywhere else; it resolves an ordinal node
(`n3`) from one observation, acts without re-observing, and its stamp-revalidation
(`IsolatedBrowserTransport._sel` → `_STAMP_JS`) fails closed when the first click
navigated. The adapter only replaces the browser launcher and inherits all of this
unchanged, so the failure class is attributable to the runtime, with this control as
evidence.

## Results

2-rep screening on the default `todomvc` task and on real harvested corpus tasks.
Reproduce:

```bash
export OPENROUTER_API_KEY=$(security find-generic-password -s codex-openrouter -a default -w)
python3 bench-ext/corpus/screen_native.py --harness adaptive-ui-runtime --reps 1,2 \
    --tasks todomvc,porsche-uk-tag-inspection,rajeevg-seo-metadata-audit,puma-uk-seo-metadata-audit \
    --out bench-ext/artifacts/<date>/corpus/adaptive-ui-runtime
```

Per-rep run JSON (including every route/action/verify event) lands beside the
summary; `independent_pass` and `runtime_verified` are both recorded.

## Verdict-disagreement classes

`runtime_verified` is recorded beside `independent_pass`, and the run JSON now also
carries `vacuous_self_pass` (true when the runtime reported success while the recorded
`finding` was null/empty and the independent verifier failed) and a named
`disagreement_class`. On this screening that flagged **2** runs — both
`tldraw-three-shape-diagram`, where the runtime self-passed an empty structural truth.
Read `runtime_verified` as the runtime's own opinion only; `independent_pass` is the
score.
