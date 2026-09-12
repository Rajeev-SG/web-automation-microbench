# Delivery run (issue #20) — top-2 harnesses on a real, auth-free task

**Date:** 2026-09-12-delivery · **Task:** `chanel-gb-tag-check` · **Model:** `z-ai/glm-5.3-flash`
via OpenRouter (temperature 0, reasoning low+excluded, `provider.sort=latency`).
**Method unchanged** from every scored round: independent verifier, timer starts at the
first model call, setup/reset before the timer, verify+screenshot after.

This run proves the issue #20 task-parameterized benchmark works end-to-end on a task that
is **not** TodoMVC, and exercises the issue #1 adaptive-replication topology. It is a
*delivery demonstration*, not a new leaderboard entry.

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

| Harness | Reps | Pass | Screen | Median (all) | Median (passes) | Tokens in/out | Cost/run |
|---|---:|---:|---:|---:|---:|---:|---:|
| browser-relay | 5 | 4/5 | 1/2 | 2.9s | 2.7s | ~3.0k / ~137 | ~$0.0003 |
| BrowserSkill | 5 | 3/5 | 2/2 | 13.0s | 10.4s | ~28.0k / ~753 | ~$0.0030 |

(Rows are generated from `summary.json`, derived from the per-rep JSON in this directory.)

## Why both harnesses ran 2 then 5 reps

The issue #1 topology is now config in `benchlib.REP_TOPOLOGY` (2 screen → 5 promote →
10+ tiebreak). Both harnesses screened 2 reps and were promoted to 5.

**The promotion mattered — twice, and in opposite directions — which is the whole point of
the topology.**

- **browser-relay screened 1/2 and looked weak; over five reps it is 4/5.** The single
  screening failure (rep 1) was a model-side JS-quoting breakdown, not a harness property;
  reps 2–5 all passed in ~2.5s. Two reps alone would have badly understated it — exactly the
  failure mode issue #1 exists to prevent.
- **BrowserSkill screened a clean 2/2 and looked perfect; over five reps it is 3/5.**
  Two reps would have overstated it. This reproduces the Round 6 chrome-cdp-skill lesson.

So the promotion correction ran in **both** directions here: screening over-scored one
contender and under-scored the other.

## Failure attributions (every failed rep preserved, none retried away)

- **1-browser-relay** (`adapter-protocol`): the model's `eval` payloads produced a JS
  `SyntaxError: Unexpected token '}'` on **9 of 10 steps** (a quoting/escaping interaction
  with the `browser-relay eval` CLI), so `window.__bench_finding` stayed `null`. Same task,
  same harness, next four reps passed with a 1-call payload — a model/quoting flake captured,
  not papered over.
- **3-BrowserSkill** (`task-state`, done never signalled): the model kept re-issuing an
  `evaluate` whose JS it kept corrupting — inserting non-breaking spaces
  (`.replace(/ /g,'\xa0')`) — and never set `window.__bench_finding`, then hit the 10-step cap.
- **4-BrowserSkill** (`task-state`, done signalled): the model identified the correct tags but
  stored a **JSON string** (`JSON.stringify(...)`) in `window.__bench_finding` instead of the
  object the instruction asked for. The independent verifier correctly failed it — the
  agent's own "done" is never sufficient.

Diagnostics captured per rep: model-call count, tool-call count, retries, recovery, tool
errors, provider and cost (`benchlib.run_rep`). Tool errors alone did not flag these — the
harness returned success strings while the *page* rejected the JS — which is why the
independent verifier and the per-rep `done` flag matter.

## Scope / honesty notes

- This is **delivery evidence for the parameterization**, not capability evidence about
  chanel.com and not a leaderboard change. No root-README results table was touched.
- Both harnesses' system prompts were made **task-agnostic** (they now teach the tool, not
  the TodoMVC job) — a prerequisite for running any second task, and a strict improvement.
- The task set is otherwise **empty**: `bench-ext/tasks_real.py` holds this one delivery
  task; the harvested corpus waits on `codex-session-orchestration-analysis#88`.
