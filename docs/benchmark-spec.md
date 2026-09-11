# Benchmark specification

This is the contract every round must follow so runs stay comparable. A new task extending this benchmark must read this first.

## Task

URL: https://demo.playwright.dev/todomvc/

Instruction given to the agent (verbatim):

```
Add exactly two todos: "Email supplier" then "Review invoice". Mark ONLY "Email supplier" complete. Click the Active filter. Verify only "Review invoice" is shown and 1 item left. Do not clear completed. Work efficiently with ONE logical UI action per response (adding a todo is one action); observe before next action. Finish only after observing the final state.
```

## Pass criteria (all must hold, verified independently outside the timed loop)

1. Final URL ends with `#/active`.
2. Exactly one todo item visible in `.todo-list li`, and its text contains "Review invoice".
3. That item is not marked completed.
4. Persisted `localStorage["react-todos"]` (key `react-todos`) equals exactly two records:
   - `{"title": "Email supplier", "completed": true}`
   - `{"title": "Review invoice", "completed": false}`

The verification code lives in `VERIFY_JS` (`artifacts/2026-09-11/bench-py.py`) and reads both live DOM and persisted state. A run passes only if `done` was signalled by the agent AND verification matches. Do not simplify the criteria per contender.

## Model + provider config

- Model: `z-ai/glm-5.3-flash` via OpenRouter for every contender.
- Temperature 0, reasoning effort low.
- Provider routing: pass `provider: {"sort": "latency"}` on every direct OpenRouter request. If a framework cannot pass it through, record the cleanest supported equivalent in the round report — never silently fall back to default routing, and never use `:nitro` (that sorts by throughput, not TTFT).
- Record the actual provider used per call (OpenRouter response `provider` field or equivalent).

## Timing boundary

Stopwatch starts at the first model call and stops when the agent signals done or fails. Excludes:
- browser launch/attach,
- initial navigation and state reset,
- independent verification and screenshot capture.

Browser-operation time and per-model-call time are recorded separately where possible.

## Required measurements per run

- task pass/fail (+ failure cause),
- total wall-clock seconds,
- number of model/agent/tool calls,
- input / output / cached / reasoning tokens where observable,
- estimated cost (OpenRouter-reported where available; otherwise exact tokens × the latency-sorted provider's published rate),
- retries/failures/recovery observed,
- whether vision was required,
- setup/integration complexity notes.

## Repetitions

Minimum two scored reps per contender (reversed order for the second to cancel ordering bias). More reps when variance is high (e.g., flaky schema output). A "rep" means a full fresh task from clean browser state.

## State hygiene

- Each rep starts from a clean task state (localStorage cleared, fresh tab/page per contender's normal mechanism).
- Only benchmark-created tabs/pages may be closed afterwards.
- Never reuse a tab with prior task state.

## Adding a new contender

1. Reuse the exact task text and verification predicate above (copy, don't reword).
2. Write a runner (Python or Node) following the pattern in `artifacts/2026-09-11/`:
   - reset state → run agent loop → stop timer → run the same verification → save `{rep}-{contender}.json` + screenshot PNG.
3. JSON transcript shape (keep field names): `id`, `contender`, `rep`, `events[]`, `setup_s`, `total_s`, `model_calls`, `tokens{input,output,cached,reasoning}`, `cost`, `verification`, `pass`.
4. Add the contender to the README table and the round's report; include a Pareto update.
5. Run at least 2 scored reps; record every failure cause.

## Known pitfalls from previous rounds

- `press_key('ENTER')` vs `press_key('Enter')` matters in Browser Harness (uppercase all-caps is not in the key map).
- After `goto_url()` re-navigation, Browser Harness CDP input events can target a stale session — use `new_tab()` for resets.
- Stagehand's strict JSON-schema action format rejects malformed GLM output; plan for model-schema mismatch failures and record them as contender failures, not harness bugs.
- bcode's own OpenRouter route reports cost; other contenders need token-based estimation at the latency-sorted provider's published rates.
