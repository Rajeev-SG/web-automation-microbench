# Round 3 runner status — after the issue #11 extension fix-up (2026-09-12)

Shared infrastructure: `bench-ext/benchlib.py` (task/verify/model/timer/schema + `run_rep`),
`bench-ext/cft_chrome.py` (Chrome for Testing launcher with `--load-extension`),
`bench-ext/cdp.mjs` (targeted CDP eval / screenshot).

| Contender | Runner | Reps | Median | Status |
|---|---|---|---:|---|
| BrowserSkill | BrowserSkill.py | 2 (2 pass) | 4.1s | DONE |
| browser-relay | browser-relay.py | 2 (2 pass) | 4.3s | DONE |
| browser-control | browser-control.py | 2 (1 pass) | 5.5s | DONE |
| browser-cli | browser-cli.py | 2 (2 pass) | 6.2s | DONE |
| pinchtab | pinchtab.py | 2 (2 pass) | 8.3s | DONE |
| agent-browser | agent-browser.py | 2 (2 pass) | 10.1s | DONE |
| cdp-browser | cdp-browser.py | 2 (2 pass) | 10.7s | DONE |
| jarvis-browser | jarvis-browser.py | 2 (2 pass) | 11.2s | DONE |
| webctl | webctl.py | 2 (2 pass) | 14.5s | DONE |
| agent-chrome-cli | agent-chrome-cli.py | 2 (2 pass) | 17.4s | DONE |
| lightpanda | lightpanda.py | 2 (2 pass) | 22.7s | DONE |
| raw-playwright | raw-playwright.py | 4 (3 pass) | 42.7s | DONE |
| notte | notte.py | 2 (2 pass) | 171.8s | DONE |
| page-agent | page-agent.py | 2 (2 pass) | 25.3s | DONE — PATCHED build (+`send_keys`, MAIN-world dispatch) |
| browser-agent (Taylor-Bayouth) | browser-agent-tb.py | 2 (1 pass) | 200.1s | DONE — stock upstream + OpenRouter adapter |
| sitegeist | — | 0 | — | UNSCOREABLE at 104788c — builds with pi-*@0.73.1 but runtime needs unpublished pi-agent-core 0.85.x |
| browser-agent (visnia-ai) | — | — | — | Round 4 2/2 @ 32.5s — unrelated same-name project (not a rewrite) |

Model config (enforced in `benchlib.openrouter_payload`): model `z-ai/glm-5.3-flash`, temp 0,
reasoning low+excluded, `response_format json_object`, `provider {"sort":"latency"}`. notte and
page-agent ship their own agent runtimes and are timed as a single agent run; page-agent's own LLM
client does not accept latency routing.
