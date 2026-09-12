#!/usr/bin/env python3
# Round 6 adapter: browser-act/skills (browser-act CLI 1.4.2, skill 2.0.2) @
#   bench-ext/work/browser-act-skills commit 11c057b.
# FREE/LOCAL mode only: `chrome`-type local browser + compact indexed state (state/click/input).
# No stealth/captcha/proxy/remote-assist. Setup: `uv tool install browser-act-cli --python 3.12`
# plus a one-time local `chrome` browser record (see BROWSER_ID; created once via browser create).
import sys, os, re, time, pathlib, subprocess
sys.path.insert(0, '/Users/rajeev/Code/web-automation-microbench/bench-ext')
import benchlib

benchlib.RES = pathlib.Path('/Users/rajeev/Code/web-automation-microbench/bench-ext/artifacts/2026-09-14/results')
benchlib.RES.mkdir(parents=True, exist_ok=True)

BROWSER_ID = 'chrome_local_117890237102817394'
SESSION = 'r6-ba'
SHOT_DIR = '/tmp/bench6-ba-shots'
pathlib.Path(SHOT_DIR).mkdir(exist_ok=True)

def ba(args, timeout=90):
    p = subprocess.run(['browser-act', '--session', SESSION] + args,
                       capture_output=True, text=True, timeout=timeout)
    return (p.stdout + p.stderr).strip()

class Adapter:
    name = 'browser-act-skills'
    doc = ("You drive a real local Chrome via the browser-act CLI. Each step, output JSON "
           "{\"code\":\"<full CLI command args>\"}. Available commands (all run with "
           "--session already set): state (indexed elements like [2]<input .../>); click <index>; "
           "input <index> \"text\" (types into the field); keys \"Enter\"; navigate <url>; reload; "
           "eval \"<js>\"; get markdown; screenshot <path>; wait stable. Do not use stealth/proxy/"
           "captcha features. Always run `state` after any page change and act on the NEW indices "
           "only. One logical UI action per step. When the latest observation already shows the task "
           "fully completed, respond {\"done\":true} immediately with no further commands.")

    def start(self):
        t0 = time.perf_counter()
        ba(['browser', 'open', BROWSER_ID, benchlib.URL_TASK])
        time.sleep(1.0)
        ba(['eval', "localStorage.removeItem('react-todos')"])
        ba(['reload'])
        time.sleep(2.0)
        obs = ba(['state'])
        self.handle = {'setup_s': round(time.perf_counter() - t0, 3)}
        return self.handle, obs

    def act(self, handle, code):
        args = code.split()
        try:
            import shlex
            args = shlex.split(code)
        except Exception:
            pass
        try:
            out = ba(args)
        except subprocess.TimeoutExpired as e:
            out = f'timeout after {e.timeout}s'
        time.sleep(0.6)  # let the page settle so the next state reflects the change
        obs = ba(['state'])
        return obs, 0.0

    def verify(self, handle):
        out = ba(['eval', benchlib.VERIFY_JS])
        # keep only the payload if the CLI wraps it in extra prose
        m = re.search(r'\{.*\}', out, re.S)
        return m.group(0) if m else out

    def screenshot(self, handle, path):
        ba(['screenshot', path])

    def teardown(self, handle):
        try:
            subprocess.run(['browser-act', 'session', 'close', SESSION],
                           capture_output=True, text=True, timeout=30)
        except Exception:
            pass

if __name__ == '__main__':
    benchlib.run_cli(Adapter, max_steps=12)
