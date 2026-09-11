#!/usr/bin/env python3
# Round 3 adapter: page-agent (alibaba) npm page-agent@1.12.4 == repo commit 9eb6b66.
# Drive path: @page-agent/mcp (MCP over stdio) -> hub WS -> Page Agent extension hub tab (Chrome for Testing, CDP 9251).
# LLM: z-ai/glm-5.3-flash via OpenRouter (LLM_BASE_URL=https://openrouter.ai/api/v1, LLM_MODEL_NAME=z-ai/glm-5.3-flash).
#   page-agent passes config per execute via hub {model,baseURL,apiKey}; here env-based config on the MCP
#   subprocess. provider.sort=latency is NOT settable (page-agent does not forward OpenRouter provider
#   routing); recorded in setup notes. The user's everyday Chrome also runs this extension and races for
#   the hub slot, so a fresh bridge port is used per run and the launcher tab is opened in the bench
#   Chrome BEFORE the bridge starts so its hub connects first.
import sys, os, json, time, subprocess, socket, urllib.request, shutil
sys.path.insert(0, '/Users/rajeev/Code/web-automation-microbench/bench-ext')
import benchlib

MCP_JS = '/Users/rajeev/Code/web-automation-microbench/bench-ext/work/page-agent/packages/mcp/src/index.js'
CDP_HTTP = 'http://127.0.0.1:9251'

class MCPStdio:
    def __init__(self, port):
        self.p = subprocess.Popen(
            ['node', MCP_JS], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True,
            env={**os.environ,
                 'PORT': str(port),
                 'LLM_BASE_URL': 'https://openrouter.ai/api/v1',
                 'LLM_API_KEY': os.environ.get('OPENROUTER_API_KEY', ''),
                 'LLM_MODEL_NAME': 'z-ai/glm-5.3-flash'})
        self.nid = 0
        self._rpc({'jsonrpc': '2.0', 'id': 0, 'method': 'initialize', 'params': {
            'protocolVersion': '2024-11-05', 'capabilities': {},
            'clientInfo': {'name': 'bench', 'version': '1.0'}}}, 0, 30)
        self.p.stdin.write(json.dumps({'jsonrpc': '2.0', 'method': 'notifications/initialized'}) + '\n')
        self.p.stdin.flush()
    def _rpc(self, obj, mid=None, timeout=300):
        self.p.stdin.write(json.dumps(obj) + '\n'); self.p.stdin.flush()
        if mid is None: return None
        t0 = time.time()
        while time.time() - t0 < timeout:
            line = self.p.stdout.readline()
            if not line: raise RuntimeError('MCP exited')
            try: msg = json.loads(line)
            except Exception: continue
            if msg.get('id') == mid: return msg
        raise TimeoutError(f'mcp id {mid}')
    def call(self, name, args, timeout=300):
        self.nid += 1
        return self._rpc({'jsonrpc': '2.0', 'id': self.nid, 'method': 'tools/call',
                          'params': {'name': name, 'arguments': args}}, self.nid, timeout)
    def close(self):
        try: self.p.stdin.close()
        except Exception: pass
        try: self.p.kill()
        except Exception: pass

class CDPHttp:
    _ws = None
    @classmethod
    def _conn(cls):
        if cls._ws is None:
            tabs = json.load(urllib.request.urlopen(CDP_HTTP + '/json', timeout=5))
            todo = [t for t in tabs if 'todomvc' in t.get('url', '')]
            url = (todo or [t for t in tabs if t.get('type') == 'page'])[0]['webSocketDebuggerUrl']
            import websocket
            cls._ws = websocket.create_connection(url, timeout=60, suppress_origin=True)
        return cls._ws
    @classmethod
    def eval(cls, expr):
        ws = cls._conn()
        ws.send(json.dumps({'id': 1, 'method': 'Runtime.evaluate',
                            'params': {'expression': expr, 'returnByValue': True}}))
        while True:
            r = json.loads(ws.recv())
            if r.get('id') == 1:
                res = r.get('result', {}).get('result', {})
                v = res.get('value')
                if isinstance(v, str) and v.strip().startswith('{'): return v
                return json.dumps(v)
    @classmethod
    def verify_js(cls):
        return cls.eval(benchlib.VERIFY_JS)
    @classmethod
    def screenshot(cls, path):
        ws = cls._conn()
        ws.send(json.dumps({'id': 2, 'method': 'Page.captureScreenshot', 'params': {}}))
        while True:
            r = json.loads(ws.recv())
            if r.get('id') == 2:
                pathlib.Path(path).write_bytes(__import__('base64').b64decode(r['result']['data']))
                return

class Adapter:
    name = 'page-agent'
    doc = ('You are the planner; page-agent executes natural-language tasks in the browser. Each step output '
           'JSON {"code":"<one short natural-language task for page-agent to execute in the browser right now>"}, '
           'e.g. {"code":"Add a todo item titled Email supplier"}. ONE logical action per task; page-agent does '
           'the DOM work itself. After a task you will receive its result text. When the whole TASK is complete, '
           'respond {"done":true}.')
    def _free_port(self):
        s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p
    def _open_launcher_tab(self, port):
        url = CDP_HTTP + '/json/new?http://localhost:' + str(port) + '/'
        try:
            req = urllib.request.Request(url, method='PUT')
            return json.load(urllib.request.urlopen(req, timeout=10))
        except Exception:
            return json.load(urllib.request.urlopen(url, timeout=10))
    def start(self):
        t0 = time.perf_counter()
        self.port = self._free_port()
        self._open_launcher_tab(self.port)
        self.mcp = MCPStdio(self.port)
        time.sleep(2.0)
        self._approve_hub()
        time.sleep(1.0)
        try:
            status = self.mcp.call('get_status', {}, timeout=15)
        except Exception as e:
            status = {'error': str(e)}
        obs = 'page-agent-mcp get_status: ' + json.dumps(status)[:300]
        return {'port': self.port}, obs
    def _approve_hub(self):
        try:
            tabs = json.load(urllib.request.urlopen(CDP_HTTP + '/json', timeout=5))
            hubs = [t for t in tabs if 'hub.html' in t.get('url', '')]
            if not hubs: return
            import websocket
            ws = websocket.create_connection(hubs[-1]['webSocketDebuggerUrl'], timeout=20, suppress_origin=True)
            ws.send(json.dumps({'id': 1, 'method': 'Runtime.evaluate', 'params': {
                'expression': "chrome.storage.local.set({allowAllHubConnection:true}); window.confirm = () => true; 'set'",
                'returnByValue': True}}))
            ws.recv()
            ws.close()
        except Exception as e:
            print('approve failed:', e)
    def act(self, handle, code):
        t = time.perf_counter()
        try:
            r = self.mcp.call('execute_task', {'task': code}, timeout=290)
            res = r.get('result', {})
            txt = ''
            try:
                txt = ' '.join(c.get('text', '') for c in res.get('content', []))
            except Exception:
                txt = json.dumps(res)[:1500]
            obs = txt[:1500] or json.dumps(res)[:1500]
        except Exception as e:
            obs = f'MCP ERROR: {type(e).__name__}: {e}'
        return obs, round(time.perf_counter() - t, 3)
    def verify(self, handle):
        try:
            return CDPHttp.verify_js()
        except Exception as e:
            return f'verify error: {type(e).__name__}: {e}'
    def screenshot(self, handle, path):
        try:
            CDPHttp.screenshot(path)
        except Exception as e:
            print('screenshot failed:', e)
    def teardown(self, handle):
        try: self.mcp.call('stop_task', {}, timeout=10)
        except Exception: pass
        try: self.mcp.close()
        except Exception: pass

if __name__ == '__main__':
    rep = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    benchlib.run_rep(Adapter(), rep, max_steps=4)
