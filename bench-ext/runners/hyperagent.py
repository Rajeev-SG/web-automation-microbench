#!/usr/bin/env python3
# Round 6 adapter: HyperAgent (hyperbrowserai/HyperAgent, npm @hyperbrowser/agent 1.1.2, built from source).
# Two native modes are exposed by the tool:
#   * page.perform(instruction) -> accessibility-tree granular single action  <-- SCORED (fast path)
#   * page.ai(instruction)      -> autonomous/visual multi-step task          <-- capability mode
# The scored row drives perform() through the shared benchlib GLM 5.3-Flash loop (one logical
# action per step), so GLM stays the decision-maker; HyperAgent does element resolution.
# provider.sort=latency is injected on every OpenRouter request by a benchmark-side fetch wrapper
# (no upstream source modified); provider + token usage are captured the same way (see the driver).
# Native browser: HyperAgent launches its own local Playwright Chromium (headless), so no
# --remote-debugging-port is reserved/used for this contender.
import sys, os, json, subprocess, time, atexit, pathlib
sys.path.insert(0, '/Users/rajeev/Code/web-automation-microbench/bench-ext')
import benchlib

benchlib.RES = pathlib.Path('/Users/rajeev/Code/web-automation-microbench/bench-ext/artifacts/2026-09-14/results')
benchlib.RES.mkdir(parents=True, exist_ok=True)
DRIVER = '/Users/rajeev/Code/web-automation-microbench/bench-ext/runners/hyperagent-driver.mjs'

_state = {'proc': None}


def _proc():
    if _state['proc'] is None:
        _state['proc'] = subprocess.Popen(['node', DRIVER], stdin=subprocess.PIPE,
                                          stdout=subprocess.PIPE, text=True, bufsize=1)
    return _state['proc']


def hp(msg):
    p = _proc()
    p.stdin.write(json.dumps(msg) + '\n')
    p.stdin.flush()
    line = p.stdout.readline()
    if not line:
        raise RuntimeError('hyperagent driver died')
    return json.loads(line)


def _cleanup():
    try:
        hp({'cmd': 'quit'})
    except Exception:
        pass
    try:
        if _state['proc']:
            _state['proc'].terminate()
    except Exception:
        pass


atexit.register(_cleanup)


class HyperAgent:
    name = 'hyperagent'
    doc = ('Drive the browser ONLY with the native HyperAgent `perform` interface: each response '
           'issues ONE natural-language browser action, which HyperAgent executes on the '
           'accessibility tree. Examples: "fill the new todo input with Email supplier", '
           '"press Enter", "click the checkbox next to Email supplier", "click the Active filter link". '
           'Note: filling a field and committing it are two separate actions. Respond as JSON '
           '{"code":"<one action>"} for each step, and {"done":true} once the final state '
           '(Active filter showing only "Review invoice", 1 item left) is observed. Strict JSON only.')

    def start(self):
        t0 = time.perf_counter()
        hp({'cmd': 'init'})
        r = hp({'cmd': 'reset', 'obs_js': benchlib.OBS_JS})
        return {'setup_s': round(time.perf_counter() - t0, 3)}, (r.get('obs') or '')

    def act(self, handle, code):
        t = time.perf_counter()
        r = hp({'cmd': 'act', 'code': code, 'obs_js': benchlib.OBS_JS})
        return (r.get('out', '') + '\n' + (r.get('obs') or '')), time.perf_counter() - t

    def verify(self, handle):
        return hp({'cmd': 'verify', 'verify_js': benchlib.VERIFY_JS}).get('out', '')

    def screenshot(self, handle, path):
        hp({'cmd': 'screenshot', 'path': path})

    def inner_usage(self):
        return hp({'cmd': 'usage_reset'}).get('usage') or {}


if __name__ == '__main__':
    reps, task = benchlib.cli_reps_and_task(sys.argv[1:])
    for rep in reps:
        a = HyperAgent()
        log = benchlib.run_rep(a, rep, task=task)
        # merge the tool-internal LLM usage (element resolution) collected by the driver
        try:
            inner = a.inner_usage()
        except Exception as e:
            inner = {'error': str(e)}
        path = benchlib.RES / f'{rep}-{a.name}.json'
        d = json.loads(path.read_text())
        d['tool_internal_llm'] = inner
        d['note'] = ('HyperAgent opens its own local Playwright Chromium (headless); '
                     'bench-side fetch wrapper injects provider.sort=latency and tallies tool-internal usage.')
        path.write_text(json.dumps(d, indent=2))
        print(json.dumps({'id': d['id'], 'inner_llm_calls': inner.get('calls'), 'inner_tokens': inner}))
