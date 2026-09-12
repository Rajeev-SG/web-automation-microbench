#!/usr/bin/env python3
"""Vendor the browser-domain harvested corpus from the producer checkout (issue #27).

The benchmark this repo runs is a *browser* benchmark: it consumes the
`task_class == "web-automation"` tasks emitted by
`Rajeev-SG/codex-session-orchestration-analysis` (issue #88, the
`pareto-research-task-definition/v1` contract). This script is a **read-only
copy** — it never edits, re-words or invents a task. If the producer checkout
does not match the pinned revision, the copy is refused.

    python3 bench-ext/corpus/refresh.py --from /path/to/codex-session-orchestration-analysis

It writes one JSON per task under `corpus/tasks/` (verbatim bytes), plus
`corpus/SOURCE.json` recording the producer repo, revision, per-file sha256 and
the vendored date, so the corpus is auditable and reproducible. A task the
producer has not admitted (a quarantined candidate) is never copied.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
import sys
from datetime import date

HERE = pathlib.Path(__file__).resolve().parent
TASKS_DIR = HERE / "tasks"
SOURCE = HERE / "SOURCE.json"
TASK_CLASS = "web-automation"
DEFAULT_REPO = "Rajeev-SG/codex-session-orchestration-analysis"


def _sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _revision(repo: pathlib.Path) -> dict:
    def git(*args):
        return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True).stdout.strip()
    remote = git("config", "--get", "remote.origin.url")
    return {
        "repo": remote.split("github.com/")[-1].removesuffix(".git") if "github.com/" in remote else remote,
        "revision": git("rev-parse", "HEAD"),
        "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
        "dirty": bool(git("status", "--porcelain")),
        "subject": git("log", "-1", "--format=%s"),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Vendor the harvested browser corpus (read-only copy).")
    ap.add_argument("--from", dest="source_root", required=True, help="path to the codex-session-orchestration-analysis checkout")
    ap.add_argument("--check", action="store_true", help="verify the vendored files still match the source; write nothing")
    args = ap.parse_args(argv)

    repo = pathlib.Path(args.source_root).resolve()
    src_dir = repo / "benchmarks" / "corpus" / "tasks"
    if not src_dir.is_dir():
        print(f"not a producer checkout (no {src_dir})", file=sys.stderr)
        return 2

    meta = _revision(repo)
    files = {}
    for path in sorted(src_dir.glob("*.json")):
        spec = json.loads(path.read_text())
        if spec.get("task_class") != TASK_CLASS:
            continue  # browser benchmark consumes browser tasks only
        files[path.name] = {"sha256": _sha256(path), "task_id": spec.get("task_id")}

    if args.check:
        drift = []
        for name, info in files.items():
            vendored = TASKS_DIR / name
            if not vendored.exists() or _sha256(vendored) != info["sha256"]:
                drift.append(name)
        extra = sorted(p.name for p in TASKS_DIR.glob("*.json") if p.name not in files)
        if drift or extra:
            print(json.dumps({"drift": drift, "not_in_source": extra}))
            return 1
        print(json.dumps({"ok": True, "files": len(files), "revision": meta["revision"]}))
        return 0

    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    for name, info in files.items():
        (TASKS_DIR / name).write_bytes((src_dir / name).read_bytes())
    for stale in TASKS_DIR.glob("*.json"):
        if stale.name not in files:
            stale.unlink()

    SOURCE.write_text(json.dumps({
        "producer": meta,
        "vendored_date": date.today().isoformat(),
        "task_class": TASK_CLASS,
        "definition_schema": "pareto-research-task-definition/v1",
        "note": ("Read-only vendored snapshot of the producer's admitted browser tasks. "
                 "Refresh with corpus/refresh.py --from <checkout>; ingest with task_ingest.py."),
        "files": files,
    }, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"vendored": len(files), "revision": meta["revision"], "dirty_source": meta["dirty"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
