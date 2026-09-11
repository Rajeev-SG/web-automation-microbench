#!/usr/bin/env python3
# Round 3 adapter: jarvis-browser (bridge25) @ bench-ext/work/jarvis-browser commit ec19a46 (v1.4.0).
# Daemon-backed ref CLI over Chrome CDP port 9246. Chrome must be running:
#   "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --remote-debugging-port=9246 \
#     --user-data-dir=/tmp/bench-chrome-jarvis3 --no-first-run --no-default-browser-check about:blank &
# Requires JARVIS_WORKER_ID isolation (set here) and jarvis-browser on PATH (~/bin).
import sys, os, json, subprocess, time
sys.path.insert(0, '/Users/rajeev/Code/web-automation-microbench/bench-ext')
import benchlib

CLI = ['/Users/rajeev/bin/jarvis-browser']
ENV = dict(os.environ, JARVIS_WORKER_ID='bench-r3')

class Adapter:
    name = 'jarvis-browser'
    doc = ("You drive a real Chrome via the jarvis-browser CLI (daemon over CDP). Each step output JSON "
           "{\"code\":\"<full CLI command args>\"}. Verbs: open <url>; snapshot --compact (ref-based tree e1,e2...); "
           "click <ref>; fill <ref> \"text\"; type <ref> \"text\" [--enter]; press <key>; select <ref> \"value\"; "
           "wait --text \"x\"; evaluate \"<js>\" [--isolated]; screenshot --path /tmp/x.png; navigate <url>; reload. "
           "One logical UI action per step; re-snapshot after acting or when unsure of refs. Use UI verbs, not DOM injection "
           "for interactions. Finish with {\"done\":true}.")
    def cli(self, args, timeout=45):
        p = subprocess.run(CLI + args, capture_output=True, text=True, timeout=timeout, env=ENV)
        return (p.stdout + p.stderr).strip()
    def start(self):
        t0 = time.perf_counter()
        out = self.cli(['open', benchlib.URL_TASK])
        self.cli(['evaluate', "localStorage.removeItem('react-todos')"])
        self.cli(['navigate', benchlib.URL_TASK])
        self.cli(['reload'])
        obs = self.cli(['evaluate', benchlib.OBS_JS])
        return {'ok': True}, obs
    def act(self, handle, code):
        import shlex
        try: args = shlex.split(code)
        except Exception: args = code.split()
        out = self.cli(args)
        return out, 0.0
    def verify(self, handle):
        raw = self.cli(['evaluate', '--isolated', benchlib.VERIFY_JS])
        try:
            wrapper = json.loads(raw)
            return str(wrapper.get('data', raw))
        except Exception:
            return raw
    def screenshot(self, handle, path):
        import shutil as _sh
        tmp = '/tmp/jb-shot.png'
        out = self.cli(['screenshot', '--path', tmp])
        if 'error' in out.lower():
            raise RuntimeError(out[:300])
        _sh.copy(tmp, path)
    def teardown(self, handle):
        # leave the tab; daemon + Chrome persist for the next rep
        pass

if __name__ == '__main__':
    rep = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    benchlib.run_rep(Adapter(), rep, max_steps=12)
