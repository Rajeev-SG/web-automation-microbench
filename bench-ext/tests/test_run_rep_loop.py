"""run_rep end-to-end, offline: task parameterization, JSON schema, and diagnostics.

The network call is monkeypatched, so this proves the loop (not the model):
- a chosen task is bound to the module globals the adapters read,
- the JSON keeps every historical field name AND gains the task id + diagnostics,
- the pass predicate comes from the task, not the agent's own "done".
"""
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import benchlib  # noqa: E402

PASS_STATE = {"url": "https://demo.playwright.dev/todomvc/#/active",
              "items": [{"text": "Review invoice", "completed": False}],
              "saved": [{"title": "Email supplier", "completed": True},
                        {"title": "Review invoice", "completed": False}]}


class FakeAdapter:
    name = "fake-harness"
    doc = "drive the browser"
    def __init__(self):
        self.acts = []
    def start(self):
        self.bound_url = benchlib.URL_TASK      # what an adapter actually reads
        return {"setup_s": 0.01}, "initial observation"
    def act(self, handle, code):
        self.acts.append(code)
        if code == "boom":
            raise RuntimeError("tool blew up")
        return ("observation for " + code, 0.02)
    def verify(self, handle):
        return json.dumps(PASS_STATE)
    def screenshot(self, handle, path):
        pass
    def teardown(self, handle):
        pass


def _fake_call_factory(script):
    it = iter(script)
    def _call(msgs):
        content = next(it)
        return {"usage": {"prompt_tokens": 1000, "completion_tokens": 100,
                          "prompt_tokens_details": {"cached_tokens": 500}},
                "choices": [{"message": {"content": content}}],
                "provider": "FakeProvider", "id": "req-1"}
    return _call


class RunRepLoop(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._orig_res, self._orig_call = benchlib.RES, benchlib.openrouter_call
        benchlib.RES = pathlib.Path(self._tmp.name)

    def tearDown(self):
        benchlib.RES, benchlib.openrouter_call = self._orig_res, self._orig_call
        self._tmp.cleanup()

    def test_loop_schema_task_binding_and_diagnostics(self):
        benchlib.openrouter_call = _fake_call_factory([
            json.dumps({"code": "click the thing"}),
            json.dumps({"done": True}),
        ])
        adapter = FakeAdapter()
        log = benchlib.run_rep(adapter, "1")

        # task id added; every historical field name still present
        for field in ("id", "contender", "rep", "task", "events", "setup_s", "total_s",
                      "model_calls", "tokens", "cost", "verification", "pass"):
            self.assertIn(field, log, field)
        self.assertEqual(log["task"], "todomvc")
        self.assertEqual(log["contender"], "fake-harness")
        self.assertTrue(log["pass"])
        # diagnostics
        self.assertEqual(log["model_calls"], 2)
        self.assertEqual(log["tool_calls"], 1)
        self.assertEqual(log["tool_errors"], 0)
        self.assertEqual(log["provider"], ["FakeProvider"])
        self.assertGreater(log["cost"], 0)
        self.assertEqual(sorted(log["tokens"]), ["cached", "input", "output", "reasoning"])
        # the adapter saw the task's URL through the module global
        self.assertEqual(adapter.bound_url, benchlib.get_task("todomvc").url)
        # JSON written to disk
        written = json.loads((benchlib.RES / "1-fake-harness.json").read_text())
        self.assertEqual(written["task"], "todomvc")

    def test_failed_tool_call_is_recorded_not_replaced(self):
        benchlib.openrouter_call = _fake_call_factory([
            json.dumps({"code": "boom"}),
            json.dumps({"code": "retry same"}),
            json.dumps({"done": True}),
        ])
        log = benchlib.run_rep(FakeAdapter(), "2")
        self.assertEqual(log["tool_errors"], 1)
        self.assertEqual(log["tool_calls"], 2)
        self.assertTrue(log["events"][0]["tool_error"])
        self.assertFalse(log["events"][1]["tool_error"])

    def test_non_todomvc_task_binds_its_own_url(self):
        benchlib.register(benchlib.Task(
            id="unit-probe", instruction="probe", url="https://example.org/probe",
            observe_js="1", verify_js="1", check=lambda v: True,
            capabilities=["probe"], provenance={"source": "controlled-instrument"}))
        benchlib.openrouter_call = _fake_call_factory([json.dumps({"done": True})])
        adapter = FakeAdapter()
        log = benchlib.run_rep(adapter, "1", task="unit-probe")
        self.assertEqual(log["task"], "unit-probe")
        self.assertEqual(adapter.bound_url, "https://example.org/probe")
        # globals revert to the default task after binding another task subsequently
        benchlib.get_task("todomvc").bind()
        self.assertEqual(benchlib.URL_TASK, benchlib.get_task("todomvc").url)


if __name__ == "__main__":
    unittest.main()
