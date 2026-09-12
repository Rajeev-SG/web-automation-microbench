# Task intake and ingestion (issues #20, #27)

Consumer side of the cross-repo **pareto-research** loop. Real benchmark tasks are
harvested in `Rajeev-SG/codex-session-orchestration-analysis` (issue #88) as
`pareto-research-task-definition/v1` JSON; this repo validates them and registers each as
a runnable `benchlib.Task`.

This repo does **not** mine, invent, or hand-author tasks. The corpus is a **read-only
vendored snapshot** under `bench-ext/corpus/`:

```
bench-ext/corpus/SOURCE.json     producer repo + revision + per-file sha256 (the pin)
bench-ext/corpus/tasks/*.json    the producer's admitted web-automation tasks, verbatim
bench-ext/corpus/refresh.py      re-vendor / drift-check against the producer checkout
bench-ext/task_ingest.py         validate -> register as benchlib.Task (no per-task code)
bench-ext/corpus/screen.py       screen a harness across the corpus
bench-ext/corpus/report.py       aggregate screening results into a capability scoreboard
```

Only `task_class == "web-automation"` tasks are vendored: the coding/desktop/document
families the harvester also emits are not this benchmark's job. There is **no fixed suite
size** — the corpus is however many browser tasks the producer has admitted.

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

## What the consumer now validates (issue #27)

`task_intake.validate_task_spec` enforces the published `#88` definition contract, not just
the envelope field names. A spec must carry:

- the envelope fields (`schema`, `task_id`, `task_class`, `evidence_type`, `objective`);
- `definition_schema: pareto-research-task-definition/v1`;
- the agent-facing execution fields (`url`, `instruction`, `capabilities[]` non-empty);
- a deterministic verifier (`verification.verify_js` or `test_command`) **and** a
  declarative `verification.pass_rule` whose kind the consumer can evaluate, plus
  `verification.authority` and `verification.description`;
- a recoverable `pre_state.kind` (`fresh-page-load` | `public-page-load` | `repo-checkout`);
- the admission gates: no `secret_dependency`, no `blocked_reason`, and — for a
  `derived-variant` — a `derivation` naming real `derived_from` sessions plus `varied` and
  `rationale`.

## Ingestion: harvester JSON -> registry -> run (no per-task Python)

```bash
python3 bench-ext/task_ingest.py                    # validate + register (session-checked)
python3 bench-ext/task_ingest.py --no-session-check # offline/CI validation only
python3 bench-ext/task_ingest.py --json             # full report
```

`task_ingest` builds each `benchlib.Task` from the spec: the instruction, start `url`,
observation JS (the spec's own, or a generic snapshot when it declares none) and the
`verification.verify_js`, with the spec's declarative `pass_rule` compiled by
`bench-ext/pass_rule.py`. Nothing is per-task in this repo.

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
  "instruction": "<verbatim instruction handed to the model>",
  "definition_schema": "pareto-research-task-definition/v1",
  "pre_state": {"kind": "fresh-page-load", "detail": "<...>"},
  "verification": {
    "verify_js": "<independent verification JS — recomputes ground truth from the live page>",
    "description": "<...>",
    "authority": "page-recomputed",
    "pass_rule": {"kind": "finding_matches_truth", "fields": ["..."], "require_any_of": ["..."]}
  },
  "provenance": {
    "source_session_id": "<AgentSessions session id>",
    "source_url": "https://<real site>/<path>",
    "verified_against": "<objective end state>"
  }
}
```

The consumer evaluates `verification.pass_rule` with `bench-ext/pass_rule.py` — a port of the
producer's `tools/task_pass_rule.py` (`finding_matches_truth`, `structural`; `test-runner` is
left to a runner). `tests/test_pass_rule.py` covers the semantics, including `url_fields`
normalisation and `require_any_of` failing a degenerate measurement closed.

## Cross-repo dependency (consumed)

`codex-session-orchestration-analysis#88` ("Harvest replayable benchmark tasks
conservatively from real work") is **CLOSED**, and the browser families it emitted
(`broader browser corpus` — PRs #105 and #107) are the corpus this repo consumes. Both
schemas are published:

| Schema | Where | What it is |
|---|---|---|
| `pareto-research-task/v1` | the run envelope | the envelope field names this validator checks |
| `pareto-research-task-definition/v1` | harvested task definitions | the canonical corpus task schema (also checked) |

The corpus lives at `codex-session-orchestration-analysis/benchmarks/corpus/tasks/`. This
repo does **not** define a parallel task schema; it validates the published contract and
vendors the browser subset read-only.

Re-vendor or drift-check against the producer checkout:

```bash
python3 bench-ext/corpus/refresh.py --from /Users/rajeev/Code/codex-session-orchestration-analysis
python3 bench-ext/corpus/refresh.py --from <checkout> --check   # exits 1 on drift
```

`refresh.py` copies only `task_class == "web-automation"` tasks and records the producer
revision plus a per-file sha256 in `bench-ext/corpus/SOURCE.json`, so the snapshot cannot
drift silently. It also drops a vendored file the producer has since removed.

## Worked example (delivery, issue #20)

`bench-ext/delivery/chanel-gb-tag-check.json` is a conformant spec (validated by
`task_intake.py`) for a real, auth-free task derived from the CHANEL tag-QA session; it is
registered by `task_ingest.py` alongside the corpus, and run with:

```bash
OPENROUTER_API_KEY=$(security find-generic-password -s codex-openrouter -w) \
  BENCH_RES=bench-ext/artifacts/2026-09-12-delivery/delivery \
  python3 bench-ext/runners/BrowserSkill.py 1 2 3 4 5 --task=chanel-gb-tag-check
```

Result: both harnesses screened 2 reps then were promoted to 5 — browser-relay 4/5,
BrowserSkill 3/5; the promotion corrected screening in both directions. See
`bench-ext/artifacts/2026-09-12-delivery/delivery/report.md`. The agent records its finding in
`window.__bench_finding`; the verifier **independently recomputes** the tag ground truth from
the live page and compares, so a run passes only when the agent's finding matches objective
page state *and* the agent signalled done.
