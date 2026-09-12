#!/usr/bin/env python3
# Round 3 fix-up runner: page-agent (alibaba/page-agent ext 1.12.4, @page-agent/mcp).
# Blocker cleared 2026-09-12: the hub approval gate is `chrome.storage.local.allowAllHubConnection`.
# Seeding it in the extension's OWN service-worker context (CDP Runtime.evaluate) clears the gate, so
# execute_task returns results instead of "User denied the connection request." Must be done in the
# extension context - chrome.storage is undefined from a plain web page, which is why earlier seeds no-op'd.
# The MCP bridge's `open <launcher>` is neutered with a no-op `open` on PATH so the user's everyday Chrome
# never races for the hub slot; the launcher is opened in Chrome for Testing instead.
# page-agent ships its own agent runtime, so it is timed as ONE execute_task call (like Magnitude/BrowserCode),
# not driven by the shared benchlib loop. TASK/VERIFY_JS/check_pass/schema come from benchlib.
import sys, os, json, time, subprocess, pathlib
sys.path.insert(0, '/Users/rajeev/Code/web-automation-microbench/bench-ext')
import benchlib, cft_chrome

PA = '/Users/rajeev/Code/web-automation-microbench/bench-ext/work/page-agent'
EXT = f'{PA}/packages/extension/.output/chrome-mv3'
MCP_JS = f'{PA}/packages/mcp/src/index.js'
CDP = 9290
PORT = 38421
EXT_ID = 'akldabonmimlicnjlflnapfeklbfemhj'
CDPJS = '/Users/rajeev/Code/web-automation-microbench/bench-ext/cdp.mjs'
NOOPEN = '/tmp/noopen'

def cdp(mode, url_sub, arg, port=CDP, timeout=60):
    r = subprocess.run(['node', CDPJS, str(port), mode, url_sub, arg], capture_output=True, text=True, timeout=timeout)
    return (r.stdout + r.stderr).strip()

class MCP:
    def __init__(self, port, key):
        # No LLM_* env on purpose: sending config over the wire makes useHubWs call configure(),
        # which re-renders useAgent and DISPOSES the running agent ("Task aborted"). The key/model are
        # pre-seeded into chrome.storage.local.llmConfig instead, which useAgent reads at mount.
        env = {**os.environ, 'PORT': str(port), 'PATH': NOOPEN + ':' + os.environ.get('PATH', '')}
        self.p = subprocess.Popen(['node', MCP_JS], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=open('/tmp/bench-pa-mcp.log', 'w'), text=True, env=env)
        self.nid = 0
        self._rpc({'jsonrpc': '2.0', 'id': 0, 'method': 'initialize', 'params': {
            'protocolVersion': '2024-11-05', 'capabilities': {}, 'clientInfo': {'name': 'bench', 'version': '1'}}}, 0, 30)
        self.p.stdin.write(json.dumps({'jsonrpc': '2.0', 'method': 'notifications/initialized'}) + '\n'); self.p.stdin.flush()
    def _rpc(self, obj, mid, timeout=300):
        import select
        self.p.stdin.write(json.dumps(obj) + '\n'); self.p.stdin.flush()
        t0 = time.time()
        while time.time() - t0 < timeout:
            r, _, _ = select.select([self.p.stdout], [], [], max(0.5, timeout - (time.time() - t0)))
            if not r:
                break
            line = self.p.stdout.readline()
            if not line: raise RuntimeError('MCP exited')
            try: m = json.loads(line)
            except Exception: continue
            if m.get('id') == mid: return m
        raise TimeoutError('mcp rpc')
    def call(self, name, args, timeout=300):
        self.nid += 1
        return self._rpc({'jsonrpc': '2.0', 'id': self.nid, 'method': 'tools/call',
                          'params': {'name': name, 'arguments': args}}, self.nid, timeout)
    def close(self):
        try: self.p.kill()
        except Exception: pass


def main(rep):
    key = os.environ.get('OPENROUTER_API_KEY', '')
    rid = f'{rep}-page-agent'
    log = {'id': rid, 'contender': 'page-agent', 'rep': rep, 'events': []}
    chrome = None; mcp = None
    try:
        os.makedirs(NOOPEN, exist_ok=True)
        p = pathlib.Path(NOOPEN, 'open'); p.write_text('#!/bin/sh\nexit 0\n'); p.chmod(0o755)
        t_setup = time.perf_counter()
        chrome = cft_chrome.Chrome(CDP, extensions=[EXT], start_url='about:blank'); chrome.launch(); time.sleep(3)
        cdp('eval', 'about:blank', f"location.href={json.dumps(benchlib.URL_TASK)}")
        time.sleep(3)
        cdp('eval', 'todomvc', "localStorage.removeItem('react-todos'); location.reload();")
        time.sleep(3)
        # seed approval in the extension's own service worker
        seed = cdp('eval', EXT_ID + '/background.js',
                   "chrome.storage.local.set({allowAllHubConnection:true,llmConfig:{baseURL:'https://openrouter.ai/api/v1',"
                   "model:'z-ai/glm-5.3-flash',apiKey:" + json.dumps(key) + "}})"
                   ".then(()=>chrome.storage.local.get(['allowAllHubConnection','llmConfig'])).then(v=>JSON.stringify(v))")
        # never log the seeded llmConfig (it contains the API key); record only the approval flag
        log['seed'] = 'allowAllHubConnection set; llmConfig seeded (redacted)' if 'true' in seed else seed
        mcp = MCP(PORT, key)
        time.sleep(1.5)
        # open the launcher in a background tab -> extension opens hub.html and connects
        cdp('eval', EXT_ID + '/background.js',
            f"chrome.tabs.create({{url:'http://localhost:{PORT}',active:false}}).then(t=>t.id)")
        time.sleep(4)
        st = mcp.call('get_status', {}); log['pre_status'] = st
        # make sure the TodoMVC tab is the active tab the hub will drive
        cdp('eval', EXT_ID + '/background.js',
            "chrome.tabs.query({url:'*://demo.playwright.dev/*'}).then(ts=>chrome.tabs.update(ts[0].id,{active:true}))")
        time.sleep(0.5)
        log['setup_s'] = round(time.perf_counter() - t_setup, 3)
        start = time.perf_counter()
        res = mcp.call('execute_task', {'task': benchlib.TASK}, timeout=900)
        total = round(time.perf_counter() - start, 3)
        log['events'].append({'step': 1, 'raw': res})
        try: log['hub_text'] = cdp('eval', 'hub.html', 'document.body.innerText')[:1500]
        except Exception as _e: log['hub_text'] = f'err {_e}'
        txt = ''
        try: txt = res['result']['content'][0]['text']
        except Exception: pass
        log.update(total_s=total, model_calls=1, done=bool(txt.startswith('Task completed')),
                   tokens={'input': 0, 'output': 0, 'cached': 0, 'reasoning': 0},
                   tokens_source='n/a (agent runs inside the extension)', agent_result=txt[:2000])
        vout = cdp('eval', 'todomvc', benchlib.VERIFY_JS)
        log['verification'] = vout
        log['pass'] = bool(benchlib.check_pass(benchlib.parse_verify(vout)) and log['done'])
        cdp('shot', 'todomvc', str(benchlib.RES / f'{rid}.png'))
    except Exception as e:
        import traceback; log['error'] = f'{type(e).__name__}: {e}'; log['trace'] = traceback.format_exc()
        log.setdefault('pass', False)
    finally:
        try:
            if mcp: mcp.close()
        except Exception: pass
        try:
            if chrome: chrome.kill()
        except Exception: pass
    (benchlib.RES / f'{rid}.json').write_text(json.dumps(log, indent=2))
    print(json.dumps({'id': rid, 'pass': log.get('pass'), 'total_s': log.get('total_s'), 'error': log.get('error')}))

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '1')
