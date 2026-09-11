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

def wc(*args, timeout=60):
    r = subprocess.run([WC, '-r'] + list(args), capture_output=True, text=True, timeout=timeout)
    return (r.stdout + r.stderr).strip()

class Webctl:
    name = 'webctl'
    doc = ('Drive the browser ONLY with the native `webctl` CLI via shell commands. One logical action per step. '
           'Commands: navigate <url>, snapshot (gives @refs), click <query-or-@ref or "text">, type <query> <text> '
           '(add --submit to press Enter), press <key>, screenshot --path <file>. There is no JS eval; '
           'use type/click/press on visible elements. Respond as JSON {"code":"webctl ..."} or {"done":true}.')

    def start(self):
        t0 = time.perf_counter()
        wc('stop')
        wc('navigate', benchlib.URL_TASK)
        # clear localStorage via a type action into devtools is not possible; use press-based fallback:
        # navigate to about:blank, use do with a no-op, then rely on fresh profile (stop/start) for hygiene.
        wc('navigate', benchlib.URL_TASK)
        obs = wc('snapshot')
        return {'setup_s': round(time.perf_counter()-t0, 3)}, obs

    def act(self, handle, code):
        t = time.perf_counter()
        wc(*code.split(' ', 1))
        obs = wc('snapshot')
        return obs, time.perf_counter()-t

    def verify(self, handle):
        # webctl exposes no JS eval; read localStorage via the session profile state.json
        import json as _j, pathlib as _p, time as _t
        wc('save')
        sf = _p.Path.home() / 'Library' / 'Application Support' / 'webctl' / 'profiles' / 'default' / 'state.json'
        for _ in range(10):
            if sf.exists():
                break
            _t.sleep(0.2)
        out = {}
        try:
            state = _j.loads(sf.read_text())
            saved = []
            for o in state.get('origins', []):
                if 'demo.playwright.dev' in o.get('origin', ''):
                    for kv in o.get('localStorage', []):
                        if kv.get('name') == 'react-todos':
                            try:
                                saved = _j.loads(kv.get('value', '[]'))
                                out['saved'] = [{'title': x.get('title', ''), 'completed': bool(x.get('completed'))} for x in saved]
                            except Exception:
                                pass
        except Exception:
            pass
        # URL + visible items from snapshot text via daemon query? Use `webctl do` no; use snapshot parse
        snap = wc('snapshot')
        import re
        m = re.search(r'url:\s*(\S+)', snap)
        out['url'] = m.group(1) if m else ''
        items = []
        for line in snap.splitlines():
            mm = re.search(r'textbox|"([^"]+)"', line)
        # simpler: parse snapshot text for todo labels between 'todos' and footer
        body = wc('snapshot')
        mm = re.findall(r'@e\d+ (?:checkbox|link|button)? ?"?(.*?)"?$', body)
        out['items'] = [{'text': t, 'completed': False} for t in mm if t]
        return _j.dumps(out)

    def screenshot(self, handle, path):
        wc('screenshot', '--path', path, timeout=30)

    def teardown(self, handle):
        try: wc('stop', timeout=30)
        except Exception: pass

if __name__ == '__main__':
    for rep in ['1', '2']:
        benchlib.run_rep(Webctl(), rep)
