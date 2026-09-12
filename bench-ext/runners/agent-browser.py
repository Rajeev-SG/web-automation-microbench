#!/usr/bin/env python3
# agent-browser runner — bench-ext Round 3 contract (benchlib.run_rep).
# Source: vercel-labs/agent-browser @ 8c15ff9; npm agent-browser@0.37.1 (darwin-arm64 native binary
# copied from npm tarball into work/agent-browser/bin/); `agent-browser install` -> Chrome for Testing 153.0.8010.36
# at ~/.agent-browser/browsers/chrome-153.0.8010.36. Runs its own daemon/browser (native mode), no --remote-debugging-port.
import sys, subprocess, os, json, time
sys.path.insert(0, '/Users/rajeev/Code/web-automation-microbench/bench-ext')
import benchlib

BIN = '/Users/rajeev/Code/web-automation-microbench/bench-ext/work/agent-browser/bin/agent-browser-darwin-arm64'
SESSION = 'bench'

def ab(*args, timeout=45):
    r = subprocess.run([BIN, '--session', SESSION] + list(args), capture_output=True, text=True, timeout=timeout)
    return (r.stdout + r.stderr).strip()

class AgentBrowser:
    name = 'agent-browser'
    doc = ('Drive the browser ONLY with the native `agent-browser` CLI. One logical action per step, '
           'and the code string MUST be EXACTLY ONE CLI invocation: `fill <selector> "<text>"` fills the '
           'new-todo field (does NOT commit), then `press Enter` commits the todo; `click <selector-or-@ref>`, '
           '`snapshot`, `get text`, `eval`. Never chain with && or ; and do not wrap todo text in quotes '
           'beyond the CLI syntax. IMPORTANT: to tick a todo checkbox or open the Active filter, first run '
           '`snapshot`, then click the printed @ref (e.g. `click @e7` for the checkbox next to the todo label, '
           '`@eN` for the "Active" link). CSS .toggle selectors and text= links are unreliable here. '
           'Example: fill .new-todo "Email supplier". Respond as JSON '
           '{"code":"agent-browser ..."} for each step, and {"done":true} IMMEDIATELY once the final state is '
           'observed (items, completed flags, Active filter). Respond ONLY with strict JSON; no extra keys, '
           'no markdown, no prose. Never send None or empty code.')

    def start(self):
        t0 = time.perf_counter()
        self.h = 'agent-browser-bench'
        ab('close', '--all')
        # state reset: fresh session page, clear localStorage, reload task URL
        ab('open', benchlib.URL_TASK)
        ab('eval', "localStorage.removeItem('react-todos')")
        ab('open', benchlib.URL_TASK)
        obs = ab('eval', benchlib.OBS_JS)
        return {'setup_s': round(time.perf_counter()-t0, 3)}, obs

    def act(self, handle, code):
        t = time.perf_counter()
        # one logical action = one CLI invocation; strip any agent-browser prefix and run via the native binary
        # thin native invocation: pass exactly what the model sends, after unquoting
        # wrapped arguments (the model sometimes double-quotes todo text).
        import shlex
        try:
            toks = shlex.split(code)
        except ValueError:
            toks = code.split()
        if toks and toks[0] in ('agent-browser', 'ab'):
            toks = toks[1:]
        # unquote arguments that are themselves quoted twice (e.g. '"Email supplier"')
        toks = [t.strip('"') if (t.startswith('"') and t.endswith('"') and len(t) > 1) else t for t in toks]
        out = ab(*toks, timeout=60)
        obs = ab('eval', benchlib.OBS_JS, timeout=60)
        return out + '\n' + obs, time.perf_counter()-t
        # model may chain two commands with && — run each on its own line, one CLI invocation each
        import shlex
        toks = code.split()[1:]
        out = ab(*toks, timeout=60) if not any(ch in code for ch in ['&&', ';']) else ''
        if not out:
            # split on && for simple two-command chains
            for part in code.split('&&'):
                toks = part.strip().split()[1:]
                out += ab(*toks, timeout=60) + '\n'
        obs = ab('eval', benchlib.OBS_JS, timeout=60)
        return out + obs, time.perf_counter()-t

    def verify(self, handle):
        return ab('eval', benchlib.VERIFY_JS, timeout=60)

    def screenshot(self, handle, path):
        ab('screenshot', path, timeout=30)

    def teardown(self, handle):
        try: ab('close', '--all', timeout=15)
        except Exception: pass

if __name__ == '__main__':
    for rep in benchlib.reps_from_argv(sys.argv[1:]):
        benchlib.run_rep(AgentBrowser(), rep)
