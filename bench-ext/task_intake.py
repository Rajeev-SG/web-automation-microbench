#!/usr/bin/env python3
"""Task intake — ingest a conformant task spec into the benchlib task registry.

Consumer side of the cross-repo pareto-research contract
(`Rajeev-SG/codex-session-orchestration-analysis`, `pareto-research-task/v1`, issue #88).

Two rules this module enforces, both covered by tests in `bench-ext/tests/`:

1. REAL-WORK PROVENANCE (mandatory, not review-only). Every non-TodoMVC task must
   carry `provenance` with all of `source_session_id`, `source_url`, `verified_against`.
   A task missing any of the three is rejected here, by the validator — not by a reviewer.
   See `docs/REAL-WORK-MANDATE.md`.
2. Session ids are DERIVED from the AgentSessions database (read-only), never copied
   out of `REAL-WORK-MANDATE.md`. `session_exists()` checks the id is a real AgentSessions
   session; `find_sessions()` lists candidates by keyword.

Schema note (do not invent a parallel schema): the canonical harvested-corpus *task*
schema belongs to codex-session-orchestration-analysis#88 and is not published yet. This
consumer therefore validates against the *published* `pareto-research-task/v1` envelope
field names (schema, task_id, task_class, evidence_type, objective) plus the browser-domain
execution fields this repo needs (url, instruction, verification), and leaves the registry
task set EMPTY pending #88 output. See `docs/task-intake.md` for the exact dependency.
"""
from __future__ import annotations
import argparse, json, sqlite3, sys
from pathlib import Path

# Mirrors Rajeev-SG/codex-session-orchestration-analysis tools/pareto_research.py.
TASK_SCHEMA = "pareto-research-task/v1"
TASK_CLASSES = [
    "small-coding-fix", "feature-implementation", "long-context-coding", "repo-devops",
    "web-automation", "desktop-automation", "document", "research",
]
EVIDENCE_TYPES = ("observed", "controlled")

# The three mandatory provenance fields for any real-work task (issue #20 + REAL-WORK-MANDATE.md).
REQUIRED_PROVENANCE = ("source_session_id", "source_url", "verified_against")
# The one non-real-work task, and the only one exempt from session provenance.
CONTROLLED_INSTRUMENT_TASK_CLASSES = ()  # TodoMVC is identified by task_id, below.
TODO_MVC_TASK_ID = "todomvc"

AGENT_SESSIONS_DB = Path.home() / "Library" / "Application Support" / "AgentSessions" / "index.db"


def _connect(db=AGENT_SESSIONS_DB):
    return sqlite3.connect(f"file:{db}?mode=ro", uri=True)


def session_exists(session_id, db=AGENT_SESSIONS_DB):
    """True iff the id is a real AgentSessions session (read-only)."""
    if not session_id:
        return False
    with _connect(db) as con:
        row = con.execute("SELECT 1 FROM session_meta WHERE session_id = ? LIMIT 1", (session_id,)).fetchone()
    return row is not None


def find_sessions(keyword, db=AGENT_SESSIONS_DB, limit=20):
    """List real AgentSessions sessions whose title matches a keyword (read-only)."""
    like = f"%{keyword}%"
    with _connect(db) as con:
        rows = con.execute(
            "SELECT session_id, source, start_ts, COALESCE(custom_title, title, '') "
            "FROM session_meta WHERE lower(COALESCE(title,'') || ' ' || COALESCE(custom_title,'')) LIKE lower(?) "
            "ORDER BY start_ts DESC LIMIT ?", (like, limit)).fetchall()
    return [{"session_id": r[0], "source": r[1], "start_ts": r[2], "title": r[3]} for r in rows]


def is_controlled_instrument(spec):
    """TodoMVC is the one controlled instrument; only it is exempt from session provenance."""
    return spec.get("task_id") == TODO_MVC_TASK_ID or spec.get("provenance", {}).get("source") == "controlled-instrument"


def validate_task_spec(spec, check_session=True, db=AGENT_SESSIONS_DB):
    """Return a list of validation errors; empty list means the spec may be ingested."""
    errors = []
    if not isinstance(spec, dict):
        return ["task spec must be an object"]
    if spec.get("schema") != TASK_SCHEMA:
        errors.append(f"schema must be {TASK_SCHEMA}")
    for field in ("task_id", "task_class", "evidence_type", "objective"):
        if spec.get(field) in (None, ""):
            errors.append(f"missing required field: {field}")
    if spec.get("task_class") not in TASK_CLASSES:
        errors.append(f"task_class must be one of {TASK_CLASSES}")
    if spec.get("evidence_type") not in EVIDENCE_TYPES:
        errors.append("evidence_type must be observed|controlled")

    # Mandatory provenance for every non-TodoMVC task. Reject, don't warn.
    if not is_controlled_instrument(spec):
        prov = spec.get("provenance")
        if not isinstance(prov, dict):
            errors.append("missing required provenance object (non-TodoMVC task)")
        else:
            for field in REQUIRED_PROVENANCE:
                if not prov.get(field):
                    errors.append(f"missing required provenance.{field} (non-TodoMVC task)")
            sid = prov.get("source_session_id")
            if sid and check_session and not session_exists(sid, db=db):
                errors.append(f"provenance.source_session_id {sid!r} is not a real AgentSessions session")

    # Browser-domain execution fields needed to actually run the task.
    for field in ("url", "verification"):
        if spec.get(field) in (None, ""):
            errors.append(f"missing required field: {field}")
    return errors


def load_specs(directory):
    """Load every *.json task spec under a directory (skips excluded-run notes)."""
    out = []
    for path in sorted(Path(directory).glob("*.json")):
        try:
            data = json.loads(path.read_text())
        except Exception as e:
            out.append((path, None, [f"unreadable JSON: {e}"]))
            continue
        out.append((path, data, validate_task_spec(data) if isinstance(data, dict) else ["not an object"]))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Validate / ingest benchmark task specs (issue #20).")
    ap.add_argument("--validate", metavar="DIR", help="validate every task spec in DIR (does not run anything)")
    ap.add_argument("--sessions", metavar="KEYWORD", help="list real AgentSessions sessions matching KEYWORD (read-only)")
    ap.add_argument("--session-exists", metavar="SESSION_ID", help="exit 0 iff SESSION_ID is a real AgentSessions session")
    args = ap.parse_args(argv)

    if args.sessions is not None:
        for row in find_sessions(args.sessions):
            print(json.dumps(row, sort_keys=True))
        return 0
    if args.session_exists is not None:
        ok = session_exists(args.session_exists)
        print(json.dumps({"session_id": args.session_exists, "exists": ok}))
        return 0 if ok else 1
    if args.validate is not None:
        specs = load_specs(args.validate)
        valid = sum(1 for _, _, errs in specs if not errs)
        for path, _, errs in specs:
            if errs:
                print(f"REJECT {path}: " + "; ".join(errs))
        print(json.dumps({"schema": TASK_SCHEMA, "specs": len(specs), "valid": valid,
                          "quarantined": len(specs) - valid}))
        return 0 if valid == len(specs) else 1
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
