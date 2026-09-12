"""The ingested corpus is harvested, validated, and runnable with no per-task code (issue #27).

Hermetic: these tests never require the AgentSessions database, so they run in CI. The
session-existence gate is exercised in tests/test_task_provenance.py against a throwaway DB.
"""
import copy
import hashlib
import json
import pathlib
import sys
import unittest

BASE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
import benchlib  # noqa: E402
import task_ingest  # noqa: E402
import task_intake  # noqa: E402

TASKS_DIR = BASE / "corpus" / "tasks"
SOURCE_PIN = BASE / "corpus" / "SOURCE.json"


def _specs():
    return [(p, json.loads(p.read_text())) for p in sorted(TASKS_DIR.glob("*.json"))]


class CorpusSourcePin(unittest.TestCase):
    def test_source_pin_records_every_vendored_file(self):
        pin = json.loads(SOURCE_PIN.read_text())
        self.assertEqual(pin["task_class"], "web-automation")
        self.assertEqual(pin["definition_schema"], task_intake.DEFINITION_SCHEMA)
        self.assertIn("revision", pin["producer"])
        self.assertEqual(set(pin["files"]), {p.name for p in TASKS_DIR.glob("*.json")})

    def test_vendored_bytes_match_the_pinned_hashes(self):
        pin = json.loads(SOURCE_PIN.read_text())
        for name, info in pin["files"].items():
            got = hashlib.sha256((TASKS_DIR / name).read_bytes()).hexdigest()
            self.assertEqual(got, info["sha256"], f"{name} drifted from the pinned producer revision")


class CorpusContract(unittest.TestCase):
    def test_every_vendored_spec_satisfies_the_definition_contract(self):
        for path, spec in _specs():
            errs = task_intake.validate_task_spec(spec, check_session=False)
            self.assertEqual(errs, [], f"{path.name} rejected: {errs}")

    def test_corpus_is_browser_only_and_non_empty(self):
        # No fixed size: the suite grows with whatever the producer emits. The one hard
        # rule is that every task is a browser task — coding/desktop/document tasks are not
        # this benchmark's job and are never vendored.
        specs = [s for _, s in _specs()]
        self.assertGreaterEqual(len(specs), 5)
        self.assertTrue(all(s["task_class"] == "web-automation" for s in specs),
                        "a non-web-automation task reached the vendored corpus")

    def test_corpus_covers_materially_different_capabilities(self):
        caps = {c for _, s in _specs() for c in s["capabilities"]}
        # the browser capability families the harvester families define
        for family in ("tag-inspection", "dom-script-audit", "seo-audit", "crawlability",
                       "consent-handling", "structural-verification"):
            self.assertIn(family, caps, f"capability {family!r} missing from the corpus")
        self.assertGreaterEqual(len(caps), 10)

    def test_every_spec_declares_a_handled_pass_rule(self):
        import pass_rule
        for _, spec in _specs():
            kind = spec["verification"]["pass_rule"]["kind"]
            self.assertIn(kind, pass_rule.RULE_KINDS, f"unhandled rule kind {kind}")
            self.assertNotEqual(kind, "test-runner", "a test-runner task is not browser-executable")

    def test_every_spec_carries_real_work_provenance(self):
        for _, spec in _specs():
            prov = spec["provenance"]
            for field in task_intake.REQUIRED_PROVENANCE:
                self.assertTrue(prov.get(field), f"{spec['task_id']} lacks provenance.{field}")

    def test_derived_variants_declare_their_seed(self):
        for _, spec in _specs():
            deriv = spec.get("derivation")
            if not deriv:
                continue
            self.assertEqual(deriv["fidelity"], "derived-variant")
            self.assertTrue(deriv["derived_from"])
            self.assertTrue(deriv.get("varied"), f"{spec['task_id']} variant did not declare `varied`")
            self.assertTrue(deriv.get("rationale"), f"{spec['task_id']} variant did not declare `rationale`")


class RegistrationWithoutPerTaskCode(unittest.TestCase):
    def test_build_task_from_a_spec_uses_the_declarative_rule(self):
        for _, spec in _specs():
            task = task_ingest.build_task(spec)
            self.assertEqual(task.id, spec["task_id"])
            self.assertEqual(task.url, spec["url"])
            self.assertEqual(task.instruction, spec["instruction"])
            self.assertEqual(task.verify_js, spec["verification"]["verify_js"])
            self.assertEqual(task.capabilities, spec["capabilities"])
            # a spec with no observation_js gets the generic observation, never a frozen one
            self.assertTrue(task.observe_js)
            self.assertEqual(task.max_steps, task_ingest.HARVESTED_MAX_STEPS)
            self.assertFalse(task.check({}))  # an unparseable result fails closed

    def test_ingest_report_accounts_for_every_file(self):
        report = task_ingest.ingest(check_session=False)
        self.assertEqual(len(report["registered"]) + len(report["rejected"]),
                         len(list(TASKS_DIR.glob("*.json"))) + len(list((BASE / "delivery").glob("*.json"))))
        self.assertEqual(report["rejected"], {})

    def test_todomvc_task_is_untouched_by_ingestion(self):
        self.assertIn("todomvc", benchlib.TASKS)
        self.assertEqual(benchlib.TASKS["todomvc"].level, "deterministic")
        self.assertIsNone(benchlib.TASKS["todomvc"].max_steps)


class RejectionGates(unittest.TestCase):
    def _first(self):
        return copy.deepcopy(_specs()[0][1])

    def test_missing_provenance_is_rejected(self):
        spec = self._first(); del spec["provenance"]["source_session_id"]
        self.assertTrue(task_intake.validate_task_spec(spec, check_session=False))

    def test_missing_capability_metadata_is_rejected(self):
        spec = self._first(); spec["capabilities"] = []
        self.assertTrue(any("capabilities" in e for e in task_intake.validate_task_spec(spec, check_session=False)))

    def test_missing_pass_rule_is_rejected(self):
        spec = self._first(); del spec["verification"]["pass_rule"]
        self.assertTrue(any("pass_rule" in e for e in task_intake.validate_task_spec(spec, check_session=False)))

    def test_blocked_spec_is_rejected(self):
        spec = self._first(); spec["blocked_reason"] = "site serves a bot wall"
        self.assertTrue(any("blocked_reason" in e for e in task_intake.validate_task_spec(spec, check_session=False)))

    def test_secret_dependency_is_rejected(self):
        spec = self._first(); spec["secret_dependency"] = "OPENROUTER_API_KEY"
        self.assertTrue(any("secret_dependency" in e for e in task_intake.validate_task_spec(spec, check_session=False)))

    def test_variant_without_rationale_is_rejected(self):
        spec = self._first()
        spec["derivation"] = {"fidelity": "derived-variant", "derived_from": ["x"], "varied": ["page"]}
        self.assertTrue(any("rationale" in e for e in task_intake.validate_task_spec(spec, check_session=False)))


if __name__ == "__main__":
    unittest.main()
