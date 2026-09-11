# Web automation benchmark — extension round 2026-09-13

One new contender scored on the standard TodoMVC task (spec: docs/benchmark-spec.md):
**browser-agent** from [visnia-ai/browser-agent](https://github.com/visnia-ai/browser-agent)
(v1.0.22). This is a different tool from the Round 3 `browser-agent`
([Taylor-Bayouth/browser-agent](https://github.com/Taylor-Bayouth/browser-agent)),
which was excluded after its custom OpenRouter adapter failed to wire tool calls.
The visnia fork is a rewrite with first-class provider support (including OpenRouter)
and a YAML CLI config, so it was scored fresh under the same contract.

## Configuration

- Model: `z-ai/glm-5.3-flash` via OpenRouter for every stage (`findTargetURL`,
  `createChecklist`, `runAgent`, `dataExtraction`, `verifySuccess`),
  `reasoning_effort: low`, temperature unset (framework default), YAML config:
  `task_checklist: false`, semantic-projection defaults otherwise,
  `headless: true`, `max_steps: 40`, one task per rep, fresh seeded Chrome profile
  per rep (localStorage cleared implicitly by fresh profile).
- Provider routing: **no explicit `provider.sort: latency` pass-through available**
  in the visnia CLI config (only `openrouter_provider` allow-list is supported, which
  pins a single provider and changes routing semantics). Runs therefore used default
  OpenRouter routing. Provider attribution per call was not surfaced by the tool.
- Task text: benchlib.TASK verbatim (Round 3 shared instruction).

## Scored results

| Rep | Pass | Wall (first model call → CLI exit) | Agent trajectory | Executor steps | Model calls* | Tokens in (cached) | Tokens out |
|---|---|---|---|---:|---:|---|---|
| 1 | pass | 32.0s | 23.2s | 8 | 8 | 36,299 (8,256) | 1,243 |
| 2 | pass | 33.0s | 25.6s | 10 | 13 | 49,844 (18,112) | 1,469 |

\* model_calls includes executor steps plus the tool's own extra stage calls
(2× dataExtraction + 1× verifySuccess in rep 2). Aggregate token counts come from
the tool's own token-usage artifact (2-token-usage.json) and rep-1 console output;
per-step transcripts live in 2-steps.jsonl (rep 1's raw steps file was overwritten
by the rep-2 run, so only its console totals are retained — noted in each JSON).

Cost estimate at latency-sorted published rates (Makora $0.075/M in, $0.25/M out,
cached ≈ half): rep 1 ≈ $0.0031, rep 2 ≈ $0.0041 — roughly 6× the Browser Harness
row and ~5× cdp-browser, driven by a large fixed system prompt (~3.6–4.9k tokens
per step) plus two extra stage LLM calls per run.

## Verdict (this round)

- **Reliable but heavyweight.** 2/2 pass, median 32.5s — reliable but ~3× slower
  than Browser Harness (9.9s), cdp-browser (10.7s), and jarvis-browser (11.2s),
  and ~20× more tokens per run. Its one action-per-turn semantic-projection loop
  plus mandatory extract_data/return_results barrier adds real steps and tokens.
- Not competitive on this simple task: dominated by Browser Harness on speed,
  tokens, and cost, with no capability gain for a plain DOM form. The ref-based
  projection approach may earn its cost on visually messy or detection-sensitive
  sites (the tool's stated niche), which this microbench does not test.

## Artifacts

- `results/1-browser-agent.json`, `results/2-browser-agent.json` (canonical run JSONs)
- `results/2-steps.jsonl` (redacted 10-step rep-2 transcript),
  `results/2-token-usage.json` (raw token-usage artifact),
  `results/2-run-summary.md` (rep-2 evidence + rep-1 console totals)
- Rep-1 PNG screenshots were not captured (tool's own screenshots were not piped
  to the runner); final states were verified from the step projections instead.
