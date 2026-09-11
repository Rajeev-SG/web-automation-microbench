# Round 3 runner status

| Contender | Owner | Runner | Reps | Status |
|---|---|---|---|---|
| raw-playwright | main | raw-playwright.py | 4 (3 pass) | DONE |
| pinchtab | main | pinchtab.py | 6 (0 pass) | scored reps exhausted, need final verdict + report |
| agent-browser | A1 | - | 0 | in progress |
| browser-control | A1 | - | 0 | in progress |
| cdp-browser | A1 | - | 0 | in progress |
| webctl | A1 | - | 0 | in progress |
| browser-agent | A2 | - | 0 | in progress |
| BrowserSkill | A2 | - | 0 | in progress |
| browser-relay | A2 | - | 0 | in progress |
| browser-cli | A2 | - | 0 | in progress |
| agent-chrome-cli | A3 | agent-chrome-cli.py | 0 | in progress |
| jarvis-browser | A3 | jarvis-browser.py | 0 | in progress |
| page-agent | A3 | page-agent.py (draft) | 0 | in progress |
| lightpanda | A3 | - | 0 | in progress |
| sitegeist | main | - | 0 | queued |
| notte | main | - | 0 | queued |

## Model-routing notes (for report)
- OpenRouter providers observed so far: Together (pinchtab rep4), Makora (raw-playwright). Record provider per call in each JSON (`events[].provider`).
- benchlib enforces: model z-ai/glm-5.3-flash, temp 0, reasoning low+excluded, response_format json_object, provider {"sort":"latency"}.
