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
schema is published by codex-session-orchestration-analysis#88 as
`pareto-research-task-definition/v1`. This consumer validates the `pareto-research-task/v1`
envelope field names (schema, task_id, task_class, evidence_type, objective) **and** the
definition contract the harvester emits: `definition_schema`, the agent-facing execution
fields (`url`, `instruction`, `capabilities`), the declarative `verification.pass_rule`
(so the consumer needs no per-task code), the recoverable `pre_state`, and the admission
gates (`secret_dependency`, `blocked_reason`, `derivation`) — so a spec this validator
accepts can be registered as a `benchlib.Task` and run. See `docs/task-intake.md`.
"""
from __future__ import annotations
import argparse, json, os, sqlite3, sys
from pathlib import Path

# Mirrors Rajeev-SG/codex-session-orchestration-analysis tools/pareto_research.py.
TASK_SCHEMA = "pareto-research-task/v1"
# The published definition schema (codex-session-orchestration-analysis#88). A spec this
# validator accepts must declare it, so the consumer ingests the harvester's own contract.
DEFINITION_SCHEMA = "pareto-research-task-definition/v1"
TASK_CLASSES = [
    "small-coding-fix", "feature-implementation", "long-context-coding", "repo-devops",
    "web-automation", "desktop-automation", "document", "research",
]
EVIDENCE_TYPES = ("observed", "controlled")
# Pass-rule kinds the declarative interpreter (bench-ext/pass_rule.py) can evaluate.
PASS_RULE_KINDS = ("finding_matches_truth", "structural", "test-runner")
# Recoverable pre-states the harvester admits (issue #88 gate 4).
PRE_STATES = ("fresh-page-load", "public-page-load", "repo-checkout")
DERIVATION_FIDELITIES = ("literal-replay", "derived-variant")

# The three mandatory provenance fields for any real-work task (issue #20 + REAL-WORK-MANDATE.md).
REQUIRED_PROVENANCE = ("source_session_id", "source_url", "verified_against")
# The one non-real-work task, and the only one exempt from session provenance.
CONTROLLED_INSTRUMENT_TASK_CLASSES = ()  # TodoMVC is identified by task_id, below.
TODO_MVC_TASK_ID = "todomvc"

# Overridable so CI/tests can point at a throwaway DB (missing DB => "not a real session").
AGENT_SESSIONS_DB = Path(os.environ.get("AGENT_SESSIONS_DB",
    Path.home() / "Library" / "Application Support" / "AgentSessions" / "index.db"))


def _connect(db=AGENT_SESSIONS_DB):
    return sqlite3.connect(f"file:{db}?mode=ro", uri=True)


def session_exists(session_id, db=AGENT_SESSIONS_DB):
    """True iff the id is a real AgentSessions session (read-only).

    CI runners have no AgentSessions DB; a missing/unreadable DB is reported as
    "not a real session" (never raised), so callers stay hermetic and a spec with no
    verifiable session is rejected rather than crashing the validator.
    """
    if not session_id:
        return False
    if not Path(db).exists():
        return False
    try:
        with _connect(db) as con:
            row = con.execute("SELECT 1 FROM session_meta WHERE session_id = ? LIMIT 1", (session_id,)).fetchone()
        return row is not None
    except sqlite3.Error:
        return False


def find_sessions(keyword, db=AGENT_SESSIONS_DB, limit=20):
    """List real AgentSessions sessions whose title matches a keyword (read-only)."""
    if not Path(db).exists():
        return []
    like = f"%{keyword}%"
    try:
        with _connect(db) as con:
            rows = con.execute(
                "SELECT session_id, source, start_ts, COALESCE(custom_title, title, '') "
                "FROM session_meta WHERE lower(COALESCE(title,'') || ' ' || COALESCE(custom_title,'')) LIKE lower(?) "
                "ORDER BY start_ts DESC LIMIT ?", (like, limit)).fetchall()
    except sqlite3.Error:
        return []
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
    for field in ("url", "instruction", "verification"):
        if spec.get(field) in (None, ""):
            errors.append(f"missing required field: {field}")

    # --- published #88 definition contract (issue #27) -------------------------------------
    if spec.get("definition_schema") != DEFINITION_SCHEMA:
        errors.append(f"definition_schema must be {DEFINITION_SCHEMA}")

    caps = spec.get("capabilities")
    if not isinstance(caps, list) or not caps:
        errors.append("capabilities must be a non-empty list (capability metadata is required)")

    verification = spec.get("verification")
    if isinstance(verification, dict):
        for field in ("description", "authority"):
            if not verification.get(field):
                errors.append(f"missing required verification.{field}")
        if not verification.get("verify_js") and not verification.get("test_command"):
            errors.append("verification needs a deterministic verifier (verify_js or test_command)")
        rule = verification.get("pass_rule")
        if not isinstance(rule, dict) or rule.get("kind") not in PASS_RULE_KINDS:
            errors.append(f"verification.pass_rule.kind must be one of {PASS_RULE_KINDS}")
    elif verification is not None:
        errors.append("verification must be an object")

    pre = spec.get("pre_state")
    if not isinstance(pre, dict) or pre.get("kind") not in PRE_STATES:
        errors.append(f"pre_state.kind must be one of {PRE_STATES}")

    # Admission gates carried on the spec (issue #88 gates 5 and the derivation gate).
    if spec.get("secret_dependency"):
        errors.append("secret_dependency is set: an unrecoverable secret cannot be admitted")
    if spec.get("blocked_reason"):
        errors.append(f"blocked_reason is set: {spec['blocked_reason']}")

    derivation = spec.get("derivation")
    if derivation is not None:
        if not isinstance(derivation, dict):
            errors.append("derivation must be an object when present")
        else:
            if derivation.get("fidelity") not in DERIVATION_FIDELITIES:
                errors.append(f"derivation.fidelity must be one of {DERIVATION_FIDELITIES}")
            derived_from = derivation.get("derived_from") or []
            if not derived_from:
                errors.append("derivation.derived_from must name at least one real session")
            else:
                for sid in derived_from:
                    if check_session and not session_exists(sid, db=db):
                        errors.append(f"derivation.derived_from {sid!r} is not a real AgentSessions session")
            if derivation.get("fidelity") == "derived-variant" and not (derivation.get("varied") and derivation.get("rationale")):
                errors.append("a derived-variant must declare `varied` and `rationale`")
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
