"""The REAL-WORK provenance rule must be enforced by the validator, not by review.

Every non-TodoMVC task without any of source_session_id / source_url / verified_against
is rejected; session ids are checked against the AgentSessions DB (read-only).
"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import task_intake  # noqa: E402

# A real session id derived from the AgentSessions DB (see REAL-WORK-MANDATE.md: derive, never copy).
REAL_SESSION = "a308af6a96316e9f148c7ce6d4153c10f1fe3b25cfb873de00c754f26051967f"


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
    def test_complete_spec_is_valid(self):
        self.assertEqual(task_intake.validate_task_spec(_spec()), [])

    def test_missing_source_session_id_rejected(self):
        s = _spec()
        del s["provenance"]["source_session_id"]
        errs = task_intake.validate_task_spec(s)
        self.assertTrue(any("source_session_id" in e for e in errs), errs)

    def test_missing_source_url_rejected(self):
        s = _spec()
        del s["provenance"]["source_url"]
        errs = task_intake.validate_task_spec(s)
        self.assertTrue(any("source_url" in e for e in errs), errs)

    def test_missing_verified_against_rejected(self):
        s = _spec()
        del s["provenance"]["verified_against"]
        errs = task_intake.validate_task_spec(s)
        self.assertTrue(any("verified_against" in e for e in errs), errs)

    def test_missing_provenance_object_rejected(self):
        s = _spec()
        del s["provenance"]
        errs = task_intake.validate_task_spec(s)
        self.assertTrue(any("provenance" in e for e in errs), errs)

    def test_fabricated_session_id_rejected(self):
        s = _spec()
        s["provenance"]["source_session_id"] = "0" * 64
        errs = task_intake.validate_task_spec(s)
        self.assertTrue(any("not a real AgentSessions session" in e for e in errs), errs)

    def test_todomvc_controlled_instrument_is_exempt(self):
        s = _spec(task_id="todomvc", provenance={"source": "controlled-instrument"})
        self.assertEqual(task_intake.validate_task_spec(s), [])

    def test_bad_schema_and_class_rejected(self):
        self.assertTrue(any("schema" in e for e in task_intake.validate_task_spec(_spec(schema="nope"))))
        self.assertTrue(any("task_class" in e for e in task_intake.validate_task_spec(_spec(task_class="nope"))))


if __name__ == "__main__":
    unittest.main()
