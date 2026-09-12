#!/usr/bin/env python3
# cdp-browser runner — bench-ext Round 3 contract (benchlib.run_rep).
# Source: sids/cdp-browser @ 857a8ba; cdp-browser@0.1.3 (npm). Node 26.7.0.
# Chrome launched manually on --remote-debugging-port 9243 (profile /tmp/bench-chrome-cdp2).
# cdp-browser hardcodes http://localhost:9222 + ws://localhost:9222, so all CLI invocations run under
# a Node preload shim (/tmp/cdp-fwd/cdp-redirect.cjs) that rewrites those URLs to 127.0.0.1:9243.
# The shim only redirects ports; no cdp-browser source files are modified.
import sys, subprocess, os, time
sys.path.insert(0, '/Users/rajeev/Code/web-automation-microbench/bench-ext')
import benchlib

CDP = '/Users/rajeev/Code/web-automation-microbench/bench-ext/work/cdp-browser'
SHIM = '/tmp/cdp-fwd/cdp-redirect.cjs'

def cdp(*args, timeout=60):
    r = subprocess.run(['node', '-r', SHIM, 'bin/browser.js'] + list(args),
                       capture_output=True, text=True, timeout=timeout, cwd=CDP)
    return (r.stdout + r.stderr).strip()

class CdpBrowser:
    name = 'cdp-browser'
    doc = ('Drive the browser ONLY with the native `cdp-browser` CLI (nav/eval/screenshot). '
           'One logical action per step. eval JS must be ONE expression - wrap statements in an IIFE '
           'and return a result string. To add a todo: focus the .new-todo input, set its value with the '
           'native setter, dispatch input event, then dispatch KeyboardEvent("keydown", {key:"Enter", '
           'keyCode:13, which:13, bubbles:true}) on the FOCUSED input. '
           'To click: call .click() on the element (e.g. filter links: a[href="#/active"]). '
           'Respond as JSON {"code":"cdp-browser eval \"<js>\""} or {"done":true}.')

    @staticmethod
    def _alive():
        import urllib.request
        try:
            with urllib.request.urlopen('http://127.0.0.1:9243/json/version', timeout=2) as r:
                return r.status == 200
        except Exception:
            return False

    def start(self):
        t0 = time.perf_counter()
        if not self._alive():
            subprocess.Popen(['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
                              '--remote-debugging-port=9243', '--user-data-dir=/tmp/bench-chrome-cdp2',
                              '--no-first-run', '--no-default-browser-check', 'about:blank'],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             start_new_session=True)
            import time as _t; _t.sleep(2)
        cdp('nav', benchlib.URL_TASK)
        cdp('eval', "localStorage.removeItem('react-todos')")
        cdp('nav', 'about:blank')
        cdp('nav', benchlib.URL_TASK)
        import time as _t
        for _ in range(10):
            _t.sleep(0.3)
            if 'new-todo' in (cdp('eval', "document.querySelector('.new-todo') ? 'y' : 'n'") or ''):
                break
        obs = cdp('eval', benchlib.OBS_JS)
        return {'setup_s': round(time.perf_counter()-t0, 3)}, obs

    def act(self, handle, code):
        t = time.perf_counter()
        toks = code.split()
        if toks and toks[0] in ('cdp-browser', 'node'): 
            # model wrote full CLI string; extract the verb+args after 'browser.js'
            import shlex
            try: t2 = shlex.split(code)
            except ValueError: t2 = toks
            if 'bin/browser.js' in code:
                i = t2.index('bin/browser.js') if 'bin/browser.js' in t2 else 0
                toks = t2[i+1:]
            else:
                toks = t2[1:]
        verb, rest = toks[0], toks[1:]
        if verb == 'nav': out = cdp('nav', *rest)
        elif verb == 'eval':
            js = rest[0] if len(rest) == 1 else ' '.join(rest)
            # tolerate stray model artifacts: cut the JS at the last ')' when unbalanced
            if js.count(')') > js.count('('):
                js = js[:js.rindex(')')+1]
            out = cdp('eval', js)
        elif verb == 'screenshot': out = cdp('screenshot')
        else: out = f'unknown verb: {verb}'
        import time as _t; _t.sleep(0.4)
        obs = cdp('eval', benchlib.OBS_JS)
        return (out + '\n' + obs), time.perf_counter()-t

    def verify(self, handle):
        return cdp('eval', benchlib.VERIFY_JS)

    def screenshot(self, handle, path):
        cdp('screenshot')

    def teardown(self, handle):
        try:
            cdp('eval', "localStorage.removeItem('react-todos'); 'cleared'")
            cdp('nav', 'about:blank')
        except Exception: pass

if __name__ == '__main__':
    for rep in benchlib.reps_from_argv(sys.argv[1:]):
        benchlib.run_rep(CdpBrowser(), rep)
