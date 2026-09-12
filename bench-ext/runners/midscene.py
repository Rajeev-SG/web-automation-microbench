#!/usr/bin/env python3
# Round 6 adapter: midscene (@midscene/web 1.12.6 from midscene repo commit e9d2c63; npm dist).
# Tier B: vision-driven GUI agent with its OWN runtime, so it is timed as ONE aiAct() run
# (same pattern as runners/notte.py). Chrome for Testing on reserved port 9309 is started by
# the runner itself (pre-timer) via cft_chrome (branded Chrome self-quits when backgrounded).
#
# Model wiring (recorded, no midscene internals patched):
#   MIDSCENE_MODEL_BASE_URL="https://openrouter.ai/api/v1"   (OpenAI-compatible base URL)
#   MIDSCENE_MODEL_API_KEY="$OPENROUTER_API_KEY"             (also export OPENAI_API_KEY=same;
#     @midscene/core's OpenAI client constructor requires OPENAI_API_KEY to be set even when
#     MIDSCENE_MODEL_API_KEY is provided — without it init fails with "Missing credentials")
#   MIDSCENE_MODEL_NAME="z-ai/glm-5.3-flash"
#   MIDSCENE_MODEL_FAMILY="glm-v"        (midscene's GLM-V adapter: bbox xy normalized to 1000,
#     thinking.type=disabled mapped from MIDSCENE_MODEL_REASONING_ENABLED=false)
# Token/cost telemetry: MIDSCENE_RECORD_MODEL_CALL=true writes midscene_run/model-requests/*.jsonl
# with per-call OpenRouter usage (prompt_tokens/completion_tokens/cost) in the `final` event.
import sys, os, json, time, glob, pathlib
sys.path.insert(0, '/Users/rajeev/Code/web-automation-microbench/bench-ext')
import benchlib, cft_chrome

benchlib.RES = benchlib.artifacts_dir('results')   # run-time date, or BENCH_RES
benchlib.RES.mkdir(parents=True, exist_ok=True)

PORT = 9309
PROFILE = f'/tmp/bench6-midscene-{PORT}'
APP_DIR = '/tmp/midscene-bench6'          # npm install @midscene/web puppeteer tsx
os.environ['MIDSCENE_MODEL_BASE_URL'] = 'https://openrouter.ai/api/v1'
os.environ['MIDSCENE_MODEL_API_KEY'] = benchlib.KEY
os.environ['OPENAI_API_KEY'] = benchlib.KEY   # required by the OpenAI SDK client ctor
os.environ['MIDSCENE_MODEL_NAME'] = 'z-ai/glm-5.3-flash'
os.environ['MIDSCENE_MODEL_FAMILY'] = 'glm-v'
os.environ['MIDSCENE_MODEL_REASONING_ENABLED'] = 'false'
os.environ['MIDSCENE_RECORD_MODEL_CALL'] = 'true'

NODE_SCRIPT = r'''
import puppeteer from 'puppeteer';
import { PuppeteerAgent } from '@midscene/web/puppeteer';
const browser = await puppeteer.connect({browserURL: process.env.CDP_URL, defaultViewport: null});
const pages = await browser.pages();
const page = pages[0] || await browser.newPage();
await page.setViewport({width:1280,height:800,deviceScaleFactor:1});
await page.goto(process.env.TASK_URL, {waitUntil:'networkidle2'});
const agent = new PuppeteerAgent(page, {replanningCycleLimit: 40});
const t0 = Date.now();
let ok = true, err = null;
try {
  await agent.aiAct(process.env.TASK_TEXT);
} catch (e) {
  ok = false; err = (e && e.message ? e.message : String(e)).slice(0, 500);
}
const total_s = (Date.now() - t0) / 1000;
console.log('MIDSCENE_RESULT ' + JSON.stringify({ok, err, total_s}));
await agent.destroy();
await browser.disconnect();
'''

def model_requests_dir():
    return pathlib.Path(APP_DIR) / 'midscene_run' / 'model-requests'

class NativeRun:
    name = 'midscene'
    # Not driven by the shared GLM loop: midscene ships its own agent runtime and is
    # timed as ONE aiAct() call (brief: "unless the tool ships its own agent runtime").

    def __init__(self):
        self.chrome = None

    def _sum_usage(self):
        """Sum usage across the JSONL files written during this run."""
        ti = to = cost = calls = 0
        for f in glob.glob(str(model_requests_dir() / '*.jsonl')):
            mtime = pathlib.Path(f).stat().st_mtime
            if mtime < self.t_start - 5:
                continue
            for line in open(f, errors='replace'):
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                if d.get('type') == 'response' and isinstance(d.get('final'), dict):
                    u = d['final'].get('usage') or {}
                    ti += u.get('prompt_tokens') or 0
                    to += u.get('completion_tokens') or 0
                    cost += u.get('cost') or 0
                    calls += 1
        return ti, to, cost, calls

    def run(self, rep):
        rid = f'{rep}-midscene'
        log = {'id': rid, 'contender': self.name, 'rep': rep, 'events': []}
        t_setup = time.perf_counter()
        self.chrome = cft_chrome.Chrome(PORT, profile=PROFILE, start_url='about:blank')
        self.chrome.launch()
        env = dict(os.environ)
        env['CDP_URL'] = f'http://127.0.0.1:{PORT}'
        env['TASK_URL'] = benchlib.URL_TASK
        env['TASK_TEXT'] = benchlib.TASK
        self.t_start = time.perf_counter()
        log['setup_s'] = round(self.t_start - t_setup, 3)
        import subprocess
        p = subprocess.run(['node', '--input-type=module', '-e', NODE_SCRIPT], cwd=APP_DIR,
                           env=env, capture_output=True, text=True, timeout=600)
        total = time.perf_counter() - self.t_start
        result = None
        for line in (p.stdout or '').splitlines():
            if line.startswith('MIDSCENE_RESULT '):
                result = json.loads(line[len('MIDSCENE_RESULT '):])
        if result is None:
            log['error'] = f'no MIDSCENE_RESULT line; rc={p.returncode}; stderr={ (p.stderr or "")[-400:] }'
            log['done'] = False
            log['pass'] = False
        else:
            ti, to, cost, calls = self._sum_usage()
            log['total_s'] = round(result.get('total_s') or total, 3)
            log['api_s'] = log['total_s']
            log['model_calls'] = calls
            log['done'] = bool(result.get('ok'))
            log['error'] = result.get('err')
            log['tokens'] = {'input': ti, 'output': to, 'cached': 0, 'reasoning': 0}
            log['cost_usd'] = round(cost, 6)
            log['tokens_source'] = 'midscene MIDSCENE_RECORD_MODEL_CALL jsonl (OpenRouter usage incl. OpenRouter-reported cost)'
            log['events'].append({'step': 1, 'answer': {'runtime': 'midscene aiAct'}, 'usage': {'calls': calls}})
            # verify + screenshot post-timer, same as benchlib
            import urllib.request
            try:
                ws = None
                # evaluate VERIFY_JS over CDP HTTP is not available; use puppeteer through node
                eval_script = r'''
import puppeteer from 'puppeteer';
const browser = await puppeteer.connect({browserURL: process.env.CDP_URL, defaultViewport: null});
const pages = await browser.pages();
const page = pages[0];
const out = await page.evaluate(() => VERIFY_JS_PLACEHOLDER);
console.log('VERIFY_OUT ' + JSON.stringify(out));
await browser.disconnect();
'''.replace('VERIFY_JS_PLACEHOLDER', benchlib.VERIFY_JS)
                pv = subprocess.run(['node', '--input-type=module', '-e', eval_script], cwd=APP_DIR,
                                    env=env, capture_output=True, text=True, timeout=60)
                vout = None
                for line in (pv.stdout or '').splitlines():
                    if line.startswith('VERIFY_OUT '):
                        vout = json.loads(line[len('VERIFY_OUT '):])
                # page.evaluate(VERIFY_JS) returns a JSON *string*; unwrap one layer so
                # check_pass sees the object (same handling as benchlib.parse_verify)
                if isinstance(vout, str):
                    try:
                        vout = json.loads(vout)
                    except Exception:
                        vout = benchlib.parse_verify(vout)
                log['verification'] = json.dumps(vout)
                log['pass'] = bool(benchlib.check_pass(vout) and log['done'])
            except Exception as e:
                log['verification'] = f'verify error: {e}'
                log['pass'] = False
            try:
                shot_script = r'''
import puppeteer from 'puppeteer';
import fs from 'fs';
const browser = await puppeteer.connect({browserURL: process.env.CDP_URL, defaultViewport: null});
const pages = await browser.pages();
const page = pages[0];
const buf = await page.screenshot({fullPage: false});
fs.writeFileSync(process.env.SHOT_PATH, buf);
console.log('SHOT_OK');
await browser.disconnect();
'''
                env2 = dict(env); env2['SHOT_PATH'] = str(benchlib.RES / f'{rid}.png')
                ps = subprocess.run(['node', '--input-type=module', '-e', shot_script], cwd=APP_DIR,
                                    env=env2, capture_output=True, text=True, timeout=60)
                if 'SHOT_OK' not in (ps.stdout or ''):
                    log['screenshot_error'] = (ps.stderr or ps.stdout or '')[-200:]
            except Exception as e:
                log['screenshot_error'] = str(e)
        try:
            self.chrome.kill()
        except Exception:
            pass
        (benchlib.RES / f'{rid}.json').write_text(json.dumps(log, indent=2))
        print(json.dumps({'id': rid, 'pass': log.get('pass'), 'total_s': log.get('total_s'),
                          'model_calls': log.get('model_calls'), 'tokens': log.get('tokens'),
                          'cost': log.get('cost_usd'), 'error': log.get('error')}))
        return log

if __name__ == '__main__':
    reps = benchlib.reps_from_argv(sys.argv[1:])
    for rep in reps:
        NativeRun().run(rep)
