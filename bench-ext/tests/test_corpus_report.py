"""The scoreboard is recomputed from stored evidence, not trusted from the run files (#27).

This matters because a later pass-rule fix (the fail-closed degenerate-measurement guard) has
to apply to evidence that was already collected. These tests are hermetic — they build a
throwaway results tree, so no network and no live corpus are required.
"""
import json
import pathlib
import sys
import tempfile
import unittest

BASE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
import benchlib  # noqa: E402
import pass_rule  # noqa: E402
from corpus import report  # noqa: E402


def _run(harness, task, rep, verification, done=True, stored_pass=False):
    return {
        "id": f"{rep}-{harness}", "contender": harness, "task": task, "rep": rep, "done": done,
        "pass": stored_pass, "verification": verification,
        "events": [{"step": 1, "provider": "Makora"}],
    }


class Rescore(unittest.TestCase):
    RULE = {"kind": "finding_matches_truth", "fields": ["gtm"], "require_any_of": ["gtm"]}

    def test_a_stored_false_pass_is_corrected_by_the_rule(self):
        run = _run("h", "t", "1", json.dumps({"truth": {"gtm": []}, "finding": {"gtm": []}}),
                   stored_pass=True)
        self.assertFalse(report.rescore(run, self.RULE))

    def test_a_genuine_pass_survives_rescoring(self):
        run = _run("h", "t", "1", json.dumps({"truth": {"gtm": ["GTM-A"]}, "finding": {"gtm": ["GTM-A"]}}))
        self.assertTrue(report.rescore(run, self.RULE))

    def test_unfinished_or_unparseable_runs_do_not_pass(self):
        self.assertFalse(report.rescore(_run("h", "t", "1", "{}", done=False), self.RULE))
        self.assertFalse(report.rescore(_run("h", "t", "1", "not json"), self.RULE))
        self.assertFalse(report.rescore(_run("h", "t", "1", "verify error: boom"), self.RULE))


class Scoreboard(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = pathlib.Path(self.tmp.name)
        # harness-a: two passing reps; harness-b: one failure that was mis-stored as a pass
        for rep in ("1", "2"):
            self._write(root, "harness-a", "task-x", rep,
                        json.dumps({"truth": {"gtm": ["GTM-A"]}, "finding": {"gtm": ["GTM-A"]}}),
                        stored_pass=True)
        self._write(root, "harness-b", "task-x", "1",
                    json.dumps({"truth": {"gtm": []}, "finding": {"gtm": []}}), stored_pass=True)
        self.root = root

    @staticmethod
    def _write(root, harness, task, rep, verification, stored_pass):
        d = root / harness / task
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{rep}-{harness}.json").write_text(
            json.dumps(_run(harness, task, rep, verification, stored_pass=stored_pass)))

    def tearDown(self):
        self.tmp.cleanup()

    def test_build_recomputes_and_records_the_divergence(self):
        old = report.load_rules
        report.load_rules = lambda: {"task-x": Rescore.RULE}
        try:
            agg = report.build(self.root)
        finally:
            report.load_rules = old
        self.assertEqual(agg["table"]["harness-a"]["task-x"]["passes"], 2)
        self.assertEqual(agg["table"]["harness-b"]["task-x"]["passes"], 0)
        self.assertEqual(len(agg["stored_vs_recomputed_divergences"]), 1)
        self.assertEqual(agg["total_runs"], 3)

    def test_markdown_renders_every_harness_and_task(self):
        self.assertIn("| Harness |", report.to_markdown({
            "tasks": ["task-x"], "harnesses": ["harness-a"],
            "table": {"harness-a": {"task-x": {"passes": 2, "reps": 2}}},
            "promotion": {"harness-a": {"stage": "promote"}}}))

    def test_report_skips_summary_files(self):
        (self.root / "harness-a" / "task-x" / "summary.json").write_text(json.dumps({"harness": "x"}))
        old = report.load_rules
        report.load_rules = lambda: {"task-x": Rescore.RULE}
        try:
            runs = report.load_runs(self.root, {"task-x": Rescore.RULE})
        finally:
            report.load_rules = old
        self.assertEqual(sum(len(v) for v in runs.values()), 3)


if __name__ == "__main__":
    unittest.main()
