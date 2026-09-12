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
