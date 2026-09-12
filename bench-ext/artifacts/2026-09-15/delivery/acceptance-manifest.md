# Acceptance manifest — issue #20 delivery

Machine-readable evidence for the three steps plus the delivery run. Verified 2026-09-15.

| # | Requirement | Evidence | Status |
|---|---|---|---|
| 1 | benchlib is a task registry; `run_rep(adapter, rep, task=…)` | `bench-ext/benchlib.py` (`Task`, `TASKS`, `get_task`), `tests/test_run_rep_loop.py` | PASS |
| 2 | TodoMVC byte-identical + golden regression test | `tests/golden/todomvc.json`, `tests/test_todomvc_golden.py` | PASS |
| 3 | Existing runners work with a minimal diff | `bench-ext/runners/*.py` unchanged in adapter contract; all parse; `tests/test_replication.py` | PASS |
| 4 | Rep counts centralized; 7 hardcoded runners fixed | `benchlib.REP_TOPOLOGY`, `reps_from_argv`; no runner contains `['1','2']` | PASS |
| 5 | Issue #1 topology as config | `benchlib.REP_TOPOLOGY = {screen:2, promote:5, tiebreak:10}`, `promotion_verdict` | PASS |
| 6 | Diagnostic metrics added | `run_rep` logs task, tool_calls, retries, recovery, tool_errors, provider, cost | PASS |
| 7 | Failures preserved, never retried away | every rep JSON kept in `bench-ext/artifacts/2026-09-15/delivery/` | PASS |
| 8 | Mandatory provenance rejected by a test | `tests/test_task_provenance.py` (missing field / missing object / fabricated id) | PASS |
| 9 | Session ids derived from AgentSessions DB (read-only) | `task_intake.session_exists` / `find_sessions`; `test_fabricated_session_id_rejected` | PASS |
| 10 | Intake/validation command + docs | `bench-ext/task_intake.py`, `bench-ext/docs/task-intake.md` | PASS |
| 11 | Task set empty pending #88 | registry has only `todomvc` + the one delivery task | PASS |
| 12 | CI guardrails unchanged and green | `py -m unittest discover -s bench-ext/tests -t bench-ext`; synthetic-fixture guard still clean | PASS |
| 13 | Delivery: top-2 harnesses on a real auth-free task | `summary.json`, `report.md`, 10 rep JSONs + 10 screenshots | PASS |

## Commands (reproducible)

```
python3 -m unittest discover -s bench-ext/tests -t bench-ext     # 21 tests
python3 bench-ext/task_intake.py --validate bench-ext/delivery    # 1 valid, 0 quarantined
OPENROUTER_API_KEY=$(security find-generic-password -s codex-openrouter -w) \
  BENCH_RES=bench-ext/artifacts/2026-09-15/delivery \
  python3 bench-ext/runners/BrowserSkill.py 1 2 3 4 5 --task=chanel-gb-tag-check
OPENROUTER_API_KEY=$(...) BENCH_RES=bench-ext/artifacts/2026-09-15/delivery \
  python3 bench-ext/runners/browser-relay.py 1 2 --task=chanel-gb-tag-check
```

## Result at a glance

- browser-relay: 4/5 (screening 1/2 → promoted to 5 → **4/5**; 2-rep screening understated it).
- BrowserSkill: 3/5 (screening 2/2 → promoted to 5 → **3/5**; 2-rep screening overstated it).
- 10 rep JSONs + 10 screenshots; all failures preserved. Promotion corrected screening in both directions.
