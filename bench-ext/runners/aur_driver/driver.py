#!/usr/bin/env python3
"""In-runtime driver for the adaptive-ui-runtime microbench adapter.

Run with the RUNTIME's own venv python. It is not a contender: the microbench
owns Chrome, the timing boundary, reset and independent verification. This driver

  1. attaches the runtime to the already-running Chrome over CDP by subclassing the
     runtime's own `IsolatedBrowserTransport` (the runtime ships no CDP transport -
     `isolated` launches its own browser; here we replace *only* the launcher), and
  2. runs ONE `Engine.execute` for the task, exactly as the CLI/MCP would, then
     prints a JSON result the adapter reads.

The success criteria (already built on the benchlib side from the task's own
`verify_js` + declarative `pass_rule`) are passed in verbatim, so the runtime
verifies itself with its own code path and the microbench then verifies
independently with its own.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from playwright.sync_api import sync_playwright
from adaptive_ui_runtime.transports.isolated import IsolatedBrowserTransport


class CdpAttachedTransport(IsolatedBrowserTransport):
    """The runtime's isolated transport attached to an external Chrome over CDP.

    Action/observe/reset semantics are inherited unchanged; only the browser is
    connected to the microbench's Chrome for Testing instead of being launched here.

    Attribution control (frontier review #1 F2). The dominant corpus failure class
    recorded for this contender is ``stale_target`` — the runtime resolves an ordinal
    node from one observation, acts without re-observing, and its stamp revalidation
    (``IsolatedBrowserTransport._sel`` -> ``_STAMP_JS``) fails closed after a navigating
    click. This is NOT caused by the CDP attach: re-running the same tasks through the
    runtime's OWN native ``IsolatedBrowserTransport`` (a real launched Chromium, no CDP
    subclass, none of this adapter's code) reproduces the same classes:

        allbirds-uk-add-to-cart-tag-check -> status=failed  failure_class=stale_target
        porsche-uk-tag-inspection         -> status=failed  failure_class=repeated_action_loop

    So the subclass changes only how the browser is obtained; the failure is the
    runtime's own binding logic, inherited unchanged. Full evidence in
    ``bench-ext/runners/ADAPTIVE_UI_RUNTIME.md``.
    """

    name = "cdp-attached"

    def __init__(self, cdp_url: str) -> None:
        self._pw = sync_playwright().start()
        self.browser = self._pw.chromium.connect_over_cdp(cdp_url)
        self.context = self.browser.contexts[0]
        page = next((p for p in self.context.pages if (p.url or "").startswith("http")), None)
        self.page = page or self.context.pages[0]
        self.commands = 0

    def reset(self, url: str) -> None:
        self.page.goto(url, wait_until="domcontentloaded")
        try:
            self.page.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
        except Exception:
            pass
        self.page.reload(wait_until="domcontentloaded")

    def close(self) -> None:
        # Detach only; the microbench owns Chrome and kills it.
        for fn in (self.browser.close, self._pw.stop):
            try:
                fn()
            except Exception:
                pass


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--request", required=True, help="path to the request JSON the adapter wrote")
    ap.add_argument("--cdp", required=True, help="CDP endpoint of the microbench's Chrome")
    args = ap.parse_args()

    from adaptive_ui_runtime.contracts import Budget, Plan, Subtask, SuccessCriterion, TaskRequest
    from adaptive_ui_runtime.durability import FileRunStore
    from adaptive_ui_runtime.engine import Engine

    spec = json.loads(open(args.request).read())
    criteria = [SuccessCriterion(**c) for c in spec["criteria"]]
    request = TaskRequest(
        goal=spec["goal"], success_criteria=criteria, start_url=spec.get("start_url"),
        constraints={"task_id": spec["task_id"], "task_class": spec.get("task_class", "")},
    )
    subtask = Subtask(
        id="mb", goal=request.goal, success_criteria=criteria,
        task_class=spec.get("task_class") or "live_site_audit",
        budget=Budget(max_actions=int(spec.get("max_actions", 14)),
                      max_wall_seconds=float(spec.get("max_wall_seconds", 300))),
    )
    plan = Plan(goal=request.goal, subtasks=[subtask],
                rationale=f"microbench task {spec['task_id']}")

    # One process, one run: no durable workflow to resume from.
    os.environ.setdefault("AUR_DURABILITY", "file")
    transport = CdpAttachedTransport(args.cdp)
    try:
        if request.start_url:
            transport.reset(request.start_url)
        engine = Engine(transport, store=FileRunStore())
        engine.manager.override_plan = plan
        result = engine.execute(request)
        out = {
            "run_id": result.run_id,
            "verified": bool(result.verified),
            "status": str(result.status),
            "failure_class": result.failure_class,
            "metrics": result.metrics,
            "events": [e.model_dump() for e in getattr(engine.tracer, "events", [])],
        }
    except Exception as exc:  # surfaced, never silently swallowed
        out = {"error": f"{type(exc).__name__}: {exc}", "verified": False,
               "failure_class": "infrastructure_error", "metrics": {}, "events": []}
    finally:
        transport.close()
    print("AURJSON" + json.dumps(out, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
