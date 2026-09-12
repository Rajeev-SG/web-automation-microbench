# Run 2 evidence (rep 2, scored)

- Tool: visnia-ai/browser-agent 1.0.22 (built dist), runner config: /tmp/vb-bench.yaml (OpenRouter z-ai/glm-5.3-flash, reasoning_effort low, every stage_llm overridden; task_checklist off; semantic-projection defaults otherwise).
- Outcome: completed=true successful=true, 10 executor steps, trajectory 25.558s (wall-clock to CLI exit 33s incl. browser teardown).
- Final state observed in last-step projection: Active view — list with "Review invoice", "1 item left", Active link present; completed todo hidden; Clear completed untouched.
- Tokens (tokenUsage artifact totals): input 49,844 (cached 18,112), output 1,469 (non-reasoning 1,070 + reasoning 399).
- Artifacts here: 2-steps.jsonl (redacted step transcript: 10 executor steps + 3 stage LLM invocations: dataExtraction x2, verifySuccess), 2-token-usage.json (raw token usage artifact).
- Rep 1 (23:18 run, console-observed only; steps.jsonl was overwritten by rep 2's run): completed=true successful=true, 8 executor steps, trajectory 23.155s, tokens input 36,299 (cached 8,256), output 1,243 (gen time 1,754ms). Final projection identical final-state (Review invoice / 1 item left). Token-usage artifact for rep 1 was also overwritten (rep 2 totals above).
- Provider attribution: not recorded per call by the tool (events carry provider only as "openrouter"); no explicit provider.sort pass-through — default routing.
