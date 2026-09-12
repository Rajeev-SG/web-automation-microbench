# Task intake (issue #20 step 3)

Consumer side of the cross-repo **pareto-research** loop. Real benchmark tasks are
harvested in `Rajeev-SG/codex-session-orchestration-analysis` (issue #88) and offered
to this repo as **conformant task specs**; `bench-ext/task_intake.py` validates them and
the `benchlib` task registry can run them.

This repo does **not** mine, invent, or hand-author tasks. The harvested **corpus** stays
empty pending #88 output — `bench-ext/tasks_v1.py` tasks 2–9 remain invalid records. The only
task present is the one issue #20 delivery demonstration (`chanel-gb-tag-check`), kept as
worked evidence, not as corpus.

## The registry

`bench-ext/benchlib.py` holds a task registry. A task is:

```python
Task(id, instruction, url, observe_js, verify_js, check,
     capabilities=[...], provenance={...}, reset=None)
```

`run_rep(adapter, rep, task=..., max_steps=..., timeout=...)` runs one rep of a chosen
task; `get_task(id)` resolves it (`None` ⇒ the default `todomvc`). The historical module
globals (`TASK`, `URL_TASK`, `OBS_JS`, `VERIFY_JS`) are still bound to the default task so
the 29 existing runners work unchanged; `run_rep` rebinds them to the selected task.

TodoMVC is the **latency microbenchmark** only (controlled instrument), never capability
evidence. Its instruction/verify text is frozen by `bench-ext/tests/golden/todomvc.json`
and the `test_todomvc_golden.py` regression test.

## Mandatory provenance (rejected by a test, not by review)

Every **non-TodoMVC** task must carry all three provenance fields, or the validator
rejects it:

| field | meaning |
|---|---|
| `source_session_id` | the AgentSessions session the task was performed in |
| `source_url` | the real site/console(s) the work was done on |
| `verified_against` | the objective end state that proves success |

The rule is enforced by `task_intake.validate_task_spec`, covered by
`bench-ext/tests/test_task_provenance.py`. A missing field, a missing provenance object,
or a **fabricated** session id (one that is not a real AgentSessions session) all fail.

## Derive session ids — never copy them

Session ids are read from the AgentSessions database **read-only**, never copied out of
`REAL-WORK-MANDATE.md` (which says so explicitly):

```bash
python3 bench-ext/task_intake.py --sessions chanel        # list real matching sessions
python3 bench-ext/task_intake.py --session-exists <ID>    # exit 0 iff ID is real
python3 bench-ext/task_intake.py --validate <dir>         # validate every spec in a dir
```

## Conformant spec shape

A spec reuses the **published** `pareto-research-task/v1` envelope field names
(`schema`, `task_id`, `task_class`, `evidence_type`, `objective`) from
`codex-session-orchestration-analysis/tools/pareto_research.py`, plus the browser-domain
execution fields this repo needs:

```json
{
  "schema": "pareto-research-task/v1",
  "task_id": "<stable id>",
  "task_class": "web-automation",
  "evidence_type": "controlled",
  "objective": "<objective end state>",
  "url": "https://<real site>/<path>",
  "instruction": "<verbatim instruction handed to the model>",
  "capabilities": ["<capability tag>"],
  "verification": {"verify_js": "<independent verification JS>", "description": "<...>"},
  "provenance": {
    "source_session_id": "<AgentSessions session id>",
    "source_url": "https://<real site>/<path>",
    "verified_against": "<objective end state>"
  }
}
```

## Outstanding cross-repo dependency

`codex-session-orchestration-analysis#88` ("Harvest replayable benchmark tasks
conservatively from real work") is **OPEN**. The shared **run-envelope** contract
(`pareto-research-task/v1`) is published (landed in #93), but #88's canonical
**harvested-corpus task schema** is not yet published, and the harvester CLI is not built.
This repo therefore validates only against the published envelope field names plus its own
browser-domain execution fields — it does **not** define a parallel task schema.

Until #88 lands, `benchmarks/corpus/` (the consumer's task set) stays empty. When #88
publishes, its harvested task definitions must carry, per REAL-WORK-MANDATE.md, at minimum:
`source_session_id`, `source_url`, `verified_against`, a deterministic verifier, a
recoverable pre-state, and no unrecoverable secret dependency — those map directly onto the
spec shape above with no translation layer required.

## Worked example (delivery, issue #20)

`bench-ext/delivery/chanel-gb-tag-check.json` is a conformant spec (validated by
`task_intake.py`) for a real, auth-free task derived from the CHANEL tag-QA session; it is
registered by `bench-ext/tasks_real.py` and run with:

```bash
OPENROUTER_API_KEY=$(security find-generic-password -s codex-openrouter -w) \
  BENCH_RES=bench-ext/artifacts/2026-09-15/delivery \
  python3 bench-ext/runners/BrowserSkill.py 1 2 3 4 5 --task=chanel-gb-tag-check
```

Result: BrowserSkill 3/5 (2/2 screening → promoted to 5), browser-relay 1/2 — see
`bench-ext/artifacts/2026-09-15/delivery/report.md`. The agent records its finding in
`window.__bench_finding`; the verifier **independently recomputes** the tag ground truth from
the live page and compares, so a run passes only when the agent's finding matches objective
page state *and* the agent signalled done.
