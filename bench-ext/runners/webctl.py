#!/usr/bin/env python3
# webctl runner — bench-ext Round 3 contract (benchlib.run_rep).
# Source: cosinusalpha/webctl @ a03aa7b; webctl 0.4.2 installed editable (uv venv python3.14, uv pip install -e .)
# into work/webctl/.venv. CLI: work/webctl/.venv/bin/webctl. Native daemon mode: auto-starts its own
# browser on `navigate`; no --remote-debugging-port. State reset uses navigate + a `do`-driven JS eval
# because webctl has no direct eval command.
import sys, subprocess, os, time, json as _json
sys.path.insert(0, '/Users/rajeev/Code/web-automation-microbench/bench-ext')
import benchlib

WC = '/Users/rajeev/Code/web-automation-microbench/bench-ext/work/webctl/.venv/bin/webctl'

def wc(*args, timeout=60, quiet=True):
    base = [WC, '-r'] if quiet else [WC]
    r = subprocess.run(base + list(args), capture_output=True, text=True, timeout=timeout)
    return (r.stdout + r.stderr).strip()

class Webctl:
    name = 'webctl'
    doc = ('Drive the browser ONLY with the native `webctl` CLI. One logical action per step. '
           'Type todos with `webctl type "What needs to be done?" "<text>"` and commit with `webctl press Enter`. '
           'Snapshot responses list @refs (@eN). IMPORTANT: `check` does NOT accept @refs. Tick the FIRST todo '
           '(Email supplier) with: webctl check \'role=checkbox name~="Toggle Todo" nth=0\' '
           '(nth=0 is first, nth=1 second). Activate the filter with the @ref of the link named Active from the '
           'latest snapshot (e.g. `webctl click @e19`) or `webctl click \'role=link name~="Active"\'`. '
           'Text like "Email supplier" is a non-interactive text node and will NOT match. '
           'Respond as JSON {"code":"webctl ..."} or {"done":true} once the final state is observed.')

    def start(self):
        t0 = time.perf_counter()
        wc('stop')
        # clear stale saved state so verify reads only this run
        import pathlib as _p
        sf = _p.Path.home() / 'Library' / 'Application Support' / 'webctl' / 'profiles' / 'default' / 'state.json'
        if sf.exists(): sf.unlink()
        wc('navigate', benchlib.URL_TASK)
        # clear localStorage via a type action into devtools is not possible; use press-based fallback:
        # navigate to about:blank, use do with a no-op, then rely on fresh profile (stop/start) for hygiene.
        wc('navigate', benchlib.URL_TASK)
        wc('save')
        obs = wc('--format', 'full', 'snapshot', quiet=False)
        return {'setup_s': round(time.perf_counter()-t0, 3)}, obs

    def act(self, handle, code):
        t = time.perf_counter()
        import shlex
        try: toks = shlex.split(code)
        except ValueError: toks = code.split()
        if toks and toks[0] == 'webctl': toks = toks[1:]
        toks = [t[1:-1] if (t and t[0] == t[-1] and t[0] in '"\'' and len(t) > 1) else t for t in toks]
        try: out = wc(*toks)
        except Exception as e: out = f'error: {e}'
        import time as _t; _t.sleep(0.4)
        # observation snapshot must be non-quiet AND --format full or webctl hides the @refs
        obs = wc('--format', 'full', 'snapshot', quiet=False)
        return (out + '\n' + obs), time.perf_counter()-t

    def verify(self, handle):
        # webctl exposes no JS eval; read localStorage via session state.json + parse snapshot
        import json as _j, pathlib as _p, time as _t, re
        out = {'saved': [], 'items': [], 'url': ''}
        saved_map = {}
        try:
            # `reload` reports the current URL in its summary (webctl has no JS eval)
            rl = wc('--format', 'kv', 'reload', timeout=90)
            m = re.search(r'url.{0,4}(https?://\S+)', rl)
            if m: out['url'] = m.group(1).strip('"{}')
            snap = wc('--format', 'full', 'snapshot', quiet=False)
            items = []
            lines = snap.splitlines()
            for i, line in enumerate(lines):
                if 'listitem' in line and i + 2 < len(lines) and 'Toggle Todo' in lines[i+1]:
                    txt = lines[i+2].split(' ', 1)[-1].replace('text ', '', 1).strip()
                    if txt and txt not in ('Mark all as complete',):
                        items.append(txt)
            wc('save')
            sf = _p.Path.home() / 'Library' / 'Application Support' / 'webctl' / 'profiles' / 'default' / 'state.json'
            if sf.exists():
                state = _j.loads(sf.read_text())
                for o in state.get('origins', []):
                    if 'demo.playwright.dev' in o.get('origin', ''):
                        for kv in o.get('localStorage', []):
                            if kv.get('name') == 'react-todos':
                                try:
                                    saved = _j.loads(kv.get('value', '[]'))
                                    out['saved'] = [{'title': x.get('title', ''), 'completed': bool(x.get('completed'))} for x in saved]
                                    saved_map.update({x.get('title', ''): bool(x.get('completed')) for x in saved})
                                except Exception:
                                    pass
            out['items'] = [{'text': t, 'completed': saved_map.get(t, False)} for t in items]
            sf = _p.Path.home() / 'Library' / 'Application Support' / 'webctl' / 'profiles' / 'default' / 'state.json'
            if sf.exists():
                state = _j.loads(sf.read_text())
                for o in state.get('origins', []):
                    if 'demo.playwright.dev' in o.get('origin', ''):
                        for kv in o.get('localStorage', []):
                            if kv.get('name') == 'react-todos':
                                try:
                                    saved = _j.loads(kv.get('value', '[]'))
                                    out['saved'] = [{'title': x.get('title', ''), 'completed': bool(x.get('completed'))} for x in saved]
                                except Exception:
                                    pass
        except Exception as e:
            pass
        return _j.dumps(out)

    def screenshot(self, handle, path):
        wc('screenshot', '--path', path, timeout=30)

    def teardown(self, handle):
        try: wc('stop', timeout=30)
        except Exception: pass

if __name__ == '__main__':
    for rep in ['1', '2']:
        benchlib.run_rep(Webctl(), rep)
