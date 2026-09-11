#!/usr/bin/env python3
# Round 3 adapter: agent-chrome-cli (npm 'agent-chrome') @ bench-ext/work/agent-chrome-cli commit da6edc5.
# Drives Chrome CDP on port 9247 via the stateless agent-chrome CLI (snapshot refs -> act).
# Required env: OPENROUTER_API_KEY (benchlib). Chrome must be running:
#   "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --remote-debugging-port=9247 \
#     --user-data-dir=/tmp/bench-chrome-agent-chrome-cli --no-first-run --no-default-browser-check about:blank &
import sys, json, re, subprocess, time, shutil, pathlib
sys.path.insert(0, '/Users/rajeev/Code/web-automation-microbench/bench-ext')
import benchlib

SRC = pathlib.Path('/Users/rajeev/Code/web-automation-microbench/bench-ext/work/agent-chrome-cli')
CLI = ['node', str(SRC / 'bin/agent-chrome.js'), '--port', '9247']
URL = benchlib.URL_TASK

class Adapter:
    name = 'agent-chrome-cli'
    doc = ("You drive a real Chrome via the agent-chrome CLI. Each step, output JSON {\"code\":\"<full CLI command args>\"}. "
           "Available verbs: open <url>; snapshot -ic (compact interactive refs like [ref=eN]); click @eN; fill @eN \"text\"; "
           "type @eN \"text\"; press <key>; select @eN \"value\"; eval \"<js>\"; scroll <dir>; screenshot; tabs; tab new <url>. "
           "One logical UI action per step; always re-snapshot (snapshot -ic) after acting or when you need state. "
           "Do not use JS injection to perform UI actions; use UI verbs (snapshot/click/fill). When the latest observation already shows the task fully completed, respond {\"done\":true} immediately with no further commands.")
    def __init__(self):
        self.handle = {'tabs': []}
    def cli(self, args, timeout=40):
        p = subprocess.run(CLI + args, capture_output=True, text=True, timeout=timeout, cwd=str(SRC))
        out = (p.stdout + p.stderr).strip()
        return out
    def start(self):
        t0 = time.perf_counter()
        out = self.cli(['tab', 'new', 'about:blank'])
        m = re.search(r'Opened new tab (t\d+)', out)
        tab = m.group(1) if m else None
        self.handle = {'tab': tab}
        pre = self._tab_args(tab)
        self.cli(pre + ['open', URL])
        self.cli(pre + ['eval', "localStorage.removeItem('react-todos'); location.reload()"])
        import time as _t; _t.sleep(2.0)
        self.cli(pre + ['snapshot', '-ic'])  # seed ref cache for the fresh page
        obs = self.cli(pre + ['eval', benchlib.OBS_JS])
        return self.handle, obs
    def _tab_args(self, tab):
        return ['--tab', tab] if tab else []
    def act(self, handle, code):
        args = code.split()
        # crude but token-preserving split: keep quoted strings via shlex
        import shlex
        try: args = shlex.split(code)
        except Exception: pass
        out = self.cli(self._tab_args(handle.get('tab')) + args)
        return out, 0.0
    def verify(self, handle):
        return self.cli(self._tab_args(handle.get('tab')) + ['eval', benchlib.VERIFY_JS])
    def screenshot(self, handle, path):
        self.cli(self._tab_args(handle.get('tab')) + ['screenshot', '--full', '--out', path])
    def teardown(self, handle):
        if handle.get('tab'):
            self.cli(['tab', 'close', handle['tab']])

if __name__ == '__main__':
    rep = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    benchlib.run_rep(Adapter(), rep, max_steps=12)
