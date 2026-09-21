# adaptive-ui-runtime — screening results (2026-09-21)

- runtime commit `2c6276ce1fa86e7d2dabbf90e343f885cc07a5ef`; adapter `bench-ext/runners/adaptive-ui-runtime.py` (own-loop).
- Model: `openrouter:z-ai/glm-5.3-flash` (strong manager, **default** OpenRouter routing) + `classifier.dev` Jev.
- Pass = INDEPENDENT (benchlib verify_js + pass_rule over CDP). `runtime_verified` is the runtime's own verdict;
  `vacuous_self_pass` flags a runtime self-pass on an empty finding. Never merged.
- 2 reps per task; failures preserved; nothing retried away.

| Task | Pass (indep) | Runtime verdict | Agree | Vacuous self-pass | Median wall | Manager calls (r1/r2) | Jev calls (r1/r2) | Failure classes |
|---|---:|---:|:--:|:--:|---:|---:|---:|---|
| `allbirds-uk-add-to-cart-tag-check` | 0/2 | 0/2 | 2/2 | 0 | 11.7s | 0/0 | 0/0 | stale_target |
| `chanel-gb-pdp-tag-inspection` | 0/2 | 0/2 | 2/2 | 0 | 138.3s | 0/1 | 0/0 | stale_target |
| `gymshark-uk-add-to-cart-tag-check` | 0/2 | 0/2 | 2/2 | 0 | 7.5s | 0/0 | 0/0 | repeated_action_loop |
| `porsche-uk-script-inventory` | 0/2 | 0/2 | 2/2 | 0 | 134.5s | 3/7 | 5/5 | stale_target |
| `porsche-uk-tag-inspection` | 0/2 | 0/2 | 2/2 | 0 | 23.5s | 0/3 | 5/5 | repeated_action_loop |
| `puma-uk-script-inventory` | 0/2 | 0/2 | 2/2 | 0 | 2.9s | 0/0 | 0/0 | repeated_action_loop |
| `puma-uk-seo-metadata-audit` | 0/2 | 0/2 | 2/2 | 0 | 5.3s | 0/0 | 0/0 | repeated_action_loop |
| `puma-uk-tag-inspection` | 0/2 | 0/2 | 2/2 | 0 | 7.1s | 0/0 | 0/0 | repeated_action_loop |
| `rajeevg-crawlability-audit` | 0/2 | 0/2 | 2/2 | 0 | 3.9s | 0/0 | 0/0 | repeated_action_loop |
| `rajeevg-seo-metadata-audit` | 0/2 | 0/2 | 2/2 | 0 | 3.2s | 0/0 | 0/0 | repeated_action_loop |
| `tldraw-three-shape-diagram` | 0/2 | 2/2 | 0/2 | 2 | 11.2s | 1/1 | 0/1 | — |
| `todomvc` | 0/2 | 0/2 | 2/2 | 0 | 32.3s | 6/7 | 0/0 | repeated_action_loop |
| **total** | **0/24** | | | **2** | | | | |

## Model engagement (the manager/Jev DID run)

Across the 24 runs the runtime made **29** manager calls and **21** Jev calls, with **22375** manager input tokens — on the decision classes (`todomvc`, `porsche-*`, `chanel-*`, `tldraw`). The 7 single-page DOM/eval audit tasks made **0** model calls because the router sends them straight to its structured route and fails there; no manager decision is requested for that class. This is a routing outcome, not a credential failure (the same env produced manager calls elsewhere in the same pass). Token/cost columns are manager usage only (Jev is classifier.dev).

## Failure classes observed

- `repeated_action_loop` — the manager re-issues the same action (types a value without submitting; re-clicks a target).
- `stale_target` — the runtime resolves an ordinal node from one observation, acts without re-observing,
  and its stamp-revalidation fails closed after a navigating click. **Attributable to the runtime, not the
  adapter:** re-running the same tasks through the runtime's own native `IsolatedBrowserTransport`
  (no CDP subclass) reproduces `stale_target` (`allbirds`) and `repeated_action_loop` (`porsche-tag-inspection`).
- `premature_done` — the actor signals done; the verifier rejects it.
- **Capability gap (all harvested audit tasks):** the runtime's action vocabulary is
  click/type/key/select/scroll/wait/focus/inspect with no page-eval action, so it cannot set the
  `window.__bench_finding` every corpus task requires.

## Verdict-disagreement classes

The runtime's own verifier and the independent verifier agreed on 22/24 runs.
The 2 disagreements are `vacuous_self_pass`: the runtime reported success while its recorded
finding was null/empty and the independent verifier failed (all `tldraw-three-shape-diagram`).
