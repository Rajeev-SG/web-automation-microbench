# REAL WORK ONLY — no invented tasks, ever

> **This is a hard, non-negotiable rule of this benchmark, not a preference.**
> Every task in this suite must be a real task that Rajeev actually performed,
> mined from recorded session history. We have a rich backlog of genuinely
> messy, authenticated, multi-tab, recovery-heavy browser work. We must never
> fabricate, approximate, or hand-author benchmark tasks when that real corpus
> exists.

## Why

A benchmark on invented tasks measures nothing about the work the rig actually
does. The Pareto/research contract in
`Rajeev-SG/codex-session-orchestration-analysis#84` exists specifically to learn
from **real usage**; #88 (harvest replayable tasks conservatively from real
work) is the intake path. Any task that did not come out of real session
history poisons that loop with fake signal.

## Where real tasks come from

Verified sources in AgentSessions (`~/Library/Application Support/AgentSessions/index.db`,
1,993 sessions; 178 browser-adjacent since 2026-08-15):

| Session ID | Date | Real work | Capability coverage |
|---|---|---|---|
| `2dbcf0e4f72d5fd107ee7e56ca4d5e5f0554c03394f4632144d9436d9bbefd1e` | 2026-09-11 | Pinterest US/UK/MENA Ads Manager flows across three authenticated accounts | multi-tab, auth/session reuse, recovery |
| `9814442de348d4f766ac3c16f4e0f80428f5cc5a3043e264408a7510b0b54a49` | 2026-09-11 | GA4 property navigation + conversion-config import | long-horizon planning, search→extract→act |
| `01a08735-b2b1-7000-bad9-87ceabb4aa1a` | 2026-09-09 | CHANEL tag QA via authenticated OMC Chrome profile / Playwriter | multi-step workflows, robustness |
| `50c64919bb1b21c871c7440369941e9352675c871c744...` *(see below)* | 2026-09-09 | CHANEL PPTX ingestion browser drive | file handling, multi-step |
| `6be9b42baadf7e8b5d59324f25d3d3147f20f8c99e7255a21339b6cb0cdcfa1d` | 2026-09-09 | CHANEL PPTX ingestion verification | recovery, verification |
| skill `amazon-uk-defect-case-flow` | ongoing | Amazon UK defect case via logged-in Chrome | files/upload, multi-tab, recovery |

*(One session ID above is abbreviated — the authoritative table lives in issue
#12, mined fresh each time. Do not copy IDs from this doc into task specs;
re-derive them from the DB.)*

## Rules for adding a task

1. **Mine from sessions first.** Use the `codex-session-mining` skill:
   `sqlite3 "file:~/Library/Application Support/AgentSessions/index.db?mode=ro"`
   against `session_meta` + `session_search_fts`.
2. **Provenance is mandatory**, not optional. Every task entry in
   `bench-ext/tasks_v1.py` must carry:
   - `source_session_id` — the AgentSessions session the task came from;
   - `source_url` — the real site(s)/console the work was done on;
   - `verified_against` — the objective end state that proves success.
   A task without all three is invalid and must not be merged.
3. **Replayability gates** (from #88, enforced): recoverable pre-state, no
   unrecoverable secret dependency, deterministic verifier.
4. **Never hand-author.** No synthetic fixtures, no generic public demos as
   stand-ins, no "similar enough" invented workflows. If a real task does not
   exist for a capability yet, that capability stays **uncovered** — do not
   invent coverage.
5. **The #2/#3 suite draws from this corpus.** Any new task PR must cite the
   session ID it came from in both the code and the PR description.

## Enforcement

- CI guardrail (PR #13) blocks synthetic fixture *files*.
- This document plus the provenance rule above is the guardrail against
  synthetic task *ideas*. Reviewers and agents must reject any task PR that
  cannot point to real session evidence.

## Status

- `bench-ext/fixtures/spa-suite/` (5 invented pages) — **known violation**,
  removal tracked in issue #12.
- `bench-ext/tasks_v1.py` tasks 2–9 — **known violation** (hand-authored or
  generic-public-site), to be replaced by session-derived tasks under #12.
- TodoMVC (task 1) and the 22 measured envelopes in
  `artifacts/2026-09-12/pareto-corpus/` — **legitimate real-work evidence** and
  remain valid.
