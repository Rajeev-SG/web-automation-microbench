#!/usr/bin/env python3
# Round 3 adapter: Lightpanda (lightpanda-io/browser) v0.4.0 == work/browser commit f3a775f.
# Thin-native: raw CDP over websocket to Lightpanda's built-in CDP server (port 9249).
# Requires: websocket-client (pip3 install --user --break-system-packages websocket-client)
# Run: /Users/rajeev/Code/web-automation-microbench/bench-ext/work/browser-bin/lightpanda serve --host 127.0.0.1 --port 9249
# NOTE: Lightpanda rejects WS handshakes carrying an Origin header (403 "Origin not allowed") —
#       python websocket-client needs suppress_origin=True.
import sys, json, time, subprocess, pathlib
sys.path.insert(0, '/Users/rajeev/Code/web-automation-microbench/bench-ext')
import benchlib
import websocket

CDP = 'ws://127.0.0.1:9249/'
LP = '/Users/rajeev/Code/web-automation-microbench/bench-ext/work/browser-bin/lightpanda'

class CDPConn:
    def __init__(self, url):
        self.ws = websocket.create_connection(url, timeout=90, suppress_origin=True)
        self.nid = 0
    def send(self, method, params=None, session=None):
        self.nid += 1
        m = {'id': self.nid, 'method': method}
        if params: m['params'] = params
        if session: m['sessionId'] = session
        self.ws.send(json.dumps(m))
        return self.nid
    def wait_id(self, mid):
        while True:
            r = json.loads(self.ws.recv())
            if r.get('id') == mid: return r
    def call(self, method, params=None, session=None):
        mid = self.send(method, params, session)
        return self.wait_id(mid)
    def close(self): self.ws.close()

class Adapter:
    name = 'lightpanda'
    doc = ("You drive Lightpanda, a Zig headless browser, over raw CDP (websocket). Each step output JSON "
           "{\"code\":\"<CDP method + JSON params>\"} on ONE line, e.g. "
           "{\"code\":\"Runtime.evaluate {\\\"expression\\\":\\\"...\\\",\\\"returnByValue\\\":true}\"} or "
           "{\"code\":\"Page.navigate {\\\"url\\\":\\\"https://...\\\"}\"}. "
           "Available CDP domains (Lightpanda supports a subset): Page.navigate, Page.captureScreenshot, "
           "Runtime.evaluate (returnByValue), Input.dispatchMouseEvent, Input.dispatchKeyEvent, DOM.getDocument/DOM.querySelector. "
           "ONE logical action per step; evaluate OBS-like JS (document.body.innerText, document.querySelectorAll) to observe before acting. "
           "Prefer Runtime.evaluate to read state and DOM.click()/element.value+events via evaluate for interactions — this is the thin-native pattern. "
           "Finish with {\"done\":true}.")
    def start(self):
        self.c = CDPConn(CDP)
        t0 = time.perf_counter()
        r = self.c.call('Target.createTarget', {'url': 'about:blank'})
        self.tid = r['result']['targetId']
        r = self.c.call('Target.attachToTarget', {'targetId': self.tid, 'flatten': True})
        self.sid = r['result']['sessionId']
        self.eval_js("localStorage.removeItem('react-todos')")
        r = self.c.call('Page.navigate', {'url': benchlib.URL_TASK}, self.sid)
        time.sleep(4.0)
        obs = self.eval_js(benchlib.OBS_JS)
        return {'tid': self.tid}, obs
    @property
    def sid(self): return self._sid
    def eval_js(self, expr, await_promise=False):
        params = {'expression': expr, 'returnByValue': True}
        if await_promise: params['awaitPromise'] = True
        r = self.c.call('Runtime.evaluate', params, self._sid)
        res = r.get('result', {}).get('result', {})
        if 'exceptionDetails' in r.get('result', {}):
            return 'EVAL ERROR: ' + json.dumps(r['result']['exceptionDetails'])[:300]
        val = res.get('value')
        if isinstance(val, str) and val.strip().startswith('{'):
            return val  # VERIFY_JS-style JSON string: return verbatim
        return json.dumps(val) if res.get('type') != 'undefined' else 'undefined'
    def act(self, handle, code):
        t = time.perf_counter()
        try:
            parts = code.split(' ', 1)
            method = parts[0].strip()
            params = json.loads(parts[1]) if len(parts) > 1 else {}
            out = ''
            if method == 'Runtime.evaluate':
                out = self.eval_js(params.get('expression', ''), params.get('awaitPromise', False))
            else:
                r = self.c.call(method, params, self._sid)
                out = json.dumps(r.get('result', r.get('error', {})))[:400]
                time.sleep(1.0)  # nav settle for non-eval methods
        except Exception as e:
            out = f'CDP ERROR: {type(e).__name__}: {e}'
        return out, round(time.perf_counter() - t, 3)
    def verify(self, handle):
        return self.eval_js(benchlib.VERIFY_JS)
    def screenshot(self, handle, path):
        try:
            r = self.c.call('Page.captureScreenshot', {}, self._sid)
            import base64
            pathlib.Path(path).write_bytes(__import__('base64').b64decode(r['result']['data']))
        except Exception as e:
            print('screenshot failed:', e)
    def teardown(self, handle):
        try: self.c.call('Target.closeTarget', {'targetId': self.tid})
        except Exception: pass
        try: self.c.close()
        except Exception: pass

# patch sid binding after attach
_orig_start = Adapter.start
def _start(self):
    self.c = CDPConn(CDP)
    r = self.c.call('Target.createTarget', {'url': 'about:blank'})
    self.tid = r['result']['targetId']
    r = self.c.call('Target.attachToTarget', {'targetId': self.tid, 'flatten': True})
    self._sid = r['result']['sessionId']
    self.eval_js("localStorage.removeItem('react-todos')")
    self.c.call('Page.navigate', {'url': benchlib.URL_TASK}, self._sid)
    time.sleep(4.0)
    obs = self.eval_js(benchlib.OBS_JS)
    return {'tid': self.tid}, obs
Adapter.start = _start

if __name__ == '__main__':
    rep = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    benchlib.run_rep(Adapter(), rep, max_steps=12)
