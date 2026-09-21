# adaptive-ui-runtime — screening results (2026-09-21)

- runtime commit `2c6276ce1fa86e7d2dabbf90e343f885cc07a5ef`; adapter `bench-ext/runners/adaptive-ui-runtime.py` (own-loop).
- Model: `openrouter:z-ai/glm-5.3-flash` (strong manager, default routing) + `classifier.dev` Jev.
- Pass = INDEPENDENT (benchlib verify_js + pass_rule over CDP). `runtime_verified` is the runtime's own verdict.
- 2 reps per task; failures preserved; nothing retried away.

| Task | Pass (indep) | Runtime verdict | Agree | Median wall | Failure classes |
|---|---:|---:|:--:|---:|---|
| `allbirds-uk-add-to-cart-tag-check` | 0/2 | 0/2 | 2/2 | 11.7s | stale_target |
| `chanel-gb-pdp-tag-inspection` | 0/2 | 0/2 | 2/2 | 138.3s | stale_target |
| `gymshark-uk-add-to-cart-tag-check` | 0/2 | 0/2 | 2/2 | 7.5s | repeated_action_loop |
| `porsche-uk-script-inventory` | 0/2 | 0/2 | 2/2 | 134.5s | stale_target |
| `porsche-uk-tag-inspection` | 0/2 | 0/2 | 2/2 | 23.5s | repeated_action_loop |
| `puma-uk-script-inventory` | 0/2 | 0/2 | 2/2 | 2.9s | repeated_action_loop |
| `puma-uk-seo-metadata-audit` | 0/2 | 0/2 | 2/2 | 5.3s | repeated_action_loop |
| `puma-uk-tag-inspection` | 0/2 | 0/2 | 2/2 | 7.1s | repeated_action_loop |
| `rajeevg-crawlability-audit` | 0/2 | 0/2 | 2/2 | 3.9s | repeated_action_loop |
| `rajeevg-seo-metadata-audit` | 0/2 | 0/2 | 2/2 | 3.2s | repeated_action_loop |
| `tldraw-three-shape-diagram` | 0/2 | 2/2 | 0/2 | 11.2s | — |
| `todomvc` | 0/2 | 0/2 | 2/2 | 32.3s | repeated_action_loop |
| **total** | **0/24** | | | | |

## Failure classes observed

- `repeated_action_loop` — the manager re-issues the same action (types a todo value without submitting; clicks the same element).
- `premature_done` — the actor signals done; the verifier rejects it.
- **Capability gap (all harvested audit tasks):** the runtime's action vocabulary is
  click/type/key/select/scroll/wait/focus/inspect, with no action that evaluates page JS,
  so it cannot set the `window.__bench_finding` every corpus task requires. These runs
  never reach a finding; independent verification reads `finding:null`.

## Verdict-agreement note

The runtime's own verifier and the independent verifier agreed on 20/22 corpus runs and 2/2
TodoMVC runs. The 2 disagreements are `tldraw-three-shape-diagram`, where the runtime's own
verifier reported success against empty structural truth (`labels:[], nodes:[], arrows:0`) —
the exact self-pass the independent verifier exists to catch.
