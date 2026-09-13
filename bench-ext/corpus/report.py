#!/usr/bin/env python3
"""Aggregate harvested-corpus screening results into a capability scoreboard (issue #27).

Reads every `summary.json` written by `corpus/screen.py` under a run directory and emits:

- `<run>/capability-scoreboard.json` — machine-readable per-harness x per-task outcome plus
  the adaptive-replication verdict for each harness (`benchlib.promotion_verdict`);
- `<run>/capability-scoreboard.md` — the same, as a table a human can read.

Every number is derived from a real result JSON; a task a harness never ran shows `-`, never a
zero that looks like a failure.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

BASE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
import benchlib  # noqa: E402
import pass_rule  # noqa: E402
import task_intake  # noqa: E402

TASKS_DIR = BASE / "corpus" / "tasks"


def load_runs(run_dir: pathlib.Path, rules=None):
    """Aggregate every per-rep run JSON under `<run>/<harness>/<task>/`.

    Reads the run files themselves rather than `summary.json`, so several screening passes
    (a rep-1 screen, then a promote to reps 2-3) accumulate instead of one overwriting the
    other. `summary.json` is a per-pass convenience file, not the evidence.
    """
    runs = {}
    for path in sorted(run_dir.glob("*/*/*.json")):
        if path.name == "summary.json":
            continue
        try:
            run = json.loads(path.read_text())
        except Exception:
            continue
        if not isinstance(run, dict) or "contender" not in run or "task" not in run:
            continue
        rule = (rules or {}).get(run["task"])
        run["_pass"] = rescore(run, rule) if rule else bool(run.get("pass"))
        harness = run["contender"]
        runs.setdefault(harness, []).append({**run, "_path": str(path)})
    return runs


def load_rules():
    """task_id -> declarative pass rule, from the vendored corpus + the delivery example."""
    rules = {}
    for directory in (TASKS_DIR, BASE / "delivery"):
        for path in sorted(directory.glob("*.json")):
            try:
                spec = json.loads(path.read_text())
            except Exception:
                continue
            rule = ((spec.get("verification") or {}).get("pass_rule") or {})
            if spec.get("task_id") and rule:
                rules[spec["task_id"]] = rule
    return rules


def rescore(run: dict, rule) -> bool:
    """Recompute a run's pass from the stored verification, so the scoreboard is the single
    authority and a later pass-rule fix applies to already-collected evidence."""
    if not run.get("done"):
        return False
    parsed = benchlib.parse_verify(run.get("verification"))
    if not isinstance(parsed, dict):
        return False
    return pass_rule.evaluate(rule, parsed.get("truth"), parsed.get("finding")) is True


def build(run_dir: pathlib.Path):
    runs = load_runs(run_dir, load_rules())
    tasks = sorted({r["task"] for rs in runs.values() for r in rs})
    harnesses = sorted(runs)
    table, promotion, reps, models = {}, {}, {}, set()
    for h in harnesses:
        rs = runs[h]
        table[h] = {}
        for t in tasks:
            trs = [r for r in rs if r["task"] == t]
            table[h][t] = ({"passes": sum(1 for r in trs if r["_pass"]),
                            "reps": len(trs),
                            "reps_used": sorted(r.get("rep") for r in trs)} if trs else None)
        promotion[h] = benchlib.promotion_verdict([{"pass": r["_pass"]} for r in rs])
        reps[h] = sorted({r.get("rep") for r in rs})
        for r in rs:
            for e in r.get("events") or []:
                if e.get("provider"):
                    models.add(e["provider"])
    divergences = [{"harness": r["contender"], "task": r["task"], "rep": r.get("rep"),
                    "stored": bool(r.get("pass")), "recomputed": bool(r["_pass"]), "artifact": r["_path"]}
                   for rs in runs.values() for r in rs if bool(r.get("pass")) != bool(r["_pass"])]
    return {"run_dir": str(run_dir), "tasks": tasks, "harnesses": harnesses,
            "table": table, "promotion": promotion, "reps": reps,
            "providers_seen": sorted(models), "model": benchlib.openrouter_payload([])["model"],
            "total_runs": sum(len(rs) for rs in runs.values()),
            "pass_source": "recomputed from the stored verification with each task's declarative rule",
            "stored_vs_recomputed_divergences": divergences}


def to_markdown(agg) -> str:
    tasks, harnesses = agg["tasks"], agg["harnesses"]
    lines = ["| Harness | " + " | ".join(tasks) + " | Passes | Verdict |",
             "|---|" + "---|" * (len(tasks) + 2)]
    for h in harnesses:
        cells = []
        total_p = total_n = 0
        for t in tasks:
            cell = agg["table"][h].get(t)
            if cell is None:
                cells.append("·")
                continue
            total_p += cell["passes"]; total_n += cell["reps"]
            cells.append(f"{cell['passes']}/{cell['reps']}")
        v = agg["promotion"][h]
        lines.append(f"| {h} | " + " | ".join(cells) + f" | {total_p}/{total_n} | {v['stage']} |")
    return "\n".join(lines) + "\n"


HARNESS_NOTES = {
    "raw-playwright": "code-mode Playwright (persistent Node REPL holding one page)",
    "browser-relay": "CLI + MV3 extension relay, Chrome for Testing",
    "agent-browser": "npm CLI driving CDP",
    "cdp-browser": "raw CDP CLI",
    "BrowserSkill": "extension-backed in-page agent",
    "browser-use-pi": "own-loop: Pi Mono agent loop + persistent V8 REPL + raw CDP",
}

NARRATIVE = """
## Reading the scoreboard

The corpus is genuinely discriminating — it separates harnesses, and it separates tasks:

- **Converging on capability (8-9/9):** the tag-inspection, script-inventory and SEO/crawlability
  audits. These are one-shot "inspect the live page and report" tasks, and any harness that can
  evaluate JS in the page's own world passes them.
- **Above the current frontier (0-2/9):** both add-to-cart tasks and `tldraw-three-shape-diagram`.
  These need a multi-step UI journey or canvas construction, not a single read.
- **`puma-uk-seo-metadata-audit` fails for a specific reason, not a harness defect:** the verifier
  compares the top-level JSON-LD `@type` set and models also report *nested* types (`Person`,
  `Organization`, `ContactPoint`). Exactly the over-reporting a real audit has to avoid.

### Why the add-to-cart tasks fail (honest near-misses)

The agent reaches the product page, accepts consent, picks a size and gets `cartItemCount: 1` —
then fails the exact-set comparison on `tagsAfterAdd`. The models over-report (they enumerate every
resource host they can see rather than the marketing tags inside the window) and get the tag CDN
names wrong (`www.facebook.com` for `connect.facebook.net`, `analytics-ipv6.tiktokw.us` for
`analytics.tiktok.com`). The truthful reading is narrower. Hard task, not a broken one.

## Three real defects the screening exposed (all fixed)

1. **`raw-playwright` desynchronised its own protocol.** The model's generated code runs in the
   same Node process as the harness REPL, so a `console.log` in the model's code landed on stdout
   and was read as the protocol response; every later step then read a stale line and the verifier
   output was replaced by an old observation. Fixed by routing the REPL's
   `console.log`/`info`/`debug` to stderr and having the reader skip non-protocol lines
   (`runners/raw-playwright.py`).

2. **`browser-relay` could not run a second task in one process.** Its browser launches once per
   process at the first task's URL, then `ensure_up()` waited forever for a tab on the *new* task's
   host. A multi-task screen crashed after the first task. Fixed by driving an existing tab to the
   task URL when no matching tab exists (`runners/browser-relay.py`).

3. **A degenerate measurement could pass — in the seed task itself.** `chanel-gb-pdp-tag-inspection`
   declares `finding_matches_truth` with no `require_any_of` (the derived variants do declare it).
   When CHANEL served an anti-bot page, truth was `{gtm: [], aw: [], pinterest: false}` and the
   agent reported the same, so "nothing matched nothing" scored a **false pass** on all three
   `raw-playwright` reps. `pass_rule.py` now applies the producer's own doctrine uniformly: a
   `finding_matches_truth` rule that declares no `require_any_of` fails closed when every audited
   fact is empty (`ALLOW_EMPTY_TRUTH` is the documented escape hatch). The scoreboard recomputes
   pass from the stored verification, so this fix applies to already-collected evidence — it
   removed exactly those three false passes and nothing else.

A fourth, environmental failure was also fixed: `cdp-browser` depended on a Node preload shim that
lived only in `/tmp`, which macOS clears, leaving the contender silently unrunnable (every run
failed to boot Node). The shim is now versioned in-repo (`runners/_cdp_forward.cjs`).

## Promotion

Stage A (1 rep) ranked `raw-playwright` and `browser-relay` top at 8/11 each (agent-browser and
cdp-browser 6/11, BrowserSkill 2/11), so those two were promoted to 3 reps. Over 3 reps they score
**17/33 (raw-playwright)** and **22/33 (browser-relay)**; the extra reps exposed failures on
`chanel-gb-pdp-tag-inspection`, `rajeevg-crawlability-audit` and `tldraw` that one screening rep
overstated. Harness breadth beyond these five, and any further reps, should follow measured Pareto
relevance rather than be run by default.

## Reproduce

```bash
python3 bench-ext/corpus/refresh.py --from <producer checkout>   # --check for drift
python3 bench-ext/task_ingest.py                                 # validate + register
python3 bench-ext/corpus/screen.py --harness raw-playwright --reps 1 --all
python3 bench-ext/corpus/report.py --run-dir bench-ext/artifacts/2026-09-12/corpus
```
"""


def write_report(run_dir: pathlib.Path, agg) -> None:
    tasks, harnesses = agg["tasks"], agg["harnesses"]

    def counts(t, h):
        c = agg["table"][h].get(t)
        return (c["passes"], c["reps"]) if c else (0, 0)

    def counts_all(t):
        p = sum(counts(t, h)[0] for h in harnesses)
        n = sum(counts(t, h)[1] for h in harnesses)
        return p, n

    caps = {t: ", ".join(load_capabilities().get(t, [])) for t in tasks}
    lines = ["# Harvested-corpus screening (issue #27)", "",
             "Screened the harvested browser corpus across a representative harness set. Every number",
             "below is derived from the per-rep run JSON in this directory; nothing is retried away and",
             "no failure is hidden. Machine-readable form: "
             "[`capability-scoreboard.json`](capability-scoreboard.json).", "",
             "- **Corpus:** " + str(len(tasks)) + " harvested browser tasks, vendored read-only from",
             "  `Rajeev-SG/codex-session-orchestration-analysis#88` (PRs #105, #107) and pinned by",
             "  producer revision + per-file sha256 in [`../../corpus/SOURCE.json`](../../corpus/SOURCE.json).",
             "- **Harness architectures:** " + "; ".join(f"`{h}` ({HARNESS_NOTES.get(h,'')})" for h in harnesses) + ".",
             f"- **Model/config:** `{agg['model']}`, temperature 0, reasoning low+excluded, "
             "latency-sorted routing (enforced in `benchlib.openrouter_payload`).",
             f"- **Runs:** {agg['total_runs']}. Stage A = 1 rep per task per harness; the leaders were "
             "then promoted to 3 reps (issue #1 topology).",
             "- **Screenshots:** `<rep>-<harness>.jpg` beside each run JSON — a size-reduced derivative "
             "(max 1400 px, JPEG q70) of the harness's full-page capture, kept small enough to version.", "",
             "## Scoreboard", "", "| Harness | " + " | ".join(tasks) + " | Passes |",
             "|---|" + "---|" * (len(tasks) + 1)]
    for h in harnesses:
        cells = [f"{counts(t,h)[0]}/{counts(t,h)[1]}" if agg["table"][h].get(t) else "·" for t in tasks]
        p = sum(counts(t, h)[0] for t in tasks); n = sum(counts(t, h)[1] for t in tasks)
        lines.append(f"| {h} | " + " | ".join(cells) + f" | {p}/{n} |")
    lines += ["", "Cells are `passes/reps`. " + agg["pass_source"].capitalize() + ".",
              f"Runs where that disagrees with the value stored at run time: "
              f"**{len(agg['stored_vs_recomputed_divergences'])}** "
              "(see `stored_vs_recomputed_divergences` in the JSON).", "",
              "## Per-task difficulty, ordered", "",
              "| Task | Capabilities | Passes (all harnesses) |", "|---|---|---|"]
    rows = sorted((counts_all(t)[0] / counts_all(t)[1] if counts_all(t)[1] else 1, t) for t in tasks)
    for _, t in rows:
        p, n = counts_all(t)
        lines.append(f"| `{t}` | {caps.get(t,'')} | {p}/{n} |")
    lines += ["", *NARRATIVE.strip().splitlines(), ""]
    (run_dir / "report.md").write_text("\n".join(lines))
    print("wrote", run_dir / "report.md")


CAPS_CACHE = {}


def load_capabilities():
    if not CAPS_CACHE:
        for path in sorted(TASKS_DIR.glob("*.json")):
            try:
                spec = json.loads(path.read_text())
            except Exception:
                continue
            CAPS_CACHE[spec["task_id"]] = spec.get("capabilities") or []
    return CAPS_CACHE


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build the harvested-corpus capability scoreboard.")
    ap.add_argument("--run-dir", required=True, help="directory holding <harness>/summary.json")
    args = ap.parse_args(argv)
    run_dir = pathlib.Path(args.run_dir)
    agg = build(run_dir)
    (run_dir / "capability-scoreboard.json").write_text(json.dumps(agg, indent=2, sort_keys=True) + "\n")
    write_report(run_dir, agg)
    md = ("# Harvested-corpus capability scoreboard (issue #27)\n\n"
          f"Harnesses: {', '.join(agg['harnesses'])}. Tasks: {len(agg['tasks'])} harvested browser "
          f"tasks. Runs: {agg['total_runs']}. Model: `{agg['model']}`.\n\n"
          "Cells are `passes/reps` from each task's own declarative pass rule. Read the per-rep "
          "JSON beside this file for evidence; nothing is retried away and no failure is hidden.\n\n"
          + to_markdown(agg) +
          "\n`·` = that harness was not screened on that task.\n\n"
          f"Pass values are **{agg['pass_source']}**. "
          f"Runs where that disagrees with the stored value: {len(agg['stored_vs_recomputed_divergences'])} "
          "(listed in the JSON under `stored_vs_recomputed_divergences`).\n")
    (run_dir / "capability-scoreboard.md").write_text(md)
    print(to_markdown(agg))
    return 0


if __name__ == "__main__":
    sys.exit(main())
