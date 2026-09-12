#!/usr/bin/env python3
"""Screen a representative harness set across the harvested corpus (issue #27).

Cheap first stage: one disposable adapter, N reps per task, every result written to
`bench-ext/artifacts/<run date>/corpus/<harness>/`. Nothing here is a per-task shim —
the driver imports the harness adapter that already exists in `bench-ext/runners/`
and lets `benchlib.run_rep` bind the harvested task.

    python3 bench-ext/corpus/screen.py --harness raw-playwright --reps 1,2 --all
    python3 bench-ext/corpus/screen.py --harness browser-relay  --reps 1 \
        --tasks porsche-uk-tag-inspection,puma-uk-tag-inspection

The summary records the outcome and the raw per-rep JSON paths, so a reader can always
go back to the evidence. A failure is reported, never retried away.
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
import task_ingest  # noqa: E402


def load_adapter(harness: str):
    path = BASE / "runners" / f"{harness}.py"
    if not path.is_file():
        raise SystemExit(f"no adapter for harness {harness!r} ({path})")
    spec = importlib.util.spec_from_file_location(f"screen_{harness.replace('-', '_')}", str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def find_adapter_class(mod, override=None):
    """Locate the runner's adapter class.

    Adapter classes are not consistently named (`Adapter`, `BrowserRelay`, `AgentBrowser`, ...),
    so discover the class that carries the interface `benchlib.run_rep` requires rather than
    hard-coding a name. `--adapter-class` overrides the search.
    """
    if override:
        cls = getattr(mod, override, None)
        if cls is None:
            raise SystemExit(f"{mod.__name__} has no class {override!r}")
        return cls
    candidates = []
    for attr in vars(mod).values():
        if isinstance(attr, type) and attr.__module__ == mod.__name__ \
                and all(hasattr(attr, m) for m in ("start", "act", "verify", "name")):
            candidates.append(attr)
    if not candidates:
        raise SystemExit(f"{mod.__name__} exposes no adapter class (start/act/verify/name)")
    named = [c for c in candidates if c.__name__ == "Adapter"]
    return named[0] if named else candidates[0]


def corpus_task_ids():
    return sorted(t for t in benchlib.TASKS if t != benchlib.DEFAULT_TASK_ID)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Screen a harness across the harvested corpus.")
    ap.add_argument("--harness", required=True, help="adapter name under bench-ext/runners/")
    ap.add_argument("--reps", default="1", help="comma-separated rep labels, e.g. 1,2")
    ap.add_argument("--tasks", help="comma-separated task ids (default: all harvested tasks)")
    ap.add_argument("--all", action="store_true", help="screen every registered harvested task")
    ap.add_argument("--out", help="output dir (default bench-ext/artifacts/<today>/corpus/<harness>)")
    ap.add_argument("--max-steps", type=int, default=None)
    ap.add_argument("--timeout", type=int, default=None)
    ap.add_argument("--adapter-class", default=None, help="override the adapter class name")
    args = ap.parse_args(argv)

    benchlib.get_task(None)  # ensure lazy ingestion has run
    if args.all or not args.tasks:
        # chanel-gb-tag-check is the #20 worked example, not corpus; keep the screen to the corpus
        import task_intake
        ids = sorted(json.loads(p.read_text())["task_id"] for p in (BASE / "corpus" / "tasks").glob("*.json"))
    else:
        ids = [t.strip() for t in args.tasks.split(",") if t.strip()]

    out = pathlib.Path(args.out) if args.out else benchlib.artifacts_dir("corpus") / args.harness
    out.mkdir(parents=True, exist_ok=True)
    reps = [r.strip() for r in str(args.reps).split(",") if r.strip()]

    mod = load_adapter(args.harness)
    factory = find_adapter_class(mod, args.adapter_class)

    rows = []
    old_res = benchlib.RES
    try:
        for tid in ids:
            # One directory per task: run_rep names its files `{rep}-{harness}.json`, so a
            # shared directory would let one task's rep overwrite another task's.
            task_res = out / tid
            task_res.mkdir(parents=True, exist_ok=True)
            benchlib.RES = task_res
            for rep in reps:
                t0 = time.perf_counter()
                log = benchlib.run_rep(factory(), rep, task=tid,
                                       max_steps=args.max_steps, timeout=args.timeout)
                rows.append({
                    "task": tid, "rep": rep, "pass": bool(log.get("pass")),
                    "done": log.get("done"), "total_s": log.get("total_s"),
                    "model_calls": log.get("model_calls"), "tool_calls": log.get("tool_calls"),
                    "tokens": log.get("tokens"), "cost_usd": log.get("cost"),
                    "error": log.get("error"), "wall_s": round(time.perf_counter() - t0, 2),
                    "artifact": str(task_res / f"{rep}-{args.harness}.json"),
                })
    finally:
        benchlib.RES = old_res

    by_task = {}
    for r in rows:
        by_task.setdefault(r["task"], []).append(r)
    summary = {
        "harness": args.harness,
        "run_date": benchlib.run_date(),
        "reps": reps,
        "model": benchlib.openrouter_payload([])["model"],
        "tasks": ids,
        "results": rows,
        "by_task": {t: {"passes": sum(1 for r in rs if r["pass"]), "reps": len(rs)} for t, rs in by_task.items()},
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    for t, agg in summary["by_task"].items():
        print(f"{args.harness:16s} {t:38s} {agg['passes']}/{agg['reps']}")
    print(json.dumps({"harness": args.harness, "tasks": len(ids), "reps": len(reps),
                      "total_passes": sum(r["pass"] for r in rows), "runs": len(rows), "out": str(out)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
