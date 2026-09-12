#!/usr/bin/env python3
# Round 6 adapter: chrome-cdp-skill @ bench-ext/work/chrome-cdp-skill commit ffea76a.
# Native interface: the tool's own cdp.mjs CLI (list/shot/snap/html/eval/nav/click/clickxy/type).
# Chrome: dedicated CFT instance on remote-debugging-port 9301, DevToolsActivePort file
# /tmp/bench-cdp-skill-port/DevToolsActivePort (CDP_PORT_FILE env points cdp.mjs at it).
import sys, os, json, re, subprocess, time, pathlib
sys.path.insert(0, '/Users/rajeev/Code/web-automation-microbench/bench-ext')
import benchlib
benchlib.RES = pathlib.Path('/Users/rajeev/Code/web-automation-microbench/bench-ext/artifacts/2026-09-14/results')
benchlib.RES.mkdir(parents=True, exist_ok=True)

SRC = pathlib.Path('/Users/rajeev/Code/web-automation-microbench/bench-ext/work/chrome-cdp-skill/skills/chrome-cdp')
CDP_MJS = str(SRC / 'scripts/cdp.mjs')
PORT_FILE = '/tmp/bench-cdp-skill-port/DevToolsActivePort'
CFT = ('/Users/rajeev/Library/Caches/ms-playwright/chromium-1243/chrome-mac-arm64/'
       'Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing')

def cdp(*args, timeout=60):
    env = {'PATH': '/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin', 'HOME': str(pathlib.Path.home()),
           'CDP_PORT_FILE': PORT_FILE}
    r = subprocess.run(['node', CDP_MJS] + list(args), capture_output=True, text=True,
                       timeout=timeout, env=env)
    return (r.stdout + r.stderr).strip()

def alive():
    import urllib.request, os
    try:
        port = open(PORT_FILE).read().split('\n')[0]
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/json/version', timeout=2) as r:
            return r.status == 200
    except Exception:
        return False

class Adapter:
    name = 'chrome-cdp-skill'
    doc = ('Drive a real Chrome ONLY with the chrome-cdp CLI. One logical action per step. '
           'Verbs: list; snap <target>; eval <target> "<expr>" (ONE expression); nav <target> <url>; '
           'click <target> "<css>"; clickxy <target> <x> <y>; type <target> "<text>"; shot <target>. '
           '<target> is a unique prefix of the targetId from `list` (e.g. 27001540). '
           'There is NO Enter/press verb: to submit text typed into an input, dispatch the key event via eval: '
           'document.activeElement.dispatchEvent(new KeyboardEvent("keydown",{key:"Enter",keyCode:13,which:13,bubbles:true})). '
           'To add a todo: click .new-todo, type the text, then dispatch that keydown via eval. '
           'Mark ONLY "Email supplier" complete (its row toggle), never toggle "Review invoice". '
           'Filter: click a[href="#/active"]; once Active shows only "Review invoice", you are finished. '
           'If a todo already exists, do NOT re-add it; work with the current list. '
           'Observe before acting (list/snap). Respond JSON {"code":"<args for the CLI>"} per step '
           '(args only, e.g. eval 27001540 "...") or {"done":true} once the final state '
           '(Active filter showing only "Review invoice", 1 item left) is observed. Strict JSON only.')
    def __init__(self):
        self.handle = {'tab': None}
    def cli(self, *args, timeout=45):
        p = __import__('subprocess').run(['node', CDP_MJS] + list(args), capture_output=True, text=True,
                                         timeout=timeout, env={'PATH': '/opt/homebrew/bin:/usr/bin:/bin',
                                                               'CDP_PORT_FILE': PORT_FILE,
                                                               'HOME': str(pathlib.Path.home())})
        return (p.stdout + p.stderr).strip()
    def start(self):
        t0 = __import__('time').perf_counter()
        if not alive():
            subprocess.Popen([CFT, '--remote-debugging-port=9301', f'--user-data-dir={os.path.dirname(PORT_FILE)}',
                              '--no-first-run', '--no-default-browser-check', 'about:blank'],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            import time as _t; _t.sleep(3)
            # CFT 153 does not write DevToolsActivePort; synthesize it for cdp.mjs (reads port+ws-path)
            import urllib.request as _u, json as _j
            v = _u.urlopen('http://127.0.0.1:9301/json/version', timeout=5).read()
            ws = json.loads(v)['webSocketDebuggerUrl'].split('127.0.0.1:9301')[1]
            open(PORT_FILE, 'w').write(f'9301\n{ws}\n')
        out = self.cli('open', benchlib.URL_TASK)
        m = re.search(r'Opened new tab: ([0-9A-F]+)', out)
        self.handle['tab'] = m.group(1) if m else None
        # clear storage and reload
        self.cli('eval', self.handle['tab'], "localStorage.removeItem('react-todos'); location.reload()")
        import time as _t; _t.sleep(2.5)
        obs = self.cli('eval', self.handle['tab'], benchlib.OBS_JS)
        self.handle['setup_s'] = round(__import__('time').perf_counter() - t0, 3)
        return dict(self.handle), obs
    def act(self, handle, code):
        import shlex
        try:
            toks = shlex.split(code)
        except ValueError:
            toks = code.split()
        # toks are the args for cdp.mjs itself (e.g. ["eval","T","..."]) — the model may
        # prepend the launcher; strip it if present.
        for i,t in enumerate(toks):
            if t.endswith('cdp.mjs'):
                toks = toks[i+1:]
                break
        out = self.cli(*toks)
        return out, 0.0
    def verify(self, handle):
        return self.cli('eval', handle.get('tab'), benchlib.VERIFY_JS)
    def screenshot(self, handle, path):
        self.cli('shot', handle.get('tab') or '', path)
    def teardown(self, handle):
        pass

if __name__ == '__main__':
    # reps 1-2 = screening; 3-5 promote the fastest Round-6 arrival to a >=5-rep row (issue #1)
    reps = sys.argv[1:] or ['1', '2']
    for rep in reps:
        benchlib.run_rep(Adapter(), rep, max_steps=18)
