> **⚠️ STATUS: PARTIALLY INVALID — DO NOT EXTEND THIS SUITE AS WRITTEN.**
> Tasks 2–9 below were hand-authored or generic public-site stand-ins, which
> violates the real-work mandate
> ([REAL-WORK-MANDATE.md](REAL-WORK-MANDATE.md), issue #12). Only task 1
> (TodoMVC) and the 22 measured envelopes in
> `artifacts/2026-09-12/pareto-corpus/` are legitimate real-work evidence.
> Task 2–9 will be replaced by session-derived tasks with mandatory
> provenance (`source_session_id`, `source_url`, `verified_against`) under
> issue #12. Until that lands, this file is a record of what **not** to do.

# Browser task suite v1 (issues #2 + #3)

Compact orthogonal suite. TodoMVC stays the **latency microbenchmark**.
Every task gets: capability tags, an objective verifier, a clean reset, and a
failure class from the shared contract (see
`codex-session-orchestration-analysis/docs/implementation/pareto-research-v1.md`).

Status key: ✅ runnable now · 🚧 implemented, unrun · 📋 specified only.

| # | Task | Capabilities | Level | Source |
|---|------|-------------|-------|--------|
| 1 | TodoMVC add/filter/complete | dom, state | deterministic | existing `benchlib.TASK` |
| 2 | Delayed-load SPA dashboard | dynamic-ui, wait-strategy | deterministic | `bench-ext/fixtures/spa-suite/` |
| 3 | Checkbox grid (20 targets) | dom-volume, robustness | deterministic | `bench-ext/fixtures/spa-suite/` |
| 4 | File upload → confirm | files, multi-step | deterministic | `bench-ext/fixtures/spa-suite/` |
| 5 | Random modal interrupt | modals, recovery | stochastic | `bench-ext/fixtures/spa-suite/` |
| 6 | Infinite scroll → extract ≥15 items | dynamic-ui, long-horizon | stochastic | `bench-ext/fixtures/spa-suite/` |
| 7 | search → extract → act | planning, state-transfer | real-site | wikipedia.org |
| 8 | visual canvas shape-count | vision | real-site | public canvas demo |
| 9 | multi-tab compare | multi-tab, vision | real-site | two public docs sites |

Failure classes (shared contract): `task-state`, `harness-tool`,
`adapter-protocol`, `model-format`, `integration-setup`, `site-environment`.
Reporting keeps the fast-path frontier (latency/cost, tasks 1–4) separate from
the capability frontier (success/recovery, tasks 5–9).

## Runner mechanics

- Same GLM 5.3 Flash / OpenRouter configuration as Round 3; one agent loop per
  contender via the existing `benchlib.run_rep` adapter contract.
- Timer starts at first model call; reset/verify/screenshot excluded, as before.
- Tasks 2–6 run from local static files (deterministic, no external network
  dependency in the task itself).
- `spa-suite` is committed to the repo so the suite is reproducible without
  external sites.

### Task registry + replication (#20)

The suite no longer shares one hardcoded TodoMVC task. `benchlib` carries a task registry
and `run_rep(adapter, rep, task=...)`; each task supplies its instruction, URL,
observation JS, verification JS, pass predicate, capability tags and provenance.
Provenance is mandatory for every non-TodoMVC task (`source_session_id`, `source_url`,
`verified_against`) and is enforced by `task_intake.validate_task_spec` +
`tests/test_task_provenance.py` — never by review alone. Session ids are derived from the
AgentSessions DB (read-only). See [task-intake.md](task-intake.md).

Rep counts are centralized (`benchlib.REP_TOPOLOGY`: 2 screen → 5 promote → 10+ tiebreak,
issue #1); runners fall back to `benchlib.reps_from_argv(sys.argv[1:])` instead of a
hardcoded `['1','2']`. Per-rep diagnostics now include tool-call count, retries/recovery,
tool errors, provider and cost; every failed rep is preserved, never retried away.

**Task set is empty pending `codex-session-orchestration-analysis#88`.** The tasks table
above is a record of what *not* to do until harvested, provenance-carrying tasks arrive.

## v1 verification status (2026-09-12)

All five local deterministic/stochastic pages load in a real Chromium via the
CDP adapter pattern, and their verifiers execute against live DOM:

- `delayed-dashboard` and `infinite-scroll` verifiers fire and correctly report
  not-yet-passable state before the agent acts.
- `checkbox-grid`, `file-upload`, `modal-interrupt` verifiers fire and are false
  until the objective end state is reached.
- `classify_failure()` maps: agent finished wrong state → `task-state`;
  control mechanism timeout → `harness-tool`; unfinished without timeout →
  `adapter-protocol`; unparseable model answer → `model-format`.

Remaining for full v1 acceptance: live model-in-loop scoring runs per contender
per task, plus real-site tasks 7–9 preflight (network-dependent; deliberately
not blocking the local suite).
