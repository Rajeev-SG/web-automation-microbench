#!/usr/bin/env python3
"""Task ingestion — validate harvested task JSON and register it as a `benchlib.Task` (issue #27).

Consumer side of the cross-repo contract defined by
`Rajeev-SG/codex-session-orchestration-analysis#88` (`pareto-research-task-definition/v1`).

    harvester JSON  ->  task_intake.validate_task_spec  ->  register as benchlib.Task  ->  run

There is **no per-task Python**: the pass predicate is the spec's own declarative
`verification.pass_rule`, evaluated by `bench-ext/pass_rule.py`, and the observation,
start URL and instruction come from the spec. Nothing in this module invents a task;
the corpus is a read-only vendored snapshot (`bench-ext/corpus/`, refresh with
`corpus/refresh.py`).

A spec that fails validation is **rejected with its reasons** and never registered.
If the AgentSessions database is absent (e.g. CI), session-backed specs are rejected
by the same rule that rejects a fabricated id — the validator stays hermetic and the
TodoMVC microbenchmark keeps working.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import benchlib  # noqa: E402
import pass_rule  # noqa: E402
import task_intake  # noqa: E402

BASE = pathlib.Path(__file__).resolve().parent
#: Where an ingested task definition is allowed to live. `corpus/tasks` is the vendored
#: harvester output; `delivery` holds the issue #20 worked example in the same contract.
CORPUS_DIRS = (BASE / "corpus" / "tasks", BASE / "delivery")

#: Per-task execution budget for harvested real-work tasks (the TodoMVC microbenchmark keeps
#: benchlib's own 10-step default). Real tasks navigate, consent, search and act.
HARVESTED_MAX_STEPS = 14
HARVESTED_TIMEOUT = 300


def load_specs(dirs=None, check_session=True, db=None):
    """Load + validate every JSON task spec under `dirs`.

    Returns a list of ``(path, spec|None, errors)``; `errors` empty means the spec is valid
    and may be registered. Nothing is filtered out silently — rejected specs stay visible.
    """
    out = []
    for directory in (dirs or CORPUS_DIRS):
        directory = pathlib.Path(directory)
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.json")):
            try:
                spec = json.loads(path.read_text())
            except Exception as e:  # unreadable JSON is a rejection, not a crash
                out.append((path, None, [f"unreadable JSON: {e}"]))
                continue
            if not isinstance(spec, dict):
                out.append((path, spec, ["task spec must be an object"]))
                continue
            errs = task_intake.validate_task_spec(spec, check_session=check_session, db=db) if db \
                else task_intake.validate_task_spec(spec, check_session=check_session)
            out.append((path, spec, errs))
    return out


def build_task(spec):
    """Turn a validated spec into a runnable `benchlib.Task` (no per-task code)."""
    verification = spec["verification"]
    rule = verification["pass_rule"]
    if rule.get("kind") == "test-runner":
        raise ValueError("test-runner tasks are not browser-executable in this consumer")
    return benchlib.Task(
        id=spec["task_id"],
        instruction=spec["instruction"],
        url=spec["url"],
        observe_js=spec.get("observation_js") or benchlib.GENERIC_OBS_JS,
        verify_js=verification["verify_js"],
        check=pass_rule.check_from_rule(rule),
        capabilities=spec.get("capabilities") or [],
        provenance=spec.get("provenance") or {},
        level="real-site",
        max_steps=HARVESTED_MAX_STEPS,
        timeout=HARVESTED_TIMEOUT,
    )


def register_spec(spec):
    """Register one validated spec in the benchlib registry and return the Task."""
    task = build_task(spec)
    benchlib.register(task)
    return task


def ingest(dirs=None, check_session=True, db=None):
    """Validate then register every valid spec. Returns a report (never raises on a bad spec)."""
    report = {"registered": [], "rejected": {}, "dirs": [str(d) for d in (dirs or CORPUS_DIRS)]}
    for path, spec, errs in load_specs(dirs, check_session=check_session, db=db):
        if errs:
            report["rejected"][str(path)] = errs
            continue
        try:
            register_spec(spec)
            report["registered"].append(spec["task_id"])
        except Exception as e:  # a spec that validates but cannot be built is still reported
            report["rejected"][str(path)] = [f"registration failed: {type(e).__name__}: {e}"]
    report["registered"].sort()
    return report


# Register at import so `benchlib.get_task(<harvested id>)` resolves without extra plumbing.
_INGEST_REPORT = ingest()


def main(argv=None):
    ap = argparse.ArgumentParser(description="Validate / ingest harvested task specs (issue #27).")
    ap.add_argument("--dir", action="append", dest="dirs", help="directory of task specs (repeatable; default corpus + delivery)")
    ap.add_argument("--no-session-check", action="store_true", help="skip the AgentSessions existence check (offline validation only)")
    ap.add_argument("--json", action="store_true", help="print the full report as JSON")
    args = ap.parse_args(argv)

    report = ingest(args.dirs, check_session=not args.no_session_check)
    counts = {"specs": len(report["registered"]) + len(report["rejected"]),
              "valid": len(report["registered"]), "quarantined": len(report["rejected"])}
    if args.json:
        print(json.dumps({"counts": counts, **report}, indent=2, sort_keys=True))
    else:
        for path, errs in sorted(report["rejected"].items()):
            print(f"REJECT {path}: " + "; ".join(errs))
        print(json.dumps({"schema": task_intake.TASK_SCHEMA, **counts, "registered": report["registered"]}))
    return 0 if not report["rejected"] else 1


if __name__ == "__main__":
    sys.exit(main())
