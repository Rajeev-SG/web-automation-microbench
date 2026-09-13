#!/usr/bin/env python3
# Round 7 runner: Browser Use Pi (browser-use/browser-use-pi, npm @browser_use/pi).
# Pi Mono agent loop -> persistent V8 REPL -> raw CDP -> Chrome (issue #34).
#
# This is an OWN-LOOP harness like notte/skyvern/midscene: it ships its own agent runtime
# (Pi Mono) and is timed as ONE agent.run per rep, never as one primitive action per model
# call — that preserves its native persistent-REPL architecture (issue #34 fairness rule).
# The node driver `runners/browser-use-pi.mjs` does the work; this module wires the benchlib
# task (instruction / url / verify_js / check), verifies independently on the same live
# browser, and writes the standard run JSON so corpus/report.py can read it.
#
# Version pin: @browser_use/pi 0.1.0, git fa838f3298673950923bdaf12bd3c1b6279cd119.
# Reproduce: bench-ext/runners/browser-use-pi-setup.sh
import json, os, pathlib, subprocess, sys, tempfile, time

sys.path.insert(0, '/Users/rajeev/code/web-automation-microbench/bench-ext')
import benchlib  # noqa: E402

BASE = pathlib.Path('/Users/rajeev/code/web-automation-microbench/bench-ext')
ROOT = os.environ.get('BUPI_ROOT', str(BASE / 'work' / 'browser-use-pi'))
DRIVER = str(BASE / 'runners' / 'browser-use-pi.mjs')
SCRATCH = pathlib.Path(os.environ.get('BUPI_SCRATCH', '/tmp/bupi'))
PIN = '0.1.0 @ fa838f3298673950923bdaf12bd3c1b6279cd119'


def run_native(rep, task=None, name='browser-use-pi'):
    """Run one rep of `task` natively and write `{rep}-{name}.json` into benchlib.RES."""
    t = benchlib.get_task(task)
    t.bind()
    rid = f'{rep}-{name}'
    out_dir = benchlib.RES / rid
    out_dir.mkdir(parents=True, exist_ok=True)
    result_json = out_dir / 'driver.json'
    # Fresh, unique profile + workspace per rep: Browser Use Pi locks a profile to one owner,
    # and reusing one across tasks would leak cookies/localStorage between reps.
    profile = pathlib.Path(tempfile.mkdtemp(prefix=f'bupi-{rid}-', dir=str(SCRATCH)))
    workspace = pathlib.Path(tempfile.mkdtemp(prefix=f'bupiw-{rid}-', dir=str(SCRATCH)))

    log = {'id': rid, 'contender': name, 'rep': rep, 'task': t.id, 'events': [],
           'version': PIN, 'architecture': 'Pi mono agent loop + persistent V8 REPL + raw CDP',
           'runtimes': 'own-loop (agent.run)', 'browser_mode': os.environ.get('BUPI_MODE', 'chromium'),
           'model_config': 'z-ai/glm-5.3-flash via OpenRouter, provider.sort=latency, reasoning low'}
    env = {k: v for k, v in os.environ.items() if not any(x in k.upper() for x in ['KEY', 'TOKEN', 'SECRET', 'PASSWORD'])}
    env.update({
        'BUPI_ROOT': ROOT, 'BUPI_MODE': os.environ.get('BUPI_MODE', 'chromium'),
        'BUPI_CDP_URL': os.environ.get('BUPI_CDP_URL', ''),
        'BUPI_MODEL': os.environ.get('BUPI_MODEL', 'openrouter/z-ai/glm-5.3-flash'),
        'BUPI_INSTRUCTION': t.instruction, 'BUPI_URL': t.url, 'BUPI_VERIFY_JS': t.verify_js,
        'BUPI_OUT': str(result_json), 'BUPI_WORKSPACE': str(workspace), 'BUPI_PROFILE': str(profile),
        'BUPI_MAX_STEPS': str(t.max_steps or benchlib.DEFAULT_MAX_STEPS),
        'BUPI_TIMEOUT_MS': str((t.timeout or benchlib.DEFAULT_TIMEOUT) * 1000),
        'BUPI_SCREENSHOT': str(benchlib.RES / f'{rid}.png'),
        'BUPI_REASONING': os.environ.get('BUPI_REASONING', 'low'),
    })
    if benchlib.KEY:
        env['OPENROUTER_API_KEY'] = benchlib.KEY

    t0 = time.perf_counter()
    try:
        proc = subprocess.run(['node', DRIVER], env=env, capture_output=True, text=True,
                              timeout=(t.timeout or benchlib.DEFAULT_TIMEOUT) + 120)
        log['driver_stdout'] = proc.stdout[-2000:]
        if proc.returncode != 0:
            log['driver_stderr'] = proc.stderr[-2000:]
        out = json.loads(result_json.read_text()) if result_json.is_file() else {}
    except Exception as e:
        out = {}
        log['error'] = f'{type(e).__name__}: {e}'
    log['wall_s'] = round(time.perf_counter() - t0, 3)

    u = out.get('usage') or {}
    tokens = {'input': u.get('input', 0), 'output': u.get('output', 0),
              'cached': u.get('cacheRead', 0), 'reasoning': u.get('reasoning', 0)}
    log.update({
        'status': out.get('status'), 'done': bool(out.get('done')),
        'total_s': round((out.get('wallMs') or 0) / 1000.0, 3),
        'duration_s': round((out.get('durationMs') or 0) / 1000.0, 3),
        'model_calls': out.get('steps'), 'tool_calls': out.get('steps'),
        'steps': out.get('steps'), 'provider': ['openrouter'] if out.get('model') else None,
        'tokens': tokens, 'tokens_source': 'browser-use-pi usage (Pi catalog rates)',
        'cost': round(float((u.get('cost') or {}).get('total') or 0.0), 8),
        'cost_from_tokens': benchlib.estimate_cost(tokens),
        'agent_output': (out.get('output') if isinstance(out.get('output'), str)
                         else json.dumps(out.get('output')))[:3000] if out.get('output') is not None else None,
        'agent_error': out.get('error'), 'run_id': out.get('runId'),
        'verification': out.get('verification'),
    })
    if not log.get('done') and not log.get('error'):
        log['error'] = (out.get('status') or 'no driver result')
    try:
        log['pass'] = bool(t.check(benchlib.parse_verify(log.get('verification'))) and log['done'])
    except Exception as e:
        log['pass'] = False
        log['check_error'] = str(e)

    (benchlib.RES / f'{rid}.json').write_text(json.dumps(log, indent=2))
    print(json.dumps({'id': rid, 'task': t.id, 'pass': log['pass'], 'status': log.get('status'),
                      'steps': log.get('steps'), 'total_s': log.get('total_s'),
                      'tokens': tokens, 'cost': log.get('cost'), 'error': log.get('error')}))
    return log


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    reps, task = benchlib.cli_reps_and_task(argv)
    return [run_native(rep, task=task) for rep in reps]


if __name__ == '__main__':
    main()
