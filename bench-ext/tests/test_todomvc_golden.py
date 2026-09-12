"""Golden-file regression: the issue #20 task-registry refactor did not change TodoMVC.

Guards the byte-identical instruction/verify text and the pass predicate against
accidental drift while the library becomes task-parameterized.
"""
import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import benchlib  # noqa: E402

GOLDEN = json.loads((pathlib.Path(__file__).parent / "golden" / "todomvc.json").read_text())


class TodoMvcGolden(unittest.TestCase):
    def test_task_strings_byte_identical(self):
        task = benchlib.get_task("todomvc")
        self.assertEqual(task.id, GOLDEN["task_id"])
        self.assertEqual(task.instruction, GOLDEN["instruction"])
        self.assertEqual(task.url, GOLDEN["url"])
        self.assertEqual(task.observe_js, GOLDEN["observe_js"])
        self.assertEqual(task.verify_js, GOLDEN["verify_js"])

    def test_module_globals_bound_to_todomvc(self):
        # Existing runners read these module globals directly; they must still resolve.
        self.assertEqual(benchlib.TASK, GOLDEN["instruction"])
        self.assertEqual(benchlib.URL_TASK, GOLDEN["url"])
        self.assertEqual(benchlib.OBS_JS, GOLDEN["observe_js"])
        self.assertEqual(benchlib.VERIFY_JS, GOLDEN["verify_js"])

    def test_default_task_is_todomvc(self):
        self.assertIs(benchlib.get_task(None), benchlib.get_task("todomvc"))

    def test_pass_predicate_vectors(self):
        for vec in GOLDEN["verify_vectors"]:
            with self.subTest(vec["name"]):
                self.assertEqual(bool(benchlib.check_pass(vec["input"])), vec["expect_pass"])

    def test_task_check_matches_check_pass(self):
        task = benchlib.get_task("todomvc")
        for vec in GOLDEN["verify_vectors"]:
            self.assertEqual(bool(task.check(vec["input"])), vec["expect_pass"])


if __name__ == "__main__":
    unittest.main()
