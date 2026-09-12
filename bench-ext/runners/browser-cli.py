#!/usr/bin/env python3
# Round 3 fix-up adapter: browser-cli (six-ddc/browser-cli, ext 0.4.0 / CLI built from source).
# Blocker cleared 2026-09-12: the extension is a plain unpacked MV3 build under
# apps/extension/.output/chrome-mv3 and loads via Chrome for Testing --load-extension.
# Daemon runs on 9333 because 9222 is the user's everyday Chrome debug port; the extension is
# rebuilt with VITE_WS_PORT=9333 so its baked DEFAULT_WS_URL matches.
# Drive path: browser-cli CLI -> daemon (unix socket + ws 127.0.0.1:9333) -> extension -> tab.
import sys, os, subprocess, time, atexit, shlex
sys.path.insert(0, '/Users/rajeev/Code/web-automation-microbench/bench-ext')
import benchlib, cft_chrome

BC = '/Users/rajeev/Code/web-automation-microbench/bench-ext/work/browser-cli'
CLI = ['node', f'{BC}/apps/cli/bin/cli.js']
EXT = f'{BC}/apps/extension/.output/chrome-mv3'
PORT = 9333
CDP = 9281
ENV = {**os.environ, 'NO_COLOR': '1'}
_state = {'chrome': None, 'tab': None}

def bc(args, timeout=90, tab=None):
    cmd = CLI + list(args)
    if tab:
        cmd += ['--tab', str(tab)]
    r = subprocess.run(cmd, env=ENV, capture_output=True, text=True, timeout=timeout)
    return (r.stdout + r.stderr).strip()

def ensure_up():
    if _state['chrome'] is None:
        bc(['stop'], timeout=20)
        bc(['start', '--port', str(PORT)], timeout=30)
        time.sleep(1)
        c = cft_chrome.Chrome(CDP, extensions=[EXT], start_url=benchlib.URL_TASK)
        c.launch()
        _state['chrome'] = c
        end = time.time() + 40
        while time.time() < end:
            s = bc(['status'], timeout=30)
            if 'Browsers connected: 1' in s:
                break
            time.sleep(1)
        else:
            raise RuntimeError('browser-cli: extension did not connect: ' + s[:300])
    # the todomvc tab id
    import json as _json, re
    end = time.time() + 30
    while time.time() < end:
        out = bc(['tab', 'list', '--json'], timeout=30)
        try:
            tabs = _json.loads(out)['data']['tabs']
        except Exception:
            tabs = []
        hit = [t for t in tabs if 'todomvc' in (t.get('url') or '').lower()]
        if hit:
            _state['tab'] = str(hit[0]['id'])
            return _state['tab']
        time.sleep(1)
    raise RuntimeError('browser-cli: no todomvc tab: ' + out[:300])

def _cleanup():
    try: bc(['stop'], timeout=15)
    except Exception: pass
    try:
        if _state['chrome']: _state['chrome'].kill()
    except Exception: pass
atexit.register(_cleanup)

class BrowserCLI:
    name = 'browser-cli'
    doc = ('Drive the browser ONLY with the native `browser-cli` CLI. One logical action per step; '
           'chain the two CLI calls a single action needs with " && ". '
           'Add a todo: `fill ".new-todo" "Email supplier" && press Enter`. '
           'Tick the first todo\'s checkbox: `check ".todo-list li:nth-child(1) .toggle"`. '
           'Open the Active filter: `click "a[href=\\"#/active\\"]"`. '
           'Inspect with `snapshot -ic` (accessibility refs) or `eval "document.body.innerText"`. '
           'Respond as JSON {"code":"browser-cli ..."} for each step and {"done":true} once the final '
           'state (Active filter showing only "Review invoice", 1 item left) is observed. Strict JSON only.')

    def start(self):
        t0 = time.perf_counter()
        tab = ensure_up()
        bc(['navigate', benchlib.URL_TASK], tab=tab)
        bc(['eval', "localStorage.removeItem('react-todos')"], tab=tab)
        bc(['navigate', benchlib.URL_TASK], tab=tab)
        obs = bc(['eval', benchlib.OBS_JS], tab=tab)
        return {'tab': tab, 'setup_s': round(time.perf_counter() - t0, 3)}, obs

    def act(self, handle, code):
        t = time.perf_counter()
        c = code.strip()
        if c.startswith('browser-cli'):
            c = c[len('browser-cli'):].strip()
        outs = []
        for part in [p.strip() for p in c.replace(';', '&&').split('&&') if p.strip()]:
            if part.startswith('browser-cli'):
                part = part[len('browser-cli'):].strip()
            try:
                toks = shlex.split(part)
            except ValueError:
                toks = part.split()
            outs.append(bc(toks, timeout=90, tab=handle['tab']))
        obs = bc(['eval', benchlib.OBS_JS], timeout=60, tab=handle['tab'])
        return '\n'.join(outs) + '\n' + obs, time.perf_counter() - t

    def verify(self, handle):
        return bc(['eval', benchlib.VERIFY_JS], timeout=60, tab=handle['tab'])

    def screenshot(self, handle, path):
        bc(['screenshot', '--path', path], timeout=40, tab=handle['tab'])

    def teardown(self, handle):
        pass


if __name__ == '__main__':
    reps, task = benchlib.cli_reps_and_task(sys.argv[1:])
    for rep in (reps if sys.argv[1:] else ['1']):
        benchlib.run_rep(BrowserCLI(), rep, task=task)
