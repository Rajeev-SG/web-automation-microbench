#!/usr/bin/env python3
# Round 6 adapter: chrome-devtools-mcp / CLI 1.9.0 @ bench-ext/work/chrome-devtools-mcp
# commit d9a8cb6. Official CLI (`npm i -g chrome-devtools-mcp@1.9.0`), full (non-slim) toolset.
# Chrome for Testing on reserved port 9309 is started by the runner itself (pre-timer, via
# cft_chrome with --no-default-app-window so CFT does not self-quit when idle).
# NOTE: branded Google Chrome on this host self-quits ~10-30s after launch when backgrounded;
# CFT (which cft_chrome.py launches) stays up, so the runner uses CFT for port 9309.
import sys, json, re, time, pathlib, subprocess
sys.path.insert(0, '/Users/rajeev/Code/web-automation-microbench/bench-ext')
import benchlib, cft_chrome

benchlib.RES = pathlib.Path('/Users/rajeev/Code/web-automation-microbench/bench-ext/artifacts/2026-09-14/results')
benchlib.RES.mkdir(parents=True, exist_ok=True)

PORT = 9309
PROFILE = f'/tmp/bench6-cdm-cft-{PORT}'
CLI = ['chrome-devtools']

def cdm(args, timeout=60):
    p = subprocess.run(CLI + args, capture_output=True, text=True, timeout=timeout)
    out = (p.stdout + p.stderr).strip()
    out = '\n'.join(l for l in out.splitlines() if 'ExperimentalWarning' not in l and '--trace-warnings' not in l)
    return out

class Adapter:
    name = 'chrome-devtools-mcp'
    doc = ("You drive a real Chrome via the official chrome-devtools CLI. Each step, output JSON "
           "{\"code\":\"<full CLI command args after 'chrome-devtools'>\"}. Verbs (pageId is ALWAYS 1; never use pageId 2 or any other id): "
           "navigate_page 2 --url <url>; take_snapshot 2 (a11y tree with uid=1_1 style refs); "
           "click 2 <uid>; fill 2 <uid> \"text\"; press_key 2 <key>; evaluate_script \"() => <js>\" "
           "--pageId 2; take_screenshot 2 --filePath <path>. Re-snapshot after every action; uids "
           "change when the page changes. One logical UI action per step. When the latest observation "
           "already shows the task fully completed, respond {\"done\":true} immediately with no "
           "further commands.")

    def start(self):
        t0 = time.perf_counter()
        chrome = cft_chrome.Chrome(PORT, profile=PROFILE, start_url='about:blank')
        chrome.launch()
        self.chrome = chrome
        try:
            cdm(['stop'])
        except Exception:
            pass
        out = cdm(['start', '--browser-url', f'http://127.0.0.1:{PORT}', '--no-usage-statistics'])
        if 'Could not connect' in out or 'exposes content' not in out:
            pass  # start prints banner then daemon info; connectivity is checked by the first call
        pages = cdm(['list_pages'])
        # first page is the pre-opened about:blank tab; reuse it by navigating (keeps pageId 1)
        # resolve the real pageId (CLI numbers pages in connection order; after
        # chrome-devtools stop+start the pre-opened tab can be id 1 or 2)
        m = re.search(r'(\d+):', pages)
        self.pid = m.group(1) if m else '1'
        self.handle = {'pid': self.pid, 'setup_s': round(time.perf_counter() - t0, 3)}
        out = cdm(['navigate_page', self.pid, '--url', benchlib.URL_TASK])
        time.sleep(1.5)
        cdm(['evaluate_script', "() => { localStorage.removeItem('react-todos'); return 'cleared'; }", '--pageId', self.pid])
        cdm(['navigate_page', self.pid, '--type', 'reload'])
        time.sleep(2.0)
        obs = cdm(['take_snapshot', self.pid])
        if 'todomvc' not in obs.lower():
            pages = cdm(['list_pages'])
            m = re.search(r'(\d+): React', pages)
            if m:
                self.pid = m.group(1)
                self.handle['pid'] = self.pid
                obs = cdm(['take_snapshot', self.pid])
        return self.handle, obs

    def act(self, handle, code):
        import shlex
        try:
            args = shlex.split(code)
        except Exception:
            args = code.split()
        # page-scoped verbs take pageId as their first positional arg; the model has been
        # told it is 1, but force it anyway so a stray id can never target the wrong page
        PAGE_SCOPED = {'navigate_page','take_snapshot','click','fill','press_key','hover',
                       'evaluate_script','take_screenshot','handle_dialog','list_console_messages'}
        if args and args[0] in PAGE_SCOPED and len(args) > 1:
            if not re.fullmatch(r'\d+', args[1]):
                args.insert(1, self.pid)
            else:
                args[1] = self.pid
        out = cdm(args)
        time.sleep(0.5)
        obs = cdm(['take_snapshot', self.pid])
        return obs, 0.0

    def verify(self, handle):
        out = cdm(['evaluate_script', f'() => {benchlib.VERIFY_JS}', '--pageId', self.pid])
        # benchlib.parse_verify expects the raw JSON payload; the CLI wraps it in
        # "Script ran on page and returned:\n```json\n<json string>``` — return just the payload.
        m = re.search(r'```json\n(.*)```', out, re.S)
        if m:
            return m.group(1).strip()
        return out

    def screenshot(self, handle, path):
        try:
            cdm(['take_screenshot', self.pid, '--filePath', path])
        except Exception as e:
            raise

    def teardown(self, handle):
        try:
            cdm(['stop'])
        except Exception:
            pass
        try:
            self.chrome.kill()
        except Exception:
            pass

if __name__ == '__main__':
    benchlib.run_cli(Adapter, max_steps=12)
