# Contender: raw persistent Playwright/CDP code-mode baseline
# Playwright npm version: 1.63.0 (bundled chromium-1243); repo ref: microsoft/playwright @ dc0f852
# Pattern: persistent Node REPL process holding one browser + context + page; GLM emits Playwright code per step.
# Model code is wrapped in (async()=>{ ... })() so await works; return value unused.
import sys, json, subprocess, time
sys.path.insert(0, '/Users/rajeev/Code/web-automation-microbench/bench-ext')
import benchlib

REPL_JS = r'''
const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();
  const readline = require('readline');
  const rl = readline.createInterface({ input: process.stdin, terminal: false });
  for await (const line of rl) {
    if (!line.trim()) continue;
    const req = JSON.parse(line);
    let out = '', err = null;
    const t0 = Date.now();
    try {
      if (req.reset) {
        await page.goto(URL_TASK, { waitUntil: 'load' });
        await page.evaluate(() => localStorage.removeItem('react-todos'));
        await page.goto(URL_TASK, { waitUntil: 'load' });
      }
      if (req.js) out = await page.evaluate(req.js);
      if (req.code) { await eval('(async()=>{' + req.code + '\n})()'); }
      if (req.verify) out = await page.evaluate(VERIFY_JS);
      if (req.screenshot) await page.screenshot({ path: req.screenshot });
    } catch (e) { err = String(e).slice(0, 500); }
    process.stdout.write(JSON.stringify({ out: typeof out === 'string' ? out : JSON.stringify(out), err, ms: Date.now() - t0 }) + '\n');
  }
  await browser.close();
})().catch(e => { console.error(String(e)); process.exit(1); });
'''
REPL_JS = REPL_JS.replace('URL_TASK', json.dumps(benchlib.URL_TASK)).replace('VERIFY_JS', json.dumps(benchlib.VERIFY_JS))

class Adapter:
    name = 'raw-playwright'
    doc = '''You drive a persistent Playwright page directly. The page is already navigated to the task URL.
Write plain JavaScript using the `page` object (Playwright API). One logical UI action per response; the harness returns an observation after your code. Code is wrapped in an async IIFE: await is available; do not use top-level `return`.
Examples: await page.fill('.new-todo', 'Email supplier'); await page.keyboard.press('Enter');
await page.click('.todo-list li:nth-child(1) .toggle'); await page.click('a[href="#/active"]');
Do not navigate or reload; the harness manages state. Return ONLY JSON: {"code":"...","done":false} or {"done":true,"result":"..."}. No markdown.'''
    def __init__(self):
        self.p = None
    def _send(self, req):
        self.p.stdin.write(json.dumps(req) + '\n'); self.p.stdin.flush()
        return json.loads(self.p.stdout.readline())
    def start(self):
        self.p = subprocess.Popen(['node', '-e', REPL_JS], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  text=True, cwd='/Users/rajeev/Code/web-automation-microbench/bench-ext')
        t0 = time.perf_counter()
        r = self._send({'reset': True, 'js': benchlib.OBS_JS})
        return {'setup_s': time.perf_counter() - t0}, r['out']
    def act(self, handle, code):
        t0 = time.perf_counter()
        r = self._send({'code': code, 'js': benchlib.OBS_JS})
        obs = r.get('out') or ''
        if r.get('err'): obs += '\nERROR: ' + r['err']
        return obs, time.perf_counter() - t0
    def verify(self, handle):
        return self._send({'verify': True})['out']
    def screenshot(self, handle, path):
        self._send({'screenshot': path})
    def teardown(self, handle):
        try: self.p.terminate()
        except Exception: pass

if __name__ == '__main__':
    reps = [int(x) for x in sys.argv[1:]] or [1, 2]
    for rep in reps:
        benchlib.run_rep(Adapter(), rep)
