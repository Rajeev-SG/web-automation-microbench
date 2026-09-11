#!/usr/bin/env python3
# browser-control runner — bench-ext Round 3 contract (benchlib.run_rep).
# Source: keon/browser-control @ b352a1a; cargo 1.98.0 (Homebrew) build --release of
# work/browser-control (crate browser-control-cli, Cargo.lock pinned). Binary: target/release/browser-control.
# Launches its own Chrome on port 9242 via `launch` (native mode), BROWSER_CONTROL_CDP_URL set for commands.
import sys, subprocess, os, time
sys.path.insert(0, '/Users/rajeev/Code/web-automation-microbench/bench-ext')
import benchlib

BC = '/Users/rajeev/Code/web-automation-microbench/bench-ext/work/browser-control/target/release/browser-control'
WS = '/tmp/bc-ws-bench'
ENV = dict(os.environ, BROWSER_CONTROL_CDP_URL='http://127.0.0.1:9242')

WS='/tmp/bc-ws-bench'

def bc(*args, timeout=45, ws=None):
    r = subprocess.run([BC] + list(args), capture_output=True, text=True, timeout=timeout, cwd=(ws or WS), env=ENV)
    return (r.stdout + r.stderr).strip()

class BrowserControl:
    name = 'browser-control'
    doc = ('Drive the browser ONLY with the native `browser-control` CLI via shell commands. '
           'One logical action per step. Refs (@e1...) are only valid for the immediately preceding '
           '`snapshot` output - take `snapshot` before every action if unsure. '
           'Committing a todo = fill the textbox @ref then `press Enter`. '
           'Click the Active filter with `click "a[href=\'#/active\']"`. '
           'Respond as JSON {"code":"browser-control ..."} or {"done":true}.')

    def start(self):
        t0 = time.perf_counter()
        # fresh profile each rep: unique workspace dir keeps localStorage empty
        self.ws = f"/tmp/bc-ws-rep-{getattr(self, 'rep', 'x')}"
        os.makedirs(self.ws, exist_ok=True)
        bc('stop', ws=self.ws)
        r = bc('launch', benchlib.URL_TASK, '--port', '9242', ws=self.ws)
        obs = bc('eval', benchlib.OBS_JS, timeout=60, ws=self.ws)
        if not obs.lstrip().startswith('{'):
            import time as _t; _t.sleep(1)
            bc('open', benchlib.URL_TASK, ws=self.ws)
            obs = bc('eval', benchlib.OBS_JS, timeout=60, ws=self.ws)
        return {'setup_s': round(time.perf_counter()-t0, 3), 'launch_out': r[:200]}, obs

    def act(self, handle, code):
        t = time.perf_counter()
        # run the model's CLI string natively; never eval it as JS
        import shlex
        try: toks = shlex.split(code)
        except ValueError: toks = code.split()
        if toks and toks[0] in ('browser-control', 'bc'): toks = toks[1:]
        toks = [t[1:-1] if (t and t[0] == t[-1] and t[0] in '\"' and len(t) > 1) else t for t in toks]
        try: out = bc(*toks, timeout=60, ws=self.ws)
        except Exception as e: out = f'error: {e}'
        obs = bc('eval', benchlib.OBS_JS, timeout=60, ws=self.ws)
        return (out + '\n' + obs), time.perf_counter()-t

    def verify(self, handle):
        return bc('eval', benchlib.VERIFY_JS, timeout=60, ws=self.ws)

    def screenshot(self, handle, path):
        bc('screenshot', path, timeout=30, ws=self.ws)

    def teardown(self, handle):
        try: bc('stop', timeout=15, ws=self.ws)
        except Exception: pass

if __name__ == '__main__':
    for rep in ['1', '2']:
        a = BrowserControl(); a.rep = rep
        benchlib.run_rep(a, rep)
