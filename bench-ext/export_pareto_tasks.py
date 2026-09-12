#!/usr/bin/env python3
"""Browser-domain adapter: export microbench run JSONs as pareto-research task envelopes.

Reference consumer for Rajeev-SG/codex-session-orchestration-analysis#84.
The shared contract is enforced over there (`pareto-research harvest`); this script
only adds browser-domain evidence. Unknown stays unknown — fields are omitted,
never zero-filled.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

TASK_SCHEMA = "pareto-research-task/v1"
TASK_CLASS = "web-automation"

# Objective failure classification from web-automation-microbench#3.
def classify_failure(run: dict) -> str | None:
    if run.get("pass") is True:
        return None
    err = str(run.get("error") or "")
    if not run.get("done"):
        if "timed out" in err or run.get("total_s", 0) >= 200:
            return "harness-tool"      # control mechanism never signalled completion
        return "adapter-protocol"      # wrapper prevented the finish protocol
    if run.get("done") and not run.get("pass"):
        return "task-state"            # agent finished but wrong final state
    return "model-format" if run.get("events") and any(
        e.get("answer") == "UNPARSEABLE" for e in run["events"]) else None


def envelope_for(run: dict, source: str) -> dict:
    tokens = run.get("tokens") or {}
    events = run.get("events") or []
    costs = [(e.get("usage") or {}).get("cost") for e in events]
    known_cost = [c for c in costs if isinstance(c, (int, float))]
    routes = sorted({e.get("provider") for e in events if e.get("provider")})
    passed = run.get("pass") is True
    env = {
        "schema": TASK_SCHEMA,
        "task_id": f"web-automation-microbench/2026-09-12/{run.get('id', Path(source).stem)}",
        "task_class": TASK_CLASS,
        "evidence_type": "observed",
        "objective": "TodoMVC: add two todos, complete one, filter Active (latency microbenchmark; see bench-ext/docs/task-suite-v1.md)",
        "configuration": {
            "harness": run.get("contender"),
            "model": "z-ai/glm-5.3-flash",
            "provider": "openrouter",
        },
        "outcome": {"success": passed},
        "outcome_evidence": {
            "verifier": "benchlib.check_pass(dom-state)",
            "passed": passed,
            "done_protocol": run.get("done"),
            "source_run": source,
        },
    }
    if run.get("total_s") is not None:
        env["elapsed_seconds"] = run["total_s"]
    if tokens.get("input") is not None:
        env["input_tokens"] = tokens["input"]
    if tokens.get("output") is not None:
        env["output_tokens"] = tokens["output"]
    if tokens.get("cached") is not None:
        env["cache_read_tokens"] = tokens["cached"]
    if tokens.get("input") is not None and tokens.get("output") is not None:
        env["total_tokens"] = tokens["input"] + tokens["output"]
    if known_cost:
        env["metered_cost_usd"] = round(sum(known_cost), 8)
    fc = classify_failure(run)
    if fc:
        env["failure_class"] = fc
    if routes:
        env["provider_route"] = routes[0] if len(routes) == 1 else routes
    env["model_calls"] = len(events)
    return env


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    results = Path(args.results_dir)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    n = 0
    for path in sorted(results.glob("*.json")):
        try:
            run = json.loads(path.read_text())
        except Exception:
            continue
        if not isinstance(run, dict) or "contender" not in run:
            continue  # exclusion notes are evidence, not runs
        env = envelope_for(run, f"web-automation-microbench/{path.relative_to(results.parent)}")
        (out / f"{path.stem}.json").write_text(json.dumps(env, indent=2, sort_keys=True) + "\n")
        n += 1
    print(f"exported {n} envelopes to {out}")

if __name__ == "__main__":
    main()
