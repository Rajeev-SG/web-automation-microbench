# adaptive-ui-runtime — screening results (2026-09-21)

- runtime commit `2c6276ce1fa86e7d2dabbf90e343f885cc07a5ef`; adapter `bench-ext/runners/adaptive-ui-runtime.py` (own-loop).
- All artifacts in this directory were produced by THIS adapter (`screen_native.py --harness adaptive-ui-runtime`), not hand-edited.
- Model: `openrouter:z-ai/glm-5.3-flash` (strong manager, **default** OpenRouter routing) + `classifier.dev` Jev.
- Pass = INDEPENDENT (benchlib verify_js + pass_rule over CDP). `runtime_verified` is the runtime's own verdict;
  `vacuous_self_pass` flags a runtime self-pass on an empty finding. `runtime_verified` is never the score.
- 2 reps per task; failures preserved; nothing retried away.

| Task | Pass (indep) | Runtime verdict | Agree | Vacuous self-pass | Median wall | Manager calls (r1/r2) | Jev calls (r1/r2) | Failure classes |
|---|---:|---:|:--:|:--:|---:|---:|---:|---|
| `allbirds-uk-add-to-cart-tag-check` | 0/2 | 0/2 | 2/2 | 0 | 12.0s | 0/0 | 0/0 | stale_target |
| `chanel-gb-pdp-tag-inspection` | 0/2 | 1/2 | 1/2 | 1 | 25.9s | 1/6 | 0/0 | repeated_action_loop |
| `gymshark-uk-add-to-cart-tag-check` | 0/2 | 0/2 | 2/2 | 0 | 7.1s | 0/0 | 0/0 | repeated_action_loop |
| `porsche-uk-script-inventory` | 0/2 | 0/2 | 2/2 | 0 | 38.1s | 3/0 | 1/0 | premature_done |
| `porsche-uk-tag-inspection` | 0/2 | 0/2 | 2/2 | 0 | 146.6s | 11/10 | 4/4 | stale_target |
| `puma-uk-script-inventory` | 0/2 | 0/2 | 2/2 | 0 | 6.4s | 0/0 | 0/0 | repeated_action_loop |
| `puma-uk-seo-metadata-audit` | 0/2 | 0/2 | 2/2 | 0 | 6.7s | 0/0 | 0/0 | repeated_action_loop |
| `puma-uk-tag-inspection` | 0/2 | 0/2 | 2/2 | 0 | 7.1s | 0/0 | 0/0 | repeated_action_loop |
| `rajeevg-crawlability-audit` | 0/2 | 0/2 | 2/2 | 0 | 5.2s | 0/0 | 0/0 | repeated_action_loop |
| `rajeevg-seo-metadata-audit` | 0/2 | 0/2 | 2/2 | 0 | 3.5s | 0/0 | 0/0 | repeated_action_loop |
| `tldraw-three-shape-diagram` | 0/2 | 2/2 | 0/2 | 2 | 15.9s | 3/1 | 1/1 | — |
| `todomvc` | 0/2 | 0/2 | 2/2 | 0 | 45.8s | 6/7 | 0/0 | repeated_action_loop |
| **total** | **0/24** | | | **3** | | | | |

## Model engagement (the manager/Jev DID run)

Across the 24 runs the runtime made **48** manager calls and **11** Jev calls, with **54739** manager input tokens — on the decision classes (`todomvc`, `porsche-*`, `chanel-*`, `tldraw`).
The 7 single-page DOM/eval audit tasks made **0** model calls because the runtime's router sends that
class straight to its structured route and fails there; no manager decision is requested. That is a
routing outcome, not a credential failure — the same env produced manager calls elsewhere in the same
pass. Token/cost columns are manager usage only (Jev is classifier.dev, no tokens).

## Failure classes observed

- `repeated_action_loop` — the manager re-issues the same action (types a value without submitting; re-clicks a target).
- `stale_target` — the runtime resolves an ordinal node from one observation, acts without re-observing, and
  its stamp-revalidation fails closed after a navigating click. **Attributable to the runtime, not the adapter:**
  re-running the same tasks through the runtime's own native `IsolatedBrowserTransport` (no CDP subclass, no
  adapter code) reproduces `stale_target` (`allbirds`) and `repeated_action_loop` (`porsche-uk-tag-inspection`).
- `premature_done` — the actor signals done; the verifier rejects it.
- **Capability gap (all harvested audit tasks):** the runtime's action vocabulary is
  click/type/key/select/scroll/wait/focus/inspect with no page-eval action, so it cannot set the
  `window.__bench_finding` every corpus task requires.

## Verdict-disagreement classes

Verdicts agreed on 21/24 runs. The 3 disagreements are
`vacuous_self_pass` (runtime reported success, recorded finding null/empty, independent verifier failed):
`tldraw-three-shape-diagram` r1+r2 and `chanel-gb-pdp-tag-inspection` r2.
