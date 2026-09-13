# Harvested-corpus screening (issue #27)

Screened the harvested browser corpus across a representative harness set. Every number
below is derived from the per-rep run JSON in this directory; nothing is retried away and
no failure is hidden. Machine-readable form: [`capability-scoreboard.json`](capability-scoreboard.json).

- **Corpus:** 11 harvested browser tasks, vendored read-only from
  `Rajeev-SG/codex-session-orchestration-analysis#88` (PRs #105, #107) and pinned by
  producer revision + per-file sha256 in [`../../corpus/SOURCE.json`](../../corpus/SOURCE.json).
- **Harness architectures:** `BrowserSkill` (extension-backed in-page agent); `agent-browser` (npm CLI driving CDP); `browser-relay` (CLI + MV3 extension relay, Chrome for Testing); `browser-use-pi` (own-loop: Pi Mono agent loop + persistent V8 REPL + raw CDP); `cdp-browser` (raw CDP CLI); `raw-playwright` (code-mode Playwright (persistent Node REPL holding one page)).
- **Model/config:** `z-ai/glm-5.3-flash`, temperature 0, reasoning low+excluded, latency-sorted routing (enforced in `benchlib.openrouter_payload`).
- **Runs:** 110. Stage A = 1 rep per task per harness; the leaders were then promoted to 3 reps (issue #1 topology).
- **Screenshots:** `<rep>-<harness>.jpg` beside each run JSON — a size-reduced derivative (max 1400 px, JPEG q70) of the harness's full-page capture, kept small enough to version.

## Scoreboard

| Harness | allbirds-uk-add-to-cart-tag-check | chanel-gb-pdp-tag-inspection | gymshark-uk-add-to-cart-tag-check | porsche-uk-script-inventory | porsche-uk-tag-inspection | puma-uk-script-inventory | puma-uk-seo-metadata-audit | puma-uk-tag-inspection | rajeevg-crawlability-audit | rajeevg-seo-metadata-audit | tldraw-three-shape-diagram | Passes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BrowserSkill | 0/1 | 0/1 | 0/1 | 1/1 | 1/1 | 0/1 | 0/1 | 0/1 | 0/1 | 0/1 | 0/1 | 2/11 |
| agent-browser | 0/1 | 0/1 | 0/1 | 1/1 | 1/1 | 1/1 | 0/1 | 1/1 | 1/1 | 1/1 | 0/1 | 6/11 |
| browser-relay | 0/3 | 2/3 | 0/3 | 3/3 | 3/3 | 3/3 | 1/3 | 3/3 | 3/3 | 3/3 | 1/3 | 22/33 |
| browser-use-pi | 0/1 | 1/1 | 0/1 | 0/1 | 1/1 | 0/1 | 0/1 | 0/1 | 1/1 | 1/1 | 0/1 | 4/11 |
| cdp-browser | 0/1 | 0/1 | 1/1 | 1/1 | 0/1 | 1/1 | 0/1 | 1/1 | 1/1 | 1/1 | 0/1 | 6/11 |
| raw-playwright | 0/3 | 0/3 | 0/3 | 2/3 | 3/3 | 3/3 | 0/3 | 3/3 | 2/3 | 3/3 | 1/3 | 17/33 |

Cells are `passes/reps`. Recomputed from the stored verification with each task's declarative rule.
Runs where that disagrees with the value stored at run time: **3** (see `stored_vs_recomputed_divergences` in the JSON).

## Per-task difficulty, ordered

| Task | Capabilities | Passes (all harnesses) |
|---|---|---|
| `allbirds-uk-add-to-cart-tag-check` | consent-handling, commerce-flow, add-to-cart, tag-inspection, real-site | 0/10 |
| `gymshark-uk-add-to-cart-tag-check` | consent-handling, commerce-flow, add-to-cart, tag-inspection, real-site | 1/10 |
| `puma-uk-seo-metadata-audit` | seo-audit, head-metadata, structured-data, real-site | 1/10 |
| `tldraw-three-shape-diagram` | ui-creation, canvas-tool, structural-verification, real-site | 2/10 |
| `chanel-gb-pdp-tag-inspection` | tag-inspection, dom-script-audit, real-site | 3/10 |
| `porsche-uk-script-inventory` | vendor-inventory, dom-script-audit, real-site | 8/10 |
| `puma-uk-script-inventory` | vendor-inventory, dom-script-audit, real-site | 8/10 |
| `puma-uk-tag-inspection` | tag-inspection, dom-script-audit, real-site | 8/10 |
| `rajeevg-crawlability-audit` | crawlability, robots-txt, sitemap, real-site | 8/10 |
| `porsche-uk-tag-inspection` | tag-inspection, dom-script-audit, real-site | 9/10 |
| `rajeevg-seo-metadata-audit` | seo-audit, head-metadata, structured-data, real-site | 9/10 |

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
