# Round 7 — Browser Use Pi (issue #34)

**Contender:** [browser-use/browser-use-pi](https://github.com/browser-use/browser-use-pi), npm
`@browser_use/pi` **0.1.0** at git `fa838f3298673950923bdaf12bd3c1b6279cd119` (2026-09-13).
**Machine:** macOS, Node v26.7.0 (`engines` requires >= 22.19).
**Reproduce:** `bash bench-ext/runners/browser-use-pi-setup.sh` (clone → pin → `npm install` → `npm run build`).

## Architecture (why it was admitted)

`Pi Mono agent loop → persistent V8 REPL → raw CDP → Chrome`, with AX-tree and screenshot
observations, sessions, saved logins and follow-ups. Unlike every other contender this is not a thin
"one native command per model call" CLI: the model writes JavaScript cells into one persistent Node
worker whose top-level state survives between calls, and builds its own browser helpers. That is a
materially distinct architecture (the §10 admission bar) whose stated value is long-horizon **code
batching**, not fast-path latency.

## Configuration

- **Model:** `z-ai/glm-5.3-flash` via OpenRouter, reasoning `low`, temperature default.
- **Routing:** `provider.sort: "latency"`. GLM 5.3 Flash is not in Pi's pinned catalog, so the driver
  registers it with `compat.openRouterRouting = {sort: 'latency'}`; the OpenAI-completions payload
  then carries `provider: {sort: 'latency'}` exactly like the other rows. Routing compatibility is
  therefore documented as **passed through**, not worked around.
- **Browser:** local Chrome, **not** Browser Use Cloud — `Browser.chromium({headless: true, profileDir})`,
  a fresh unique profile and workspace per rep (Browser Use Pi locks one profile to one owner).
- **Runner mode:** own-loop. One `agent.run()` per rep, never one primitive action per call — the
  fairness rule in the issue. Timed from the first model call to the agent's completion; browser
  launch and the independent verifier are outside the timer.
- **Verification:** the shared verifier runs on the *same live browser* over CDP before close
  (`Runtime.evaluate(VERIFY_JS)`), and the pass predicate is the task's own rule (TodoMVC
  `benchlib.check_pass`; harvested tasks via `pass_rule`). The agent's own "done" is never trusted.
- **Cost basis:** Pi's catalog rates set to the benchmark's published latency-sorted rates
  ($0.075/M in, $0.25/M out, $0.0375/M cached) for comparability with the other rows.

## 1. TodoMVC latency microbenchmark — 7/10, median 53.5s

10 reps (2-rep screening then promoted; the issue-#1 topology allows 10 for high variance — which
this showed). Rejection of the pure 5-rep run is deliberate: reps 1–5 screened clean 5/5, then reps
6–10 exposed three false successes, so the promoted set is reported, not the flattering subset.

| Rep | Pass | Status | Model calls | Wall s | Tok in | Tok out | Tok cached | Cost |
|---:|---|---|---:|---:|---:|---:|---:|---:|
| 1 | PASS | completed | 7 | 43.6 | 7348 | 728 | 9088 | $0.00087 |
| 2 | PASS | completed | 7 | 47.8 | 4815 | 607 | 12352 | $0.00070 |
| 3 | PASS | completed | 6 | 32.8 | 2485 | 522 | 9664 | $0.00046 |
| 4 | PASS | completed | 9 | 62.7 | 6593 | 979 | 17664 | $0.00100 |
| 5 | PASS | completed | 7 | 44.1 | 3193 | 761 | 14208 | $0.00064 |
| 6 | PASS | completed | 8 | 51.1 | 5325 | 614 | 13568 | $0.00076 |
| 7 | PASS | completed | 8 | 55.9 | 6576 | 624 | 11712 | $0.00082 |
| 8 | fail | completed | 10 | 64.6 | 6951 | 1115 | 19328 | $0.00109 |
| 9 | fail | completed | 10 | 58.1 | 6628 | 914 | 19968 | $0.00103 |
| 10 | fail | completed | 10 | 99.7 | 7628 | 1377 | 20992 | $0.00123 |

- **Median 53.5s, 7/10.** Tokens ≈ 6.6k in / 0.7k out per run; ≈ $0.0010/run.
- **Every failure is a false success, and the verifier caught it.** Reps 8, 9 and 10 added both
  todos, toggled "Email supplier" correctly, but never clicked the Active filter (URL stayed `#/`
  instead of `#/active`) and reported done. Rep 10 did not even toggle. Status `completed` here means
  "delivered a schema-valid string", not "the task succeeded".
- Relative to the field: ~13× slower than BrowserSkill (4.1s) and slower than raw-playwright (42.7s).
  On a three-action deterministic task the persistent-REPL architecture is pure overhead — a larger
  prompt and AX/tool plumbing per turn buy nothing when one native command per step already suffices.

## 2. Harvested real-work corpus (issue #27) — 4/11 (1-rep screening)

`python3 bench-ext/corpus/screen_native.py --harness browser-use-pi --reps 1 --all`
Results in `artifacts/2026-09-12/corpus/browser-use-pi/`, aggregated into the shared scoreboard
(`artifacts/2026-09-12/corpus/capability-scoreboard.md`) so it is directly comparable with the other
five harnesses.

| Task | Pass | Status | Model calls | Wall s | Tok in | Tok out | Cost |
|---|---|---|---:|---:|---:|---:|---:|
| `allbirds-uk-add-to-cart-tag-check` | fail | completed | 14 | 53.2 | 16593 | 1589 | $0.00209 |
| `chanel-gb-pdp-tag-inspection` | PASS | completed | 13 | 152.8 | 4397 | 2655 | $0.00157 |
| `gymshark-uk-add-to-cart-tag-check` | fail | completed | 14 | 110.6 | 20448 | 1913 | $0.00245 |
| `porsche-uk-script-inventory` | fail | completed | 3 | 36.7 | 2172 | 250 | $0.00028 |
| `porsche-uk-tag-inspection` | PASS | completed | 4 | 26.0 | 2264 | 294 | $0.00033 |
| `puma-uk-script-inventory` | fail | completed | 3 | 13.7 | 5768 | 305 | $0.00051 |
| `puma-uk-seo-metadata-audit` | fail | completed | 3 | 18.4 | 6472 | 457 | $0.00060 |
| `puma-uk-tag-inspection` | fail | completed | 6 | 32.9 | 10730 | 541 | $0.00098 |
| `rajeevg-crawlability-audit` | PASS | completed | 10 | 21.6 | 8249 | 639 | $0.00105 |
| `rajeevg-seo-metadata-audit` | PASS | completed | 5 | 12.0 | 3304 | 953 | $0.00062 |
| `tldraw-three-shape-diagram` | fail | completed | 14 | 25.8 | 48465 | 1843 | $0.00437 |

**It passes the anti-bot boundary — but it is not unique in doing so.** It records the two GTM container
ids correctly on `chanel-gb-pdp-tag-inspection`, with the tolerance the pass rule allows for extra keys.
The task stands at **3/10 across harnesses, and browser-relay accounts for two of those three (2/3)**.
Every one of the four tasks browser-use-pi passed is a task browser-relay also passes, so its 4/11 is a
**strict subset** of browser-relay's 22/33. An earlier draft of this report claimed it was "the only
harness in the set to pass" this task; that was wrong and is corrected here.

**Honest failures (not harness defects):**
- `allbirds`/`gymshark` (add-to-cart): the journey actually completed — allbirds' cart reaches
  `cartItemCount: 1` — but the agent never published `window.__bench_finding`, so the finding is null.
  Same "reach the state, fail to report the exact set" mode the other harnesses exhibit.
- `puma-uk-script-inventory`: under-reported the third-party host set (4 of 9).
- `porsche-uk-script-inventory`: content is exactly right but **double-encoded** — it set
  `window.__bench_finding` to a JSON *string* instead of an object.
- `puma-uk-seo-metadata-audit`: over-reported nested JSON-LD `@type`s (the documented over-reporting
  failure that also catches the other harnesses).
- `tldraw-three-shape-diagram`: never published a finding.

## Pareto impact

- **Fast path: no new frontier.** Dominated on (speed, cost) by every thin CLI in the 4–15s block.
- **Capability: also no new frontier.** A candidate is Pareto-relevant only if it passes something the
  frontier does not; browser-use-pi passes nothing browser-relay misses. It reaches the anti-bot
  boundary but does not extend it. Reporting it as a capability win would have been a miscount of the
  scoreboard (browser-relay 2/3 vs browser-use-pi 1/1 on that task) — the corrected reading is that
  the new architecture adds a datapoint, not a Pareto point.

## Does the persistent code-execution model get more competitive as tasks get longer?

Partially, and not yet. Two observations from the evidence:

1. **Round-trip count does drop as tasks get more compositional.** The one-shot audits cost 3–6 model
   calls versus the 8–14 steps the thin CLIs need for the same work — the model composes a page
   inspection into one cell. That is the batching advantage, visible.
2. **It does not yet translate into wall-time or reliability.** CHANEL took 152.8s over 13 steps;
   TodoMVC's median is 53.5s. Each cell round-trip is heavier than a thin command, and the agent
   re-derives helpers instead of reusing them. On this corpus it mostly used the REPL as a slower
   one-command-per-step loop.

The honest answer: the architecture *permits* bigger composed actions, but this run did not exploit
them enough to beat the thin leaders on speed or the strongest rows on reliability — and it extended
neither frontier. That is a **1-rep corpus screen and a 10-rep microbenchmark**, so it is evidence
against the hypothesis rather than a settled verdict. The claim to test next is a long-horizon,
multi-tab, authenticated workflow where a single 30-action cell would beat 30 round-trips; the
exploration-report task proposed in issue #3 is exactly that shape.

## Not yet covered

- **Own-Chrome / saved-login mode.** The issue prefers the user's own Chrome; the corpus tasks are
  auth-free public pages, so this run used headless local Chrome. The driver supports
  `BUPI_MODE=chrome BUPI_CDP_URL=...` for attaching to a real logged-in Chrome, but no authenticated
  task was scored.
- **Multi-tab / follow-up / persisted-workspace tasks.** The corpus has no such task yet; the
  long-horizon claim above is inferred, not measured.
- **Browser Use Cloud** was deliberately not used.
- **Promotion.** 4/11 is a 1-rep screen; a 3-rep promotion of the tasks it passed (and the ones it
  narrowly missed) would tighten the capability number.
