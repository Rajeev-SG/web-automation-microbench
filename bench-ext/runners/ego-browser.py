#!/usr/bin/env python3
# Round 6 runner: ego-browser (ego-lite) — code-mode TaskSpace/Page API via `ego-browser nodejs` heredocs.
# Source: bench-ext/work/ego-lite commit d01be93; ego lite app 0.5.0.32 provides the native `ego-browser` CLI.
# Contenders must use their own interface: each act() runs ONE Node script that may compose multiple
# Page ops (code-mode preserved, per skill: multi-op scripts in one invocation). Local CDP override is
# impossible from the CLI binary itself (bundled), so the runner uses the installed app's own port and
# session state (space "bench-todomvc" persists between steps, like any other ego-browser agent).
import sys, json, subprocess, os, time, pathlib
sys.path.insert(0, '/Users/rajeev/Code/web-automation-microbench/bench-ext')
import benchlib

benchlib.RES = pathlib.Path('/Users/rajeev/Code/web-automation-microbench/bench-ext/artifacts/2026-09-14/results')
benchlib.RES.mkdir(parents=True, exist_ok=True)

EGO = os.path.expanduser('~/.local/bin/ego-browser')
MJS = '/tmp/ego-act.mjs'

ACT_MJS = '''\
import { readFileSync } from 'node:fs';
const task = await taskSpace("bench-todomvc");
const page = task.page("p1");
const spec = JSON.parse(readFileSync('/tmp/ego-act.json','utf8'));
let out = '';
const code = spec.code;
if (code.startsWith('goto ')) await page.goto(code.slice(5).trim());
else if (code.startsWith('reload')) await page.reload();
else if (code.startsWith('fill ')) { const rest = code.slice(5); const m = rest.match(/^\\s*(\\S+)\\s+(".*")\\s*$/); if (!m) throw new Error('fill parse fail'); await page.fill(m[1], JSON.parse(m[2])); }
else if (code.startsWith('click ')) await page.click(code.slice(6).trim());
else if (code.startsWith('press ')) { const parts = code.slice(6).trim().split(/\\s+/); await page.press(parts[0], parts.slice(1).join(' ')); }
else if (code.startsWith('wait ')) { await page.waitForFunction(code.slice(5).trim(), undefined, {timeout: 8000}); }
else if (code.startsWith('eval ')) { out = await page.evaluate(code.slice(5).trim()); }
else throw new Error('unsupported: ' + code.slice(0,80));
console.log('OUT:' + JSON.stringify(out));
'''

class EgoBrowser:
    name = 'ego-browser'
    doc = ('You drive a real Chrome via the ego-browser Node API (official skill interface). '
           'Each step output JSON {"code":"<command>"} where <command> is ONE logical op for the '
           'adapter to run inside one `ego-browser nodejs` heredoc against the SAME TaskSpace/page: '
           'goto <url>; reload; fill <selector> "text"; click <selector>; press <key>; wait <js-expr> '
           '(waitForFunction); eval <js>. Selectors: CSS, or @N refs from the last snapshot. '
           'Use `eval` with an IIFE returning JSON for observation (e.g. eval (() => JSON.stringify({...}))()). '
           'One logical UI action per step (fill+press Enter to commit a todo counts as 2 commands, '
           'or compose them yourself if you prefer multiple in one string). Respond {"done":true} '
           'when the latest observation already shows the final state. Strict JSON only.')

    def start(self):
        t0 = time.perf_counter()
        pathlib.Path(MJS).write_text(ACT_MJS)
        self._run('goto ' + benchlib.URL_TASK)
        self._run('wait () => document.readyState === "complete"')
        self._run('eval (() => { localStorage.removeItem("react-todos"); location.reload(); })()')
        time.sleep(2.0)
        obs = self._run('eval ' + benchlib.OBS_JS)
        return {'setup_s': round(time.perf_counter() - t0, 3)}, obs

    def _run(self, code, timeout=60):
        pathlib.Path('/tmp/ego-act.json').write_text(json.dumps({'mode':'act','code':code}))
        p = subprocess.run([EGO, 'nodejs'], stdin=open(MJS), capture_output=True, text=True, timeout=timeout,
                           env={**os.environ, 'PATH': os.path.expanduser('~/.local/bin') + ':' + os.environ['PATH']})
        out = (p.stdout + p.stderr).strip()
        for line in out.splitlines():
            if line.startswith('OUT:'):
                raw = line[4:]
                try: return json.loads(raw)
                except Exception: return raw
        return out

    def act(self, handle, code):
        try:
            out = self._run(code)
        except Exception as e:
            out = f'error: {e}'
        obs = self._run('eval ' + benchlib.OBS_JS)
        return (out or '') + '\n' + obs, 0.0

    def verify(self, handle):
        return self._run('eval ' + benchlib.VERIFY_JS)

    def screenshot(self, handle, path):
        try:
            script = f'''
import {{ readFileSync }} from 'node:fs';
const task = await taskSpace("bench-todomvc");
const page = task.page("p1");
await page.screenshot({{ path: {json.dumps(path)} }});
'''
            pathlib.Path('/tmp/ego-shot-run.mjs').write_text(script)
            subprocess.run([EGO, 'nodejs'], stdin=open('/tmp/ego-shot-run.mjs'),
                           capture_output=True, text=True, timeout=30,
                           env={**os.environ, 'PATH': os.path.expanduser('~/.local/bin') + ':' + os.environ['PATH']})
        except Exception as e:
            print(f'screenshot error: {e}', file=sys.stderr)

    def teardown(self, handle):
        try:
            subprocess.run([EGO, 'nodejs'], input='const t = await taskSpace("bench-todomvc"); await t.finish({keep:true});',
                           capture_output=True, text=True, timeout=30,
                           env={**os.environ, 'PATH': os.path.expanduser('~/.local/bin') + ':' + os.environ['PATH']})
        except Exception:
            pass

if __name__ == '__main__':
    reps = sys.argv[1:] or ['1', '2']
    for rep in reps:
        benchlib.run_rep(EgoBrowser(), rep, max_steps=12)
