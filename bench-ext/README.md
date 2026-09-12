# Web Automation Microbenchmarks — bench-ext

This directory holds the harness library, the runner adapters and the harvested task corpus
introduced in Round 3.

**The benchmark itself — results, both leaderboards, and the round-by-round write-ups — lives in
the repository README: [`../README.md`](../README.md).**

## What is in here

| Path | What it is |
|---|---|
| `benchlib.py` | shared library: task registry, model payload, `run_rep` loop, token/cost accounting, artifact paths |
| `runners/` | one adapter per contender, each driven by `benchlib.run_cli(Adapter)` |
| `tests/` | unit suite + the golden TodoMVC fixture + the README/scoreboard consistency guard |
| `pass_rule.py` | declarative pass-rule interpreter for harvested tasks |
| `task_intake.py` | validates a task spec against the published `#88` contract |
| `task_ingest.py` | validate → register as `benchlib.Task`, with no per-task code |
| `corpus/` | the vendored harvested browser corpus, its pin, and the screen/report tools |
| `delivery/` | the issue #20 worked-example task spec |
| `docs/` | task intake contract and the real-work mandate |
| `artifacts/` | Round 3 on: per-run JSON, screenshots, summaries and reports |

## Contracts

- TodoMVC round: [`../docs/benchmark-spec.md`](../docs/benchmark-spec.md)
- Task intake and the harvested corpus: [`docs/task-intake.md`](docs/task-intake.md)
- No invented tasks, ever: [`docs/REAL-WORK-MANDATE.md`](docs/REAL-WORK-MANDATE.md)

## Running

```bash
export OPENROUTER_API_KEY=$(security find-generic-password -s codex-openrouter -w)   # never committed
python3 bench-ext/runners/<harness>.py 1 2 --task=<task-id>       # one scored rep per number
python3 bench-ext/corpus/screen.py --harness <harness> --reps 1 --all
```

Full instructions, the shared runner contract and the round gotchas: [`RUNNER_NOTES.md`](RUNNER_NOTES.md).
Hand-off state: [`HANDOFF.md`](HANDOFF.md).
