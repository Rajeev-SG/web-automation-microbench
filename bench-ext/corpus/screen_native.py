#!/usr/bin/env python3
"""Screen an OWN-LOOP harness across the harvested corpus (issue #34).

`corpus/screen.py` drives harnesses that expose a benchlib adapter (start/act/verify). Some
contenders ship their own agent runtime instead (notte, skyvern, midscene, and Browser Use Pi):
reducing them to one primitive action per model call would erase the architecture under test.
This driver runs such a harness natively — one whole agent run per task — and writes the same
run JSON the scoreboard reads, so `corpus/report.py` aggregates it unchanged.

    python3 bench-ext/corpus/screen_native.py --harness browser-use-pi --reps 1 --all
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import pathlib
import sys
import time

BASE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
import benchlib  # noqa: E402


def load_runner(harness: str):
    path = BASE / "runners" / f"{harness}.py"
    if not path.is_file():
        raise SystemExit(f"no runner for harness {harness!r} ({path})")
    spec = importlib.util.spec_from_file_location(f"native_{harness.replace('-', '_')}", str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    if not hasattr(mod, "run_native"):
        raise SystemExit(f"{path} exposes no run_native(rep, task=...) — not an own-loop runner")
    return mod


def main(argv=None):
    ap = argparse.ArgumentParser(description="Screen an own-loop harness across the harvested corpus.")
    ap.add_argument("--harness", required=True)
    ap.add_argument("--reps", default="1", help="comma-separated rep labels, e.g. 1,2")
    ap.add_argument("--tasks")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--out", help="output dir (default bench-ext/artifacts/<today>/corpus/<harness>)")
    args = ap.parse_args(argv)

    benchlib.get_task(None)  # force lazy ingest
    if args.all or not args.tasks:
        ids = sorted(json.loads(p.read_text())["task_id"] for p in (BASE / "corpus" / "tasks").glob("*.json"))
    else:
        ids = [t.strip() for t in args.tasks.split(",") if t.strip()]

    out = pathlib.Path(args.out) if args.out else benchlib.artifacts_dir("corpus") / args.harness
    out.mkdir(parents=True, exist_ok=True)
    reps = [r.strip() for r in str(args.reps).split(",") if r.strip()]
    mod = load_runner(args.harness)

    rows = []
    old_res = benchlib.RES
    try:
        for tid in ids:
            task_res = out / tid
            task_res.mkdir(parents=True, exist_ok=True)
            benchlib.RES = task_res
            for rep in reps:
                t0 = time.perf_counter()
                log = mod.run_native(rep, task=tid, name=args.harness)
                rows.append({"task": tid, "rep": rep, "pass": bool(log.get("pass")),
                             "done": log.get("done"), "total_s": log.get("total_s"),
                             "model_calls": log.get("model_calls"), "tool_calls": log.get("tool_calls"),
                             "tokens": log.get("tokens"), "cost_usd": log.get("cost"),
                             "error": log.get("error"), "wall_s": round(time.perf_counter() - t0, 2),
                             "artifact": str(task_res / f"{rep}-{args.harness}.json")})
    finally:
        benchlib.RES = old_res

    summary = {"harness": args.harness, "reps": reps, "tasks": ids, "runs": rows,
               "passes": sum(1 for r in rows if r["pass"]), "total": len(rows)}
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps({k: summary[k] for k in ("harness", "passes", "total")}))
    return rows


if __name__ == "__main__":
    main()
