#!/usr/bin/env python3
# Round 6 adapter: bb-browser (npm 0.14.2 @ bench-ext/work/bb-browser commit 7975dc7).
# Native interface: the bb-browser CLI (open/snap -i -c/fill/type/press/eval/screenshot/tab close).
# Chrome: dedicated CFT on remote-debugging-port 9302 (launched outside; env BB_BROWSER_CDP_URL
# and the ~/.bb-browser/browser/cdp-port file route the daemon to it).
import sys, os, json, re, subprocess, time, pathlib
sys.path.insert(0, '/Users/rajeev/Code/web-automation-microbench/bench-ext')
import benchlib
benchlib.RES = pathlib.Path('/Users/rajeev/Code/web-automation-microbench/bench-ext/artifacts/2026-09-14/results')
benchlib.RES.mkdir(parents=True, exist_ok=True)

CFT = ('/Users/rajeev/Library/Caches/ms-playwright/chromium-1243/chrome-mac-arm64/'
       'Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing')
ENV = {**os.environ, 'BB_BROWSER_CDP_URL': 'http://127.0.0.1:9302',
       'PATH': '/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin'}
os.makedirs(os.path.expanduser('~/.bb-browser/browser'), exist_ok=True)
open(os.path.expanduser('~/.bb-browser/browser/cdp-port'), 'w').write('9302')
CDP_CACHE = '/var/folders/0p/rbvkdzkx48v616c1fsyl2k2h0000gn/T/bb-browser-cdp-cache.json'

def refresh_cache():
    import json as _j
    with open(CDP_CACHE, 'w') as f:
        _j.dump({'host': '127.0.0.1', 'port': 9302, 'timestamp': int(time.time()*1000)}, f)

def alive():
    import urllib.request
    try:
        with urllib.request.urlopen('http://127.0.0.1:9302/json/version', timeout=2) as r:
            return r.status == 200
    except Exception:
        return False

def bb(*args, timeout=45):
    r = subprocess.run(['bb-browser'] + list(args), capture_output=True, text=True, timeout=timeout, env=ENV)
    return (r.stdout + r.stderr).strip()

class Adapter:
    name = 'bb-browser'
    doc = ('Drive a real Chrome ONLY with the bb-browser CLI. One logical action per step. '
           'Verbs: open <url>; tab list; snap -i -c --tab <id>; click <ref> --tab <id>; '
           'fill <ref> "<text>" --tab <id>; type <ref> "<text>" --tab <id>; press <key> --tab <id>; '
           'eval "<js>" --tab <id>; screenshot <path> --tab <id>; close --tab <id>. '
           'NOTE (observed on React TodoMVC): fill/type sets the input value but press Enter does not create '
           'todos on this app (no todos appear). Verify with snap/eval after submitting; try fill vs type, '
           're-click then type, or press Enter again. Do not use eval to inject UI events for this. '
           'To add a todo: click the .new-todo input ref, fill/type the text, then press Enter. '
           'Mark ONLY "Email supplier" complete (its row checkbox ref). Filter: click a[href="#/active"]. '
           'The initial observation already contains the tab id in the URL header (e.g. "--tab d911"); '
           'use it for every command. '
           'Observe before acting (snap). Respond JSON {"code":"<full CLI command>"} per step '
           '(e.g. "click @3 --tab d911"), or {"done":true} once the final state '
           '(Active filter showing only "Review invoice", 1 item left) is observed. Strict JSON only.')
    def __init__(self):
        self.handle = {'tab': None}
    def start(self):
        t0 = time.perf_counter()
        if not alive():
            raise RuntimeError('CFT on 9302 not running (bb-keeper must be up)')
        refresh_cache()
        out = bb('tab', 'list')
        # close any pre-existing tabs to start clean
        for m in re.finditer(r'\[([0-9a-f]{4})\]', out):
            pass
        r = bb('open', benchlib.URL_TASK)
        m = re.search(r'tab: ([0-9a-f]{4,})', r)
        self.handle['tab'] = m.group(1) if m else None
        pre = ['--tab', self.handle['tab']] if self.handle['tab'] else []
        bb('eval', "localStorage.removeItem('react-todos'); location.reload()", *pre)
        time.sleep(2.5)
        obs = bb('snap', '-i', '-c', *pre)
        self.handle['setup_s'] = round(time.perf_counter() - t0, 3)
        header = f'Active tab: --tab {self.handle["tab"]}\n' if self.handle['tab'] else ''
        return dict(self.handle), header + obs
    def act(self, handle, code):
        import shlex
        try:
            toks = shlex.split(code)
        except ValueError:
            toks = code.split()
        out = bb(*toks)
        return out, 0.0
    def verify(self, handle):
        return bb('eval', benchlib.VERIFY_JS, '--tab', handle.get('tab'))
    def screenshot(self, handle, path):
        bb('screenshot', path, '--tab', handle.get('tab'))
    def teardown(self, handle):
        if handle.get('tab'):
            bb('close', '--tab', handle['tab'])

if __name__ == '__main__':
    for rep in benchlib.reps_from_argv(sys.argv[1:]):
        benchlib.run_rep(Adapter(), rep, max_steps=16)
