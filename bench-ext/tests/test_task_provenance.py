"""The REAL-WORK provenance rule must be enforced by the validator, not by review.

Every non-TodoMVC task without any of source_session_id / source_url / verified_against
is rejected, and session ids are checked against the AgentSessions DB (read-only).
Hermetic: the tests build a throwaway session DB, so they run in CI with no AgentSessions
install (a missing DB reports "not a real session", never raises).
"""
import os
import pathlib
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import task_intake  # noqa: E402

# A real session id derived from the AgentSessions DB (derive, never copy — REAL-WORK-MANDATE.md).
REAL_SESSION = "a308af6a96316e9f148c7ce6d4153c10f1fe3b25cfb873de00c754f26051967f"
FABRICATED = "0" * 64


def _make_session_db(ids, path):
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE session_meta (session_id TEXT PRIMARY KEY, source TEXT, start_ts INTEGER, title TEXT)")
    for i in ids:
        con.execute("INSERT INTO session_meta (session_id, source, title) VALUES (?, 'test', 't')", (i,))
    con.commit()
    con.close()
    return path


def _spec(**overrides):
    spec = {
        "schema": task_intake.TASK_SCHEMA,
        "task_id": "example-real-task",
        "task_class": "web-automation",
        "evidence_type": "controlled",
        "objective": "do the real thing",
        "url": "https://example.com/",
        "verification": {"verify_js": "JSON.stringify({ok:true})"},
        "provenance": {
            "source_session_id": REAL_SESSION,
            "source_url": "https://example.com/console",
            "verified_against": "objective end state",
        },
    }
    spec.update(overrides)
    return spec


class ProvenanceRejection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db = _make_session_db([REAL_SESSION], os.path.join(cls.tmp.name, "index.db"))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def validate(self, spec):
        return task_intake.validate_task_spec(spec, db=self.db)

    def test_complete_spec_is_valid(self):
        self.assertEqual(self.validate(_spec()), [])

    def test_missing_source_session_id_rejected(self):
        s = _spec(); del s["provenance"]["source_session_id"]
        self.assertTrue(any("source_session_id" in e for e in self.validate(s)))

    def test_missing_source_url_rejected(self):
        s = _spec(); del s["provenance"]["source_url"]
        self.assertTrue(any("source_url" in e for e in self.validate(s)))

    def test_missing_verified_against_rejected(self):
        s = _spec(); del s["provenance"]["verified_against"]
        self.assertTrue(any("verified_against" in e for e in self.validate(s)))

    def test_missing_provenance_object_rejected(self):
        s = _spec(); del s["provenance"]
        self.assertTrue(any("provenance" in e for e in self.validate(s)))

    def test_fabricated_session_id_rejected(self):
        s = _spec(); s["provenance"]["source_session_id"] = FABRICATED
        self.assertTrue(any("not a real AgentSessions session" in e for e in self.validate(s)))

    def test_missing_db_is_hermetic_and_rejects(self):
        # CI has no AgentSessions DB: a spec with a session id is rejected, never raises.
        missing = os.path.join(self.tmp.name, "does-not-exist.db")
        errs = task_intake.validate_task_spec(_spec(), db=missing)
        self.assertTrue(any("not a real AgentSessions session" in e for e in errs))
        self.assertFalse(task_intake.session_exists(REAL_SESSION, db=missing))
        self.assertEqual(task_intake.find_sessions("chanel", db=missing), [])

    def test_todomvc_controlled_instrument_is_exempt(self):
        s = _spec(task_id="todomvc", provenance={"source": "controlled-instrument"})
        self.assertEqual(self.validate(s), [])

    def test_bad_schema_and_class_rejected(self):
        self.assertTrue(any("schema" in e for e in self.validate(_spec(schema="nope"))))
        self.assertTrue(any("task_class" in e for e in self.validate(_spec(task_class="nope"))))


if __name__ == "__main__":
    unittest.main()
