"""Every contender that uses the shared loop accepts `--task=<id>` (issue #20/#24).

Guards the runner CLI plumbing and pins the honest boundary: the five self-driving runtimes
that ship their own agent loop are listed as NOT task-aware, so nobody cites them for another
task by accident.
"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import benchlib  # noqa: E402

RUNNERS = pathlib.Path(__file__).resolve().parents[1] / "runners"
# Self-driving runtimes with their own agent loop (no benchlib.run_rep call).
OWN_LOOP_RUNNERS = {"browser-agent-tb", "midscene", "notte", "page-agent", "skyvern"}
NON_CONTENDERS = {"make_round6_summary", "hyperagent_reps34"}


class RunnerTaskFlag(unittest.TestCase):
    def test_cli_parsing(self):
        self.assertEqual(benchlib.cli_reps_and_task([]), (["1", "2"], None))
        self.assertEqual(benchlib.cli_reps_and_task(["3", "4"]), (["3", "4"], None))
        self.assertEqual(benchlib.cli_reps_and_task(["--task=chanel-gb-tag-check"]),
                         (["1", "2"], "chanel-gb-tag-check"))
        reps, task = benchlib.cli_reps_and_task(["1", "--task=ue", "2"])
        self.assertEqual((reps, task), (["1", "2"], "ue"))

    def test_run_cli_default_reads_sys_argv(self):
        # Regression: run_cli must read sys.argv when argv is omitted (needs `import sys`).
        import sys as _sys
        saved = _sys.argv
        _sys.argv = ["runner.py", "5"]
        seen = []
        orig = benchlib.run_rep
        benchlib.run_rep = lambda a, r, task=None, max_steps=10, timeout=180: seen.append((r, task))
        try:
            class F:
                def __call__(self):  # zero-arg factory
                    return object()
            benchlib.run_cli(F)
        finally:
            benchlib.run_rep = orig
            _sys.argv = saved
        self.assertEqual(seen, [("5", None)])

    def test_run_cli_threads_task_into_run_rep(self):
        seen = {}

        class Fake:
            name = "fake"
            doc = "d"
            def start(self): return {}, "obs"
            def act(self, h, c): return "obs", 0.0
            def verify(self, h): return "{}"
            def screenshot(self, h, p): pass
            def teardown(self, h): pass

        calls = []

        def fake_run_rep(adapter, rep, task=None, max_steps=10, timeout=180):
            calls.append({"rep": rep, "task": task, "max_steps": max_steps})
            return {"rep": rep}

        orig = benchlib.run_rep
        benchlib.run_rep = fake_run_rep
        try:
            benchlib.run_cli(Fake, ["1", "--task=probe-task"], max_steps=17)
            benchlib.run_cli(Fake, ["1", "2", "3"])
        finally:
            benchlib.run_rep = orig
        self.assertEqual([c["task"] for c in calls], ["probe-task", None, None, None])
        self.assertEqual([c["rep"] for c in calls], ["1", "1", "2", "3"])
        self.assertEqual(calls[0]["max_steps"], 17)

    def test_every_shared_loop_runner_is_task_aware(self):
        offenders = []
        for p in RUNNERS.glob("*.py"):
            if p.stem in NON_CONTENDERS or p.stem in OWN_LOOP_RUNNERS:
                continue
            text = p.read_text()
            if "run_cli(" not in text and "cli_reps_and_task(" not in text:
                offenders.append(p.stem)
        self.assertEqual(offenders, [], f"runners missing --task support: {offenders}")

    def test_own_loop_runners_are_exactly_the_known_five(self):
        found = set()
        for p in RUNNERS.glob("*.py"):
            if p.stem in NON_CONTENDERS:
                continue
            text = p.read_text()
            if "run_cli(" not in text and "cli_reps_and_task(" not in text and "run_rep(" not in text:
                found.add(p.stem)
        self.assertEqual(found, OWN_LOOP_RUNNERS,
                         f"own-loop runner set drifted: {found ^ OWN_LOOP_RUNNERS}")

    def test_no_runner_snapshots_task_globals_at_import(self):
        """Guards the import-time-freeze bug: a module-level read of a task global bakes
        TodoMVC into every rep, so --task silently drives the wrong page."""
        import ast as _ast
        banned = []
        for p in RUNNERS.glob("*.py"):
            if p.stem in NON_CONTENDERS:
                continue
            src = p.read_text()
            tree = _ast.parse(src)
            for node in tree.body:  # module level only
                if isinstance(node, (_ast.Assign, _ast.AnnAssign)):
                    seg = _ast.get_source_segment(src, node) or ""
                    if any(f"benchlib.{g}" in seg for g in ("TASK", "URL_TASK", "OBS_JS", "VERIFY_JS")):
                        banned.append(f"{p.name}:{node.lineno}")
        self.assertEqual(banned, [],
                         f"runners snapshotting task globals at import (freeze bug): {banned}")

    def test_raw_playwright_repl_is_lazy(self):
        """Raw-playwright must build its REPL JS at call time, honouring the bound task."""
        import importlib.util
        p = RUNNERS / "raw-playwright.py"
        spec = importlib.util.spec_from_file_location("rp_lazy", str(p))
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        saved = benchlib.URL_TASK
        try:
            benchlib.URL_TASK = "https://example.test/other-task"
            js = m.build_repl_js()
            self.assertIn("https://example.test/other-task", js)
            self.assertNotIn("demo.playwright.dev/todomvc", js)
        finally:
            benchlib.URL_TASK = saved


if __name__ == "__main__":
    unittest.main()
