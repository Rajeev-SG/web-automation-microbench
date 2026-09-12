# Harvested-corpus capability scoreboard (issue #27)

Harnesses: BrowserSkill, agent-browser, browser-relay, cdp-browser, raw-playwright. Tasks: 11 harvested browser tasks. Runs: 99. Model: `z-ai/glm-5.3-flash`.

Cells are `passes/reps` from each task's own declarative pass rule. Read the per-rep JSON beside this file for evidence; nothing is retried away and no failure is hidden.

| Harness | allbirds-uk-add-to-cart-tag-check | chanel-gb-pdp-tag-inspection | gymshark-uk-add-to-cart-tag-check | porsche-uk-script-inventory | porsche-uk-tag-inspection | puma-uk-script-inventory | puma-uk-seo-metadata-audit | puma-uk-tag-inspection | rajeevg-crawlability-audit | rajeevg-seo-metadata-audit | tldraw-three-shape-diagram | Passes | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BrowserSkill | 0/1 | 0/1 | 0/1 | 1/1 | 1/1 | 0/1 | 0/1 | 0/1 | 0/1 | 0/1 | 0/1 | 2/11 | promote |
| agent-browser | 0/1 | 0/1 | 0/1 | 1/1 | 1/1 | 1/1 | 0/1 | 1/1 | 1/1 | 1/1 | 0/1 | 6/11 | promote |
| browser-relay | 0/3 | 2/3 | 0/3 | 3/3 | 3/3 | 3/3 | 1/3 | 3/3 | 3/3 | 3/3 | 1/3 | 22/33 | promote |
| cdp-browser | 0/1 | 0/1 | 1/1 | 1/1 | 0/1 | 1/1 | 0/1 | 1/1 | 1/1 | 1/1 | 0/1 | 6/11 | promote |
| raw-playwright | 0/3 | 0/3 | 0/3 | 2/3 | 3/3 | 3/3 | 0/3 | 3/3 | 2/3 | 3/3 | 1/3 | 17/33 | promote |

`·` = that harness was not screened on that task.

Pass values are **recomputed from the stored verification with each task's declarative rule**. Runs where that disagrees with the stored value: 3 (listed in the JSON under `stored_vs_recomputed_divergences`).
