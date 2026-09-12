#!/usr/bin/env python3
# Round 6 adapter: surf-cli @ bench-ext/work/surf-cli commit 56faa5a (v2.19.0).
# Native interface: the surf CLI (native/cli.cjs) over its own native-messaging socket.
# Chrome: dedicated CFT on remote-debugging-port 9303 with the Surf extension loaded;
# native host pinned to /tmp/surf-9303.sock via SURF_DEFAULT_SOCKET patch in work/surf-cli
# (upstream hardcodes /tmp/surf.sock and ignores env, breaking parallel Chrome instances).
import sys, os, re, json, subprocess, time, pathlib
sys.path.insert(0, '/Users/rajeev/Code/web-automation-microbench/bench-ext')
import benchlib
benchlib.RES = pathlib.Path('/Users/rajeev/Code/web-automation-microbench/bench-ext/artifacts/2026-09-14/results')
benchlib.RES.mkdir(parents=True, exist_ok=True)

CLI = '/Users/rajeev/Code/web-automation-microbench/bench-ext/work/surf-cli/native/cli.cjs'
ENV = {**os.environ, 'SURF_SOCKET': '/tmp/surf-9303.sock', 'PATH': '/opt/homebrew/bin:/usr/bin:/bin'}

def alive():
    import urllib.request
    try:
        with urllib.request.urlopen('http://127.0.0.1:9303/json/version', timeout=2) as r:
            return r.status == 200
    except Exception:
        return False

def surf(*args, timeout=45):
    r = subprocess.run(['node', CLI] + list(args), capture_output=True, text=True, timeout=timeout, env=ENV)
    return (r.stdout + r.stderr).strip()

class Adapter:
    name = 'surf-cli'
    doc = ('Drive a real Chrome ONLY with the surf CLI. One logical action per step. '
           'Verbs: tab.new <url>; read (page text + interactive refs eN); click <eN>; '
           'type "<text>" (types at cursor); key <key> (e.g. key Enter); smart_type --selector <css> '
           '--text "<text>" --submit; '
           'js "<expression>" (evaluate JS, read-only checks only); screenshot --output <path>; '
           'tab.reload. To add a todo: click the textbox ref, then type "text" --submit. '
           'Mark ONLY "Email supplier" complete (its row checkbox ref from read). '
           'Filter: click the Active link ref. Observe (read) before acting. '
           'Respond JSON {"code":"<full CLI command>"} per step (e.g. "click e2"), '
           'or {"done":true} once the final state (Active filter showing only "Review invoice", '
           '1 item left) is observed. Strict JSON only.')
    def __init__(self):
        self.handle = {'tab': None}
    def start(self):
        t0 = time.perf_counter()
        if not alive():
            raise RuntimeError('CFT 9303 with Surf extension not running (surf-keeper up?)')
        r = surf('tab.new', benchlib.URL_TASK)
        m = re.search(r'Created tab (\d+)', r)
        self.handle['tab'] = m.group(1) if m else None
        surf('js', "localStorage.removeItem('react-todos')")
        surf('tab.reload')
        time.sleep(2.5)
        obs = surf('read')
        self.handle['setup_s'] = round(time.perf_counter() - t0, 3)
        return dict(self.handle), obs
    def act(self, handle, code):
        import shlex
        try:
            toks = shlex.split(code)
        except ValueError:
            toks = code.split()
        if toks and toks[0] == 'surf':
            toks = toks[1:]
        out = surf(*toks)
        return out, 0.0
    def verify(self, handle):
        out = surf('js', benchlib.VERIFY_JS)
        return out.split('[surf tab=')[0].strip()
    def screenshot(self, handle, path):
        surf('screenshot', '--output', path)
    def teardown(self, handle):
        pass

def surf(*args, timeout=45):
    r = subprocess.run(['node', CLI] + list(args), capture_output=True, text=True, timeout=timeout, env=ENV)
    return (r.stdout + r.stderr).strip()

if __name__ == '__main__':
    benchlib.run_cli(Adapter, max_steps=22)
