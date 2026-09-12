#!/usr/bin/env python3
# Round 6 runner: OpenCLI (jackwener/OpenCLI commit 8271afc, npm @jackwener/opencli 1.8.7, extension v1.0.24).
# Generic browser-control path only (state/click/type/fill/keys/wait/eval); no site adapter.
# Chrome for Testing on reserved port 9305 with --load-extension=<repo>/extension; session "r6-opencli".
import sys, json, subprocess, os, time, pathlib, shlex
sys.path.insert(0, '/Users/rajeev/Code/web-automation-microbench/bench-ext')
import benchlib
from cft_chrome import Chrome

benchlib.RES = benchlib.artifacts_dir('results')   # run-time date, or BENCH_RES
benchlib.RES.mkdir(parents=True, exist_ok=True)

EXT = '/Users/rajeev/Code/web-automation-microbench/bench-ext/work/OpenCLI/extension'
SESSION = 'r6-opencli'

class OpenCli:
    name = 'opencli'
    doc = ('You drive a real Chrome via the OpenCLI generic browser-control CLI. Each step output JSON '
           '{"code":"<full opencli browser args, WITHOUT the "opencli browser ' + SESSION + '" prefix>"} — '
           'one logical action per step. Available: open <url>; state (indexed elements with [N] refs); '
           'find --css <sel>; click <N|css> [--nth n]; fill <N|css> "text"; type <N|css> "text"; keys <key>; '
           'wait selector <css>|wait text <str>|wait time <s>; eval "<js IIFE>"; get text/value; '
           'screenshot <path>. Do NOT use site adapters or eval for UI actions. Todo text commits on Enter '
           '(use keys Enter after fill if needed). Respond {"done":true} once the latest observation shows '
           'the final state (Active filter showing only "Review invoice", 1 item left). Strict JSON only.')

    def __init__(self):
        self.chrome = None
        self.handle = {}

    def _cli(self, args, timeout=45):
        r = subprocess.run(['opencli', 'browser', SESSION] + args, capture_output=True, text=True,
                           timeout=timeout)
        return (r.stdout + r.stderr).strip()

    def start(self):
        t0 = time.perf_counter()
        # fresh CFT with extension on reserved port 9305
        try:
            subprocess.run(['pkill', '-f', 'remote-debugging-port=9305'], capture_output=True, timeout=10)
        except Exception: pass
        self.chrome = Chrome(9305, extensions=[EXT], start_url='about:blank')
        self.chrome.launch(wait=True)
        time.sleep(4)
        # ensure profile bound to this instance
        pid_ = self._profile_id()
        if pid_: subprocess.run(['opencli', 'profile', 'use', pid_], capture_output=True, timeout=15)
        self._cli(['open', benchlib.URL_TASK], timeout=45)
        time.sleep(2)
        self._cli(['eval', "(() => { localStorage.removeItem('react-todos'); location.reload(); })()"], timeout=30)
        time.sleep(2)
        obs = self._cli(['eval', benchlib.OBS_JS])
        self.handle = {'setup_s': round(time.perf_counter()-t0, 3)}
        return self.handle, obs

    def _profile_id(self):
        try:
            out = subprocess.run(['opencli', 'profile', 'list'], capture_output=True, text=True, timeout=15).stdout
            import re
            m = re.search(r'(?:•|—)\s*([A-Za-z0-9]+)\s*[—-]?\s*connected', out)
            if m: return m.group(1)
        except Exception: pass
        return None

    def act(self, handle, code):
        t = time.perf_counter()
        try:
            out = self._cli(shlex.split(code), timeout=60)
        except Exception as e:
            out = f'error: {e}'
        time.sleep(0.8)
        obs = self._cli(['eval', benchlib.OBS_JS])
        return out + '\n' + obs, time.perf_counter()-t

    def verify(self, handle):
        return self._cli(['eval', benchlib.VERIFY_JS])

    def screenshot(self, handle, path):
        try: self._cli(['screenshot', path], timeout=30)
        except Exception as e: print(f'screenshot error: {e}', file=sys.stderr)

    def teardown(self, handle):
        try: self._cli(['close'], timeout=15)
        except Exception: pass
        if self.chrome:
            self.chrome.kill(); self.chrome = None

if __name__ == '__main__':
    benchlib.run_cli(OpenCli, max_steps=12)
