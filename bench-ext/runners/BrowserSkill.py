#!/usr/bin/env python3
# Round 3 fix-up adapter: BrowserSkill (Tencent/BrowserSkill, bsk CLI 0.2.1 + wxt MV3 extension).
# Blocker cleared 2026-09-12: the extension is a plain wxt build (apps/extension/dist/chrome-mv3)
# and loads via Chrome for Testing --load-extension; bsk daemon (ws 127.0.0.1:52800) then sees it.
# Drive path: bsk CLI -> daemon -> extension -> Agent Window tab. Uses benchlib for task/verify/model.
import sys, os, subprocess, time, atexit, shlex
sys.path.insert(0, '/Users/rajeev/Code/web-automation-microbench/bench-ext')
import benchlib, cft_chrome

BSK = '/tmp/bsk-bin/bsk'
BS = '/Users/rajeev/Code/web-automation-microbench/bench-ext/work/BrowserSkill'
EXT = f'{BS}/apps/extension/dist/chrome-mv3'
CDP = 9286
_state = {'chrome': None, 'session': None}

def bsk(args, timeout=90):
    r = subprocess.run([BSK] + list(args), capture_output=True, text=True, timeout=timeout)
    return (r.stdout + r.stderr).strip()

def ensure_up():
    if _state['chrome'] is None:
        bsk(['daemon', 'start'], timeout=30)
        time.sleep(1)
        c = cft_chrome.Chrome(CDP, extensions=[EXT], start_url='about:blank')
        c.launch()
        _state['chrome'] = c
        end = time.time() + 40
        while time.time() < end:
            if 'chrome' in bsk(['browsers'], timeout=30):
                break
            time.sleep(1)
        else:
            raise RuntimeError('BrowserSkill: extension never connected')
        out = bsk(['session', 'start'], timeout=30).splitlines()[-1].strip()
        _state['session'] = out.split()[-1]
    return _state['session']

def _cleanup():
    try: bsk(['session', 'stop', '--all'], timeout=15)
    except Exception: pass
    try:
        if _state['chrome']: _state['chrome'].kill()
    except Exception: pass
atexit.register(_cleanup)

class BrowserSkill:
    name = 'BrowserSkill'
    doc = ('Drive the browser ONLY with the native `bsk` CLI. One logical action per step; chain the two '
           'calls one action needs with " && ". '
           'Add a todo: `fill ".new-todo" --value "Email supplier" && press Enter`. '
           'Tick the first todo\'s checkbox: `click ".todo-list li:nth-child(1) .toggle"`. '
           'Open the Active filter: `click "a[href=\\"#/active\\"]"`. '
           'Inspect with `snapshot` (aria @eN refs) or `evaluate "document.body.innerText"`. '
           'Respond as JSON {"code":"bsk ..."} for each step and {"done":true} once the final state '
           '(Active filter showing only "Review invoice", 1 item left) is observed. Strict JSON only.')

    def start(self):
        t0 = time.perf_counter()
        s = ensure_up()
        bsk(['navigate', benchlib.URL_TASK, '--session', s])
        bsk(['evaluate', "localStorage.removeItem('react-todos')", '--session', s])
        bsk(['navigate', benchlib.URL_TASK, '--session', s])
        obs = bsk(['evaluate', benchlib.OBS_JS, '--session', s])
        return {'session': s, 'setup_s': round(time.perf_counter() - t0, 3)}, obs

    def act(self, handle, code):
        t = time.perf_counter()
        c = code.strip()
        if c.startswith('bsk'):
            c = c[len('bsk'):].strip()
        outs = []
        for part in [p.strip() for p in c.replace(';', '&&').split('&&') if p.strip()]:
            if part.startswith('bsk'):
                part = part[len('bsk'):].strip()
            try:
                toks = shlex.split(part)
            except ValueError:
                toks = part.split()
            outs.append(bsk(toks + ['--session', handle['session']], timeout=90))
        obs = bsk(['evaluate', benchlib.OBS_JS, '--session', handle['session']], timeout=60)
        return '\n'.join(outs) + '\n' + obs, time.perf_counter() - t

    def verify(self, handle):
        return bsk(['evaluate', benchlib.VERIFY_JS, '--session', handle['session']], timeout=60)

    def screenshot(self, handle, path):
        bsk(['screenshot', '--out', path, '--session', handle['session']], timeout=40)

    def teardown(self, handle):
        pass


if __name__ == '__main__':
    rep = sys.argv[1] if len(sys.argv) > 1 else '1'
    benchlib.run_rep(BrowserSkill(), rep)
