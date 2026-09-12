# Delivery run (issue #20) — top-2 harnesses on a real, auth-free task

**Date:** 2026-09-15 · **Task:** `chanel-gb-tag-check` · **Model:** `z-ai/glm-5.3-flash`
via OpenRouter (temperature 0, reasoning low+excluded, `provider.sort=latency`).
**Method unchanged** from every scored round: independent verifier, timer starts at the
first model call, setup/reset before the timer, verify+screenshot after.

This run exists to prove the issue #20 task-parameterized benchmark works end-to-end on a
task that is **not** TodoMVC. It is a *delivery demonstration*, not a new leaderboard entry.

## The task (real work, no auth)

`chanel-gb-tag-check` is the auth-free, replayable encoding of the CHANEL marketing-tag QA
rounds: open the public CHANEL UK homepage and record which marketing tags the live page
actually carries — the Google Tag Manager container id set, Google Ads (`AW-`) presence and
Pinterest tag presence. It is **not hand-authored**: provenance is derived from the
AgentSessions DB (`source_session_id 01a08735-…`, the CHANEL tag-QA session) and validated
through `bench-ext/task_intake.py`. The agent records its finding in
`window.__bench_finding`; the verifier **independently recomputes the tag ground truth from
the live page** and compares — a run passes only if the agent's finding matches that
independent recomputation *and* the agent signalled done.

## Results

| Harness | Reps | Pass | Median (all) | Median (passes) | Tokens in/out | Cost/run |
|---|---:|---:|---:|---:|---:|---:|
| BrowserSkill | 5 | 3/5 | 13.0s | 10.4s | ~28.0k / ~753 | ~$0.0030 |
| browser-relay | 2 | 1/2 | 16.2s | 2.9s | ~28.9k / ~1,270 | ~$0.0040 |

(Rows are generated from `summary.json`, which is derived from the per-rep JSON in this
directory. browser-relay screened only — see the promotion note.)

## Why BrowserSkill ran 5 reps and browser-relay only 2

The issue #1 topology is now config in `benchlib.REP_TOPOLOGY` (2 screen → 5 promote →
10+ tiebreak). BrowserSkill screened **2/2** and was promoted to 5; browser-relay screened
1/2 and was not promoted.

**The promotion mattered — and reproduces the Round 6 lesson.** On 2-rep screening
BrowserSkill looked like a clean 2/2. Over five reps it is **3/5**: reps 3 and 4 failed.
A 2-rep screen overstates reliability, exactly as the Round 6 chrome-cdp-skill result
showed. This is the strongest evidence yet that the adaptive-replication topology earns its
keep.

## Failure attributions (every failed rep preserved, none retried away)

- **3-BrowserSkill** (`task-state`, done never signalled): the model kept re-issuing an
  `evaluate` whose JS it kept corrupting — it even inserted non-breaking spaces
  (`.replace(/ /g,'\xa0')`) — and never set `window.__bench_finding`, then hit the 10-step
  cap.
- **4-BrowserSkill** (`task-state`, done signalled): the model identified the correct tags
  but stored a **JSON string** (`JSON.stringify(...)`) in `window.__bench_finding` instead
  of the object the instruction asked for. The independent verifier correctly failed it —
  the agent's own "done" is never sufficient.
- **1-browser-relay** (`adapter-protocol`): the model's `eval` payloads produced a JS
  `SyntaxError: Unexpected token '}'` on **9 of 10 steps** (a quoting/escaping interaction
  with the `browser-relay eval` CLI), so `window.__bench_finding` stayed `null`. The model
  did not vary the broken pattern and hit the step cap.

Diagnostics captured per rep: model-call count, tool-call count, retries, recovery, tool
errors, provider and cost (`benchlib.run_rep`). Tool errors alone did not flag these — the
harness returned success strings while the *page* rejected the JS — which is why the
independent verifier and the per-rep `done` flag matter.

## Scope / honesty notes

- This is **delivery evidence for the parameterization**, not capability evidence about
  chanel.com and not a leaderboard change. No root-README table was touched.
- The task set is otherwise **empty**: `bench-ext/tasks_real.py` holds this one delivery
  task; the harvested corpus waits on `codex-session-orchestration-analysis#88`.
- Both harnesses' system prompts were made **task-agnostic** (they now teach the tool, not
  the TodoMVC job) — a prerequisite for running any second task, and a strict improvement.
