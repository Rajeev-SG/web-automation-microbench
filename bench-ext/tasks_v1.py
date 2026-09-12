"""Task-suite v1 specs + deterministic verifiers (web-automation-microbench #2/#3).

Each TASK_* dict is the single source of truth consumed by runners; each has an
objective JS verifier evaluated in the page, a reset procedure, capability tags
and the shared-contract failure taxonomy. Unknown stays unknown: verifiers
return explicit false, never None-as-success.
"""
from pathlib import Path
import re, json

SPA = (Path(__file__).parent / 'fixtures' / 'spa-suite').resolve().as_uri()

# ---------- verifiers ----------
V_DELAYED = "JSON.stringify({ready:!!window.__ready,cards:Array.from(document.querySelectorAll('.card')).map(c=>({t:c.innerText,ok:c.dataset.ok==='true'})).length})"
def check_delayed(v):
    try: v=json.loads(v) if isinstance(v,str) else v
    except Exception: return False
    return v.get('ready') is True and v.get('cards')==5

V_GRID = "JSON.stringify({submitted:window.__submitted||null,boxes:Array.from(document.querySelectorAll('#f input')).map(b=>({row:b.dataset.row,checked:b.checked}))})"
def check_grid(v):
    try: v=json.loads(v) if isinstance(v,str) else v
    except Exception: return False
    if not isinstance(v,dict): return False
    target={'approve-alpha','approve-gamma','approve-epsilon','approve-zeta','approve-theta'}
    checked={b['row'] for b in v.get('boxes',[]) if b.get('checked')}
    return v.get('submitted')==','.join(sorted(target)) and checked==target

V_UPLOAD = "JSON.stringify({st:document.querySelector('#st').textContent,files:!!(document.querySelector('#inp').files&&document.querySelector('#inp').files.length)})"
def check_upload(v):
    try: v=json.loads(v) if isinstance(v,str) else v
    except Exception: return False
    return isinstance(v,dict) and str(v.get('st','')).startswith('RECEIVED:feedback.csv')

V_MODAL = "JSON.stringify({placed:!!window.__placed,terms:document.querySelector('#t1').checked,addr:document.querySelector('#t2').checked,modalHidden:getComputedStyle(document.querySelector('#m')).display==='none'})"
def check_modal(v):
    try: v=json.loads(v) if isinstance(v,str) else v
    except Exception: return False
    return bool(v.get('placed') and v.get('terms') and v.get('addr') and v.get('modalHidden'))

V_SCROLL = "JSON.stringify({n:document.querySelectorAll('#list .item').length,ids:Array.from(document.querySelectorAll('#list .item')).slice(-3).map(e=>e.dataset.id)})"
def check_scroll(v):
    try: v=json.loads(v) if isinstance(v,str) else v
    except Exception: return False
    return isinstance(v,dict) and v.get('n',0)>=15 and str(v.get('ids',[''])[-1]).startswith('item-')

TASKS = {
    # 1. latency microbenchmark (existing TodoMVC, unchanged contract)
    "todomvc": {
        "level": "deterministic", "capabilities": ["dom", "state"],
        "url": "https://demo.playwright.dev/todomvc/",
        "objective": "Add exactly two todos: \"Email supplier\" then \"Review invoice\". Mark ONLY \"Email supplier\" complete. Click the Active filter. Verify only \"Review invoice\" is shown and 1 item left. Do not clear completed. Work efficiently with ONE logical UI action per response (adding a todo is one action); observe before next action. Finish only after observing the final state.",
    },
    # 2. delayed-load SPA dashboard
    "delayed-dashboard": {
        "level": "deterministic", "capabilities": ["dynamic-ui", "wait-strategy"],
        "url": f"{SPA}/delayed-dashboard.html",
        "objective": "Wait for the region dashboard to finish loading asynchronously, then report: how many region cards exist and whether 'us-west' shows 'healthy' or 'DEGRADED'. Finish only after observing the loaded cards.",
        "verify_js": V_DELAYED, "check": check_delayed,
        "post_steps": lambda handle_code: None,  # adapter reports via final observation
    },
    # 3. checkbox grid (dom volume)
    "checkbox-grid": {
        "level": "deterministic", "capabilities": ["dom-volume", "robustness"],
        "url": f"{SPA}/checkbox-grid.html",
        "objective": "Check every row whose name starts with 'approve' (leave 'reject' rows unchecked), then click Submit. Finish only after the form has been submitted.",
        "verify_js": V_GRID, "check": check_grid,
    },
    # 4. file upload
    "file-upload": {
        "level": "deterministic", "capabilities": ["files", "multi-step"],
        "url": f"{SPA}/upload.html",
        "objective": "Create a CSV file named exactly 'feedback.csv' locally, upload it via the file input, then click Upload and finish after observing the confirmation text.",
        "verify_js": V_UPLOAD, "check": check_upload,
    },
    # 5. modal interrupt / recovery
    "modal-interrupt": {
        "level": "stochastic", "capabilities": ["modals", "recovery"],
        "url": f"{SPA}/modal.html",
        "objective": "Complete checkout: accept terms, confirm address, then Place order. A privacy modal may appear at any moment — dismiss it and continue. Finish only after observing the order placed.",
        "verify_js": V_MODAL, "check": check_modal,
    },
    # 6. infinite scroll
    "infinite-scroll": {
        "level": "stochastic", "capabilities": ["dynamic-ui", "long-horizon"],
        "url": f"{SPA}/scroll-feed.html",
        "objective": "Load at least 15 feed items by scrolling, then report the id of the last visible item. Finish only after observing 15+ items.",
        "verify_js": V_SCROLL, "check": check_scroll,
    },
    # 7-9: real-site tasks — spec-level in v1 (see task-suite-v1.md)
    "wiki-extract-act": {
        "level": "real-site", "capabilities": ["planning", "state-transfer"],
        "url": "https://en.wikipedia.org/wiki/Main_Page",
        "objective": "Find the 'On this day' entry for a shipwreck, note its year, then open that year's page and report one event that happened in that year other than the shipwreck.",
    },
    "canvas-vision": {
        "level": "real-site", "capabilities": ["vision"],
        "url": "https://developer.mozilla.org/en-US/docs/Web/API/Canvas_API/Tutorial/Basic_shapes",
        "objective": "Count how many distinct filled shapes appear in the first live canvas example on this page and report the count.",
    },
    "multi-tab-compare": {
        "level": "real-site", "capabilities": ["multi-tab", "vision"],
        "url": "https://developer.mozilla.org/",
        "objective": "Open the Python 3 and Python 2 'datetime' documentation pages in two tabs, then report which one documents the 'timestamp()' method.",
    },
}

# Shared failure taxonomy — imported conceptually from the shared contract;
# kept as literals here so the repo stays independently usable.
FAILURE_CLASSES = ["task-state", "harness-tool", "adapter-protocol", "model-format", "integration-setup", "site-environment"]

def classify_failure(run: dict) -> str | None:
    """Objective failure class for a suite run (same rules as the exporter)."""
    if run.get("pass"):
        return None
    err = str(run.get("error") or "")
    if not run.get("done"):
        if "timed out" in err or run.get("total_s", 0) >= 200:
            return "harness-tool"
        return "adapter-protocol"
    if run.get("done") and not run.get("pass"):
        return "task-state"
    if any((e.get("answer") == "UNPARSEABLE") for e in run.get("events", [])):
        return "model-format"
    return None
