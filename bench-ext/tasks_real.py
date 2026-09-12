#!/usr/bin/env python3
"""Real-work tasks (session-derived) for the task registry.

Nothing here is hand-authored benchmark content: each task is an auth-free, replayable
encoding of browser work Rajeev really did, carrying mandatory provenance
(`source_session_id`, `source_url`, `verified_against`) derived from the AgentSessions
database (read-only). See docs/REAL-WORK-MANDATE.md and docs/task-intake.md.

The delivery demonstration for issue #20 lives here; the broader harvested corpus stays
empty pending codex-session-orchestration-analysis#88.
"""
from __future__ import annotations
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import benchlib  # noqa: E402

# ---------------------------------------------------------------------------------------------
# chanel-gb-tag-check — CHANEL UK homepage marketing-tag inspection.
#
# Real-work origin: the CHANEL tag-QA rounds inspect which marketing tags (Google Tag
# Manager / Google Ads / Pinterest) a CHANEL page actually carries. This task is the
# auth-free, replayable encoding of that inspection on the public UK homepage.
# ---------------------------------------------------------------------------------------------
CHANEL_GB_URL = "https://www.chanel.com/gb/"

CHANEL_OBS_JS = (
    "JSON.stringify({url:location.href,title:document.title,"
    "scripts:[...document.querySelectorAll('script[src]')].map(s=>s.src).slice(0,25),"
    "dataLayer:(window.dataLayer||[]).length,"
    "globals:{pintrk:typeof window.pintrk,gtag:typeof window.gtag,fbq:typeof window.fbq}})"
)

# Independent verifier: recompute the objective tag ground truth from the live page and read
# the agent's answer. The pass predicate compares the two — never the agent's self-report alone.
CHANEL_VERIFY_JS = (
    "(()=>{const html=document.documentElement.innerHTML;"
    "const gtm=[...new Set(html.match(/GTM-[A-Z0-9]+/g)||[])].sort();"
    "const aw=[...new Set(html.match(/AW-[0-9]{6,}/g)||[])].sort();"
    "const pinterest=(typeof window.pintrk!=='undefined')||/ct\\.pinterest\\.com|pintrk/i.test(html);"
    "let f=null;try{f=window.__bench_finding||null;}catch(e){}"
    "return JSON.stringify({url:location.href,truth:{gtm:gtm,aw:aw,pinterest:pinterest},finding:f});})()"
)


def chanel_check(v):
    if not isinstance(v, dict):
        return False
    truth = v.get("truth") or {}
    finding = v.get("finding")
    if not truth.get("gtm"):
        return False  # sanity: a page with no GTM at all is not a valid measurement
    if not isinstance(finding, dict):
        return False
    try:
        return (sorted(finding.get("gtm") or []) == sorted(truth["gtm"])
                and bool(finding.get("googleAds")) == bool(truth.get("aw"))
                and bool(finding.get("pinterest")) == bool(truth.get("pinterest")))
    except Exception:
        return False


CHANEL_INSTRUCTION = (
    "Open the CHANEL UK homepage. Inspect the LIVE page (page HTML, script tags, window globals) "
    "for marketing tags, then record your finding by setting window.__bench_finding with ONE eval to a "
    "JSON object with exactly these keys: "
    '{"gtm": [every GTM container id found anywhere in the page, each matching /GTM-[A-Z0-9]+/], '
    '"googleAds": [every Google Ads id matching /AW-[0-9]{6,}/], '
    '"pinterest": true if a Pinterest tag is present (window.pintrk is defined, or a ct.pinterest.com / '
    'pintrk reference exists), else false}. '
    "Do not change the page. Finish only after window.__bench_finding is set."
)

CHANEL_TASK = benchlib.Task(
    id="chanel-gb-tag-check",
    instruction=CHANEL_INSTRUCTION,
    url=CHANEL_GB_URL,
    observe_js=CHANEL_OBS_JS,
    verify_js=CHANEL_VERIFY_JS,
    check=chanel_check,
    capabilities=["tag-inspection", "dom-script-audit", "real-site"],
    provenance={
        # derived from the AgentSessions DB (read-only) via task_intake.find_sessions("chanel")
        "source_session_id": "01a08735-b2b1-7000-bad9-87ceabb4aa1a",
        "source_url": "https://www.chanel.com/",
        "verified_against": (
            "window.__bench_finding matches the independently recomputed tag ground truth: "
            "GTM container id set, Google Ads AW- presence, Pinterest tag presence"
        ),
    },
    level="real-site",
)
benchlib.register(CHANEL_TASK)


if __name__ == "__main__":
    import json
    print(json.dumps({"registered": sorted(benchlib.TASKS), "chanel_url": CHANEL_TASK.url}, indent=2))
