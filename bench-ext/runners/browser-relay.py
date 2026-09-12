#!/usr/bin/env python3
# Round 3 fix-up adapter: browser-relay (reliefeai/browser-relay, pkg @linsoai/browser-relay 1.5.2).
# Blocker cleared 2026-09-12: the bundled unpacked MV3 extension loads via Chrome for Testing
# --load-extension (branded Chrome ignores it). Drive path: browser-relay CLI -> local relay server
# (127.0.0.1:18795) -> extension -> attached tab. Uses benchlib for task/verify/model/timer/schema.
import sys, os, subprocess, time, atexit, signal
sys.path.insert(0, '/Users/rajeev/Code/web-automation-microbench/bench-ext')
import benchlib, cft_chrome

WR = '/Users/rajeev/Code/web-automation-microbench/bench-ext/work/browser-relay'
CLI = [ 'node', f'{WR}/server/cli.js']
PORT = 18795
CDP = 9270
EXT = f'{WR}/extension'
PORT_ENV = {**os.environ, 'BROWSER_RELAY_PORT': str(PORT)}

_state = {'relay': None, 'chrome': None, 'tab': None}

def br(args, timeout=60):
    r = subprocess.run(CLI + list(args), env=PORT_ENV, capture_output=True, text=True, timeout=timeout)
    return (r.stdout + r.stderr).strip()

def ensure_up():
    if _state['relay'] is None:
        log = open('/tmp/bench-br-relay.log', 'w')
        _state['relay'] = subprocess.Popen(['node', f'{WR}/server/relay-server.js'], env=PORT_ENV,
                                           stdout=log, stderr=log)
        time.sleep(2)
    if _state['chrome'] is None:
        c = cft_chrome.Chrome(CDP, extensions=[EXT], start_url=benchlib.URL_TASK)
        c.launch()
        _state['chrome'] = c
    # The browser is launched once per process, so a later task's tab will not exist yet.
    # Find a tab already on the task's host, else drive an existing tab to the task URL
    # (re-launching the browser per task would defeat the warm-start timing).
    host = benchlib.URL_TASK.split('/')[2].lower() if '//' in benchlib.URL_TASK else 'todomvc'
    end = time.time() + 30
    tabs = ''
    while time.time() < end:
        tabs = br(['tabs'], timeout=30)
        rows = [ln for ln in tabs.splitlines() if '\t' in ln]
        m = [ln for ln in rows if host in ln.lower()]
        if m:
            _state['tab'] = m[0].split('\t')[0].strip()
            return _state['tab']
        if rows:
            tab0 = rows[0].split('\t')[0].strip()
            try:
                br(['navigate', benchlib.URL_TASK, '--tab', tab0], timeout=30)
                _state['tab'] = tab0
                return tab0
            except Exception:
                pass
        time.sleep(1)
    raise RuntimeError(f'browser-relay: no tab for {host} attached: ' + tabs[:300])

def _cleanup():
    try:
        if _state['chrome']: _state['chrome'].kill()
    except Exception: pass
    try:
        if _state['relay']: _state['relay'].terminate()
    except Exception: pass
atexit.register(_cleanup)

class BrowserRelay:
    name = 'browser-relay'
    doc = ('Drive the browser ONLY with the native `browser-relay` CLI (one CLI invocation per step). '
           'Useful commands: `navigate <url>`, `type "<text>" --selector "<sel>"` (add `--submit` to press Enter), '
           '`click "<selector>"`, `key <Key>`, `eval "<js>"`, `observe` (accessibility snapshot), '
           '`screenshot <path>`, `tabs`, `focus`. Read state with `eval` (e.g. `eval "document.title"`). '
           'Respond as JSON {"code":"browser-relay <cmd>"} per step, and {"done":true} once the task '
           'instruction has been carried out and the required end state is observed. Strict JSON only, no prose.')

    def start(self):
        t0 = time.perf_counter()
        tab = ensure_up()
        br(['navigate', benchlib.URL_TASK, '--tab', tab])
        br(['eval', "localStorage.removeItem('react-todos')", '--tab', tab])
        br(['navigate', benchlib.URL_TASK, '--tab', tab])
        # CDP keyboard events only reach the page when its window is foreground;
        # bring the tab forward once so the tool's `key`/`--submit` path works.
        br(['focus', '--tab', tab])
        obs = br(['eval', benchlib.OBS_JS, '--tab', tab])
        return {'tab': tab, 'setup_s': round(time.perf_counter() - t0, 3)}, obs

    def act(self, handle, code):
        t = time.perf_counter()
        c = code.strip()
        if c.startswith('browser-relay'):
            c = c[len('browser-relay'):].strip()
        import shlex
        try:
            toks = shlex.split(c)
        except ValueError:
            toks = c.split()
        out = br(toks + ['--tab', handle['tab']], timeout=90)
        obs = br(['eval', benchlib.OBS_JS, '--tab', handle['tab']], timeout=60)
        return out + '\n' + obs, time.perf_counter() - t

    def verify(self, handle):
        return br(['eval', benchlib.VERIFY_JS, '--tab', handle['tab']], timeout=60)

    def screenshot(self, handle, path):
        br(['screenshot', path, '--tab', handle['tab']], timeout=30)

    def teardown(self, handle):
        pass


if __name__ == '__main__':
    benchlib.run_cli(BrowserRelay)
