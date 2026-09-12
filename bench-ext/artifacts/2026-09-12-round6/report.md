# Round 6 — remaining high-value contenders (issue #17)

Round 6 closes the remaining tool-coverage gap in the microbench: the Tier A thin-CLI / code-mode
contenders that could plausibly move the fast-path Pareto frontier, the Tier B capability
architectures (vision + autonomous runtimes), one official Chrome DevTools control baseline, and a
brief architecture/relevance decision on the Tier D long tail.

Spec: [`docs/benchmark-spec.md`](../../../docs/benchmark-spec.md). Task: the unchanged TodoMVC
latency microbenchmark. All numbers below come from the per-run JSON in
`bench-ext/artifacts/2026-09-12-round6/results/` and the aggregate `summary.json` next to this file.

## Method and fairness

- **Model, everywhere:** `z-ai/glm-5.3-flash` via OpenRouter, `temperature 0`, reasoning `low`
  (excluded), `response_format json_object`, `provider: {"sort": "latency"}` — enforced by
  `benchlib.openrouter_payload()` for every contender driven by the shared loop.
- **Timing boundary:** timer starts at the first model call and stops at done/failure. Browser
  launch, extension install, state reset and the independent verification/screenshot are outside it.
- **Verification:** the shared `benchlib.VERIFY_JS` + `check_pass` (final URL `#/active`,
  exactly one visible non-completed "Review invoice", and `localStorage["react-todos"]` exactly
  `[{Email supplier,true},{Review invoice,false}]`). The agent's own "done" is never sufficient.
- **Reps:** ≥2 scored reps per runnable contender, and the four near-tie rows in the 8–16s block
  (chrome-cdp-skill, chrome-devtools-mcp, ego-browser, playwright-cli) were promoted to **5 reps** per
  issue #1. HyperAgent has 4 reps (variance 19s → 241s). Failures are kept as failures. Promoting the
  near-tie was not academic: **chrome-cdp-skill screened 2/2 and then scored 3/5** — see §2.
- **Native interfaces preserved:** code-mode tools were allowed to batch; indexed CLIs used indexed
  commands; the vision agent used vision; the autonomous runtimes ran their own loop as a single
  timed run (never flattened into the shared one-command-per-step loop). No contender received a
  TodoMVC adapter, hand-written action sequence, or site-specific shortcut.
- **Routing caveats (recorded, not hidden):** Skyvern and the midscene runtime do not expose an
  OpenRouter `provider.sort` pass-through (default routing); everything else is latency-sorted.
- **Cost:** OpenRouter-reported where the tool reports it (midscene, Skyvern); otherwise exact
  tokens × the latency-sorted provider's published rate (Makora: $0.075/M in, cached ≈ half,
  $0.25/M out).

## 1. Screening table

One row per contender (HyperAgent's two native modes are a single row; see §3). "Calls" = model
calls made by the shared loop (midscene/Skyvern run their own loop, so this is their own step count).

| Contender | Architecture | Pass | Median | Calls | Tokens (in/out) | Cost | Notes |
|---|---|---:|---:|---:|---:|---:|---|
| chrome-cdp-skill | direct CDP / compact snapshot CLI | **3/5** | **11.5s** | 12–15 | ~21.1k / ~323 | ~$0.0083 | Fast; no build/npm deps. **Screened 2/2, dropped to 3/5 on promotion** (see §2) |
| chrome-devtools-mcp | official CDP CLI/MCP (a11y snapshot + uid) | **5/5** | **11.8s** | 7 | ~12.6k / ~89 | ~$0.0048 | Official baseline; full (non-slim) toolset; most consistent new row |
| ego-browser | code-mode / browser-product API | **5/5** | **14.2s** | 8 | ~12.3k / ~99 | ~$0.0048 | Needs its own ego browser app; one nodejs invocation per step |
| playwright-cli | official Playwright CLI + Skills | **5/5** | **14.7s** | 9–10 | ~21.7k / ~113 | ~$0.0083 | Microsoft's CLI path (not MCP); launches its own Chromium |
| browser-act-skills | extension-backed indexed CLI | 2/2 | **18.5s** | 7 | ~6.0k / ~76 | ~$0.0009 | Cheapest per run; free local `chrome` browser, no account |
| hyperagent (perform mode) | Playwright-derived AI SDK | 3/4 | **28.3s** | 5–7 + 6–32 internal | ~20.8k / ~3.4k | ~$0.0096 | Own runtime; rep 1 failed after 4 "no elements found" attempts |
| opencli | extension-backed CLI | **0/2** | 30.4s | 12 | ~20.8k / ~234 | ~$0.0032 | Native `keys Enter` never commits (keyCode 0) — tool defect |
| surf-cli | extension-backed native-host CLI | 2/2 | **31.8s** | 15–21 | ~28.6k / ~519 | ~$0.0046 | Auto-screenshot/rich `read` output raises tokens |
| bb-browser | daemon + direct-browser CLI | **0/2** | 32.7s | 16 | ~12.6k / ~380 | ~$0.0021 | Native `press Enter` never commits (no keyCode) — tool defect |
| midscene | vision-first GUI agent | 2/2 | **33.4s** | 42–44 | ~444k / ~62k | ~$0.074 | Vision screenshots; ~15–20× the token cost of thin CLIs |
| skyvern | autonomous multi-agent runtime | 2/2 | **186.5s** | 5–6 steps | ~29.0k / ~4.2k | ~$0.0055 | Preserved native architecture; not a latency contender |

## 2. Pareto analysis

**Nothing beat BrowserSkill, and no Round 6 row extends the existing fast-path frontier.** Screening
the new rows against the current front (BrowserSkill 4.1s / ~$0.0005, browser-relay 4.3s, browser-cli
6.2s, pinchtab 8.3s / ~$0.0003) on the axes that define it — wall-clock and cost — gives a blunt
result: **every Round 6 contender is dominated by at least one existing row.**

| Round 6 contender | Median | Pass | Cost/run | Dominated by |
|---|---:|---:|---:|---|
| chrome-cdp-skill | 11.5s | **3/5** | ~$0.0083 | BrowserSkill (4.1s, ~$0.0005) |
| chrome-devtools-mcp | 11.8s | **5/5** | ~$0.0048 | BrowserSkill |
| ego-browser | 14.2s | **5/5** | ~$0.0048 | BrowserSkill |
| playwright-cli | 14.7s | **5/5** | ~$0.0083 | BrowserSkill |
| browser-act-skills | 18.5s | 2/2 | ~$0.0009 | pinchtab (8.3s, ~$0.0003) — faster *and* cheaper |
| hyperagent (perform) | 28.3s | 3/4 | ~$0.0096 | BrowserSkill |
| opencli / surf-cli / bb-browser | 30–33s | 0/2, 2/2, 0/2 | ~$0.002–0.005 | BrowserSkill |
| midscene | 33.4s | 2/2 | ~$0.074 | BrowserSkill |
| skyvern | 186.5s | 2/2 | ~$0.0055 | BrowserSkill |

### The promotion result: 2-rep screening overstated reliability

The 8–16s block looked like a near-tie after screening (chrome-cdp-skill 8.8s 2/2, chrome-devtools-mcp
13.1s 2/2, ego-browser 13.7s 2/2, playwright-cli 15.2s 2/2). Promoting all four to **5 reps** resolved
it — and changed the winner:

| Contender | Screen (2 reps) | Promoted (5 reps) | Outcome |
|---|---|---|---|
| chrome-cdp-skill | 8.8s, 2/2 | **11.5s, 3/5** | Regressed. Reps 4–5 ended with the *correct persisted state* (`Email supplier` done, `Review invoice` not) but the wrong live view (URL `#/`, 0 visible items) and the model still said "done". |
| chrome-devtools-mcp | 13.1s, 2/2 | **11.8s, 5/5** | Reliable; fastest **reliable** new row. |
| ego-browser | 13.7s, 2/2 | **14.2s, 5/5** | Reliable. |
| playwright-cli | 15.2s, 2/2 | **14.7s, 5/5** | Reliable. |

So the honest Round 6 conclusion is not "chrome-cdp-skill is the fastest new CLI" but **"the fastest
new CLI is the least reliable, and the best new row is chrome-devtools-mcp (5/5 @ 11.8s)"**. This is a
direct vindication of the issue's warning against reading 2-rep ordering; the remaining 2-rep rows
(browser-act, surf-cli, midscene, skyvern, and the two failures) are screening signals only.

**Is anything cheaper at similar speed/reliability?** No. **browser-act-skills** is the cheapest new row
(~$0.0009) but is 4.5× slower than BrowserSkill and 2.2× slower than pinchtab, which is itself cheaper —
it does not take the cost frontier either. **pinchtab still owns the cost frontier.**

**Is anything materially more reliable for modest cost?** No. Round 6 produced two more hard failures
(opencli, bb-browser) and one reliability regression (chrome-cdp-skill 3/5). The reliability leader
overall remains Magnitude (4/4, vision), though chrome-devtools-mcp's 5/5 on a thin CLI is the best
*fresh* reliability evidence this round.

**Worth keeping anyway (capability, not fast path).** The value of several Round 6 rows is not their
TodoMVC time: midscene (vision on weak/canvas/icon-only DOM), skyvern (long-horizon autonomous
recovery), ego-browser (state-native code-mode), browser-act's advanced modes, and hyperagent's
`page.ai()` autonomous mode are the arms of the capability suite, and TodoMVC deliberately cannot
discriminate them.

**No simplistic total score.** Speed, cost and capability stay separate. On the two hard axes Round 6
was a no-op for the frontier, which is itself the useful result: the thin-CLI family is close to
exhausted, the omission risk the issue worried about did not materialise, and the one new tool that
looked fastest did not survive five reps.

## 3. Architecture classification

| Architecture class | Round 6 members |
|---|---|
| Direct CDP / daemon | chrome-cdp-skill (compact a11y snapshot, no Puppeteer/Playwright), chrome-devtools-mcp (official a11y tree + uid) |
| Extension-backed CLI | browser-act-skills (indexed `state`/`click N`/`input N`), surf-cli (native-messaging socket), opencli (indexed `state`), bb-browser (daemon + direct browser) |
| Code-mode | ego-browser (`ego-browser nodejs` heredoc; agent composes Page ops) |
| Playwright-derived AI SDK | playwright-cli (official Microsoft CLI + Skills path; launched/attached Chromium), hyperagent `page.perform()` (a11y-tree granular actions over Playwright) |
| Vision-first GUI agent | midscene (screenshot-driven `aiAct`) |
| Autonomous multi-agent runtime | skyvern (LLM + CV, multi-step planner/executor), hyperagent `page.ai()` (autonomous/visual mode) |
| Browser / runtime product | ego-browser (ships its own browser app), skyvern (self-hosted server + Postgres) |

Two design lessons this round, both from the failures and the token counts:

1. **The Enter-key commit is the discriminator for React-style inputs.** Four separate tools now
   fail TodoMVC for the *same* reason — a key event synthesised without `keyCode`/`windowsVirtualKeyCode`
   (bb-browser, opencli) or a missing key action entirely (page-agent, Round 5). Any tool that
   claims keyboard support should be probed for `windowsVirtualKeyCode: 13` before it is trusted.
2. **Compact observation beats rich observation.** The 11–18s CLIs return a short indexed snapshot;
   surf-cli's verbose auto-`read`/screenshot behaviour roughly doubles its tokens, and midscene's
   per-step screenshots cost ~100× the thin CLIs.
3. **Two reps cannot measure reliability.** The fastest new contender screened 2/2 at 8.8s and scored
   3/5 once promoted; a "pass" here is a single-bit observation, so a 2/2 is weak evidence (§2).

## 4. Exclusions / blocked attempts

**No contender needed an exclusion file this round — all eleven runnable contenders were scored**
(including both genuine 0/2 failures, which are kept in the dataset as failures, not excluded).

Two are **scored tool failures**, not setup problems:

- **opencli 0/2** (commit `8271afc`, npm `@jackwener/opencli` 1.8.7, extension v1.0.24).
  Command attempted: `opencli browser <session> fill .new-todo "Email supplier"` → `keys Enter`.
  Result: `{filled:true, verified:true, actual:"Email supplier"}` then `Pressed: Enter`, but
  `document.querySelectorAll('.todo-list li').length === 0` and `saved: []` on every attempt.
  Root cause **confirmed by direct probe**: OpenCLI's `keys` dispatches a synthetic `KeyboardEvent`
  with `keyCode: 0, which: 0` (observed from an in-page keydown listener); the identical dispatch
  with `keyCode: 13, which: 13` commits the todo correctly. **Upstream defect** in
  `src/browser/dom-helpers.ts` (`pressKeyJs`) — it omits `keyCode`/`which`.
- **bb-browser 0/2** (commit `7975dc7`, npm 0.14.2). Command attempted: `fill @1 "Email supplier"`
  then `press Enter`. Its `press` dispatches `Input.dispatchKeyEvent` **without**
  `windowsVirtualKeyCode`, so React sees `keyCode 0`; reproduced deterministically outside the
  runner (value stays set, `saved: null`). Its `fill`/`type` also set the DOM value without
  updating React state. **Upstream defect** in `packages/daemon/src/command-dispatch.ts`.

Both should be retried after an upstream fix; the failure is one line of key-event plumbing, not an
architectural limit. (Evidence: `results/{1,2}-{opencli,bb-browser}.json`.)

## 5. Tier C — official Chrome DevTools control baseline

**chrome-devtools-mcp / CLI 1.9.0** (commit `d9a8cb6`) is scored as the single official baseline:
**5/5, 11.8s median, ~12.6k/~89 tokens, ~$0.0048** using the full (non-slim) official CLI against
Chrome for Testing — the best reliability of any Round 6 row and the fastest reliable new arrival. The low-schema `--slim` mode was evaluated and rejected for the row: it exposes
only `navigate`/`evaluate`/`screenshot` — no snapshot/click/fill — so it cannot complete a generic
agent task and would not be a meaningful baseline. This gives the benchmark one modern official
control surface without multiplying official-protocol variants.

## 6. Tier D — architecture/relevance decisions (review only; none promoted)

| Candidate | Decision | Why |
|---|---|---|
| nanobrowser | Not promoted | Chrome-extension multi-agent runtime configured through its own sidepanel UI; same class as page-agent, which is already represented. No new observation/action architecture, and its config surface makes a fair CLI-level row impractical. |
| browserable | Not promoted | Docker-Compose agent framework (Playwright-derived) plus a hosted remote-browser API; the same broad family as Stagehand/Magnitude/BrowserCode, already covered. No plausible Pareto improvement on the fast path. |
| BrowserOS | Not promoted | A complete Chromium fork ("the missing browser for AI agents") — a browser/runtime product, not a control layer. Benchmarking it would measure a different product category, and it exposes no comparable agent CLI to time. |
| steel-browser / pi-steel | Not promoted | Cloud browser infrastructure plus a separate agent; the browser is hosted, and there is no directly comparable local agent-control loop to score. |

Per the issue: none of these adds a capability missing from the Tier A/B set, and none has public
evidence making a Pareto improvement plausible, so they are documented and left out.

## 7. Browser Harness / upstream relationship (README correction)

Round 2 labelled the Browser Harness row's repo as **"in-repo (artifacts/2026-09-11)"**, which is
ambiguous. Verified this round:

- The benchmarked implementation is the **upstream `browser-harness` PyPI package**
  ([browser-use/browser-harness](https://github.com/browser-use/browser-harness)), installed as a
  CLI via `uv tool install browser-harness` and driven over its own stdin-code interface. Its
  metadata homepage/repository is the upstream GitHub project and it ships the same helpers the
  Round 2 runner used (`trusted_click`, `type_text`, `press_key`, `js`, `new_tab`, `wait_for_load`).
- **No modified or vendored harness source was used.** The "in-repo" part was only the *runner*
  (`artifacts/2026-09-11/bench-py.py`), not the tool.
- Installed version today: **0.1.13** (`~/.local/share/uv/tools/browser-harness`, receipt has no
  pin, so Round 2 used the latest-at-install on 2026-09-11).

The README row is repointed at the upstream repo with the version documented, so the row is no
longer read as a bespoke in-house harness.

## 8. Reproducibility

Every runner lives in `bench-ext/runners/<name>.py` and carries its own version/commit, install
commands, browser connection mode, and gotchas in its header. Key setup per contender:

- **chrome-cdp-skill** — `git clone` (commit `ffea76a`); no build/npm; CFT on port 9301 with
  `CDP_PORT_FILE` synthesised (CFT 153 does not write it). Native CLI verbs only.
- **chrome-devtools-mcp** — `npm i -g chrome-devtools-mcp@1.9.0`; CFT on 9309; full toolset.
- **ego-browser** — ego lite app 0.5.0.32 (commit `d01be93`) supplying `ego-browser`; TaskSpace
  `bench-todomvc`, one `ego-browser nodejs` invocation per step.
- **playwright-cli** — `npm i -g @playwright/cli` → 0.1.19 (commit `655530f`); the CLI launches and
  manages its own Chromium (`playwright-cli open`); `attach --cdp` daemon exits 1 here, so the
  tool's default path was used. Snapshot `eN` refs preserved.
- **browser-act-skills** — `uv tool install browser-act-cli --python 3.12` + one-time local
  `chrome` browser record; free/local only, no account.
- **hyperagent** — `npm install && npm run build` of the repo (commit `a7ec1f4`, pkg 1.1.2); a
  Node driver holds the HyperAgent instance and executes one `page.perform()` per command; a
  benchmark-side `fetch` wrapper injects `provider.sort=latency` and tallies its internal LLM usage
  (HyperAgent exposes no token telemetry). No upstream source modified.
- **opencli** — `npm i -g @jackwener/opencli` (1.8.7) + extension via CFT `--load-extension` on 9305.
- **surf-cli** — `npm install && npm run build` (commit `56faa5a`, v2.19.0), extension loaded in CFT
  on 9303, `scripts/install-native-host.cjs`, plus the native-messaging manifest copied into
  `Google Chrome for Testing`'s `NativeMessagingHosts` dir. One 1-line local patch:
  `native/socket-path.cjs` honours `SURF_DEFAULT_SOCKET` so parallel instances don't fight over
  `/tmp/surf.sock`. Adapter strips surf's `[surf tab=…]` status banner from verify output only.
- **bb-browser** — `npm install -g bb-browser` (0.14.2); CFT on 9302 via `BB_BROWSER_CDP_URL`.
- **midscene** — `npm i @midscene/web puppeteer tsx`; wired to OpenRouter GLM purely by env
  (`MIDSCENE_MODEL_BASE_URL`, `MIDSCENE_MODEL_NAME`, `MIDSCENE_MODEL_FAMILY=glm-v`,
  `MIDSCENE_MODEL_REASONING_ENABLED=false`) with no midscene internals patched. Gotcha: `OPENAI_API_KEY`
  must also be exported or the SDK client constructor fails.
- **skyvern** — Python 3.12 uv venv + `pip install -e ".[all]" ".[server]"`; Postgres 14 container
  (`skyvern-postgres` on 55432 — the SQLite default is broken upstream: migrations emit Postgres-only
  `'[]'::jsonb` and die on `unrecognized token: ":"`); `skyvern quickstart --database-string … --server-only`;
  `skyvern run server` on 127.0.0.1:8000; `ENABLE_OPENROUTER=true`, `LLM_KEY=OPENROUTER`,
  `OPENROUTER_MODEL=z-ai/glm-5.3-flash`; CFT on 9311 attached via `browser_address`. Tokens/cost read
  from Skyvern's own `steps` table.

Reproduce any row with:
`OPENROUTER_API_KEY=$(security find-generic-password -s codex-openrouter -w) python3 runners/<name>.py <rep>`
(the Skyvern runner additionally needs its server + Postgres container running, and the midscene
runner needs `OPENAI_API_KEY` set to the same key).

## 9. Artifacts

- `results/{1,2}-<contender>.json` + `.png` for all eleven contenders (HyperAgent also has 3–4).
- `summary.json` — the aggregate used for the README rows (`runners/make_round6_summary.py`).
- Round-6 worker brief: `bench-ext/docs/ROUND6-BRIEF.md`.

## 10. Stop condition / admission rule

Round 6 completes Tier A and the justified Tier B/C coverage, so the benchmark now adopts the
issue's admission rule:

> A new browser automation tool is only added when it demonstrates a genuinely different
> architecture, credible external evidence of a Pareto improvement, or a capability absent from the
> current suite.

The long tail (every remaining Playwright/Puppeteer MCP, thin wrapper, abandoned PoC, site-specific
scraper, or hosted-browser product) is explicitly out of scope from here.
