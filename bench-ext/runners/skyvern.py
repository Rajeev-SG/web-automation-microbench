#!/usr/bin/env python3
# Round 6 adapter: Skyvern (Skyvern-AI/skyvern, commit 35cfb31) — self-hosted local server.
#
# Skyvern is a heavyweight autonomous multi-agent browser workflow system (LLM + computer vision).
# Its native architecture is preserved: ONE agent run is timed per rep (like notte / Magnitude),
# NOT normalised into the shared one-command-per-step benchlib loop — that would be exactly the
# "optimise away its native architecture" the issue forbids. The shared benchlib supplies the
# verbatim TASK text, VERIFY_JS and the pass predicate.
#
# Local stack (all outside the timed section):
#   * Postgres 14 container `skyvern-postgres` on 127.0.0.1:55432 (SQLite default is broken upstream:
#     migrations emit Postgres-only "'[]'::jsonb" and fail with "unrecognized token: ':'").
#   * `skyvern quickstart --database-string ... --server-only` -> migrations + local org API key.
#   * `skyvern run server` on 127.0.0.1:8000.
#   * LLM: OpenRouter/GLM 5.3-Flash via ENABLE_OPENROUTER=true, LLM_KEY=OPENROUTER,
#     OPENROUTER_MODEL=z-ai/glm-5.3-flash (litellm-backed).
#   * Browser: Chrome for Testing on port 9311 (fresh profile per run) attached via browser_address,
#     so the independent verifier can read the final page + localStorage over CDP after the run.
#
# Comparability limitations (recorded, not hidden):
#   * Skyvern does not pass OpenRouter `provider: {"sort": "latency"}` through — default routing only.
#   * Token/cost telemetry is read from Skyvern's own run record where present, else "unobservable".
import sys, os, json, time, subprocess, urllib.request, re, pathlib
sys.path.insert(0, '/Users/rajeev/Code/web-automation-microbench/bench-ext')
import benchlib, cft_chrome

benchlib.RES = benchlib.artifacts_dir('results')   # run-time date, or BENCH_RES
benchlib.RES.mkdir(parents=True, exist_ok=True)

SKYVERN_DIR = '/Users/rajeev/Code/web-automation-microbench/bench-ext/work/skyvern'
VENV_PY = '/tmp/skyvern-venv/bin/python'
CDP = 9311
BASE_URL = 'http://localhost:8000'
TOKEN = subprocess.run(
    ['docker', 'exec', 'skyvern-postgres', 'psql', '-U', 'skyvern', '-d', 'skyvern', '-t', '-c',
     'select token from organization_auth_tokens limit 1;'],
    capture_output=True, text=True).stdout.strip()


def cdp_eval_node(js, port=CDP):
    r = subprocess.run(['node', '/Users/rajeev/Code/web-automation-microbench/bench-ext/cdp.mjs',
                        str(port), 'eval', 'todomvc', js], capture_output=True, text=True, timeout=60)
    return (r.stdout + r.stderr).strip()


def main(rep):
    rid = f'{rep}-skyvern'
    log = {'id': rid, 'contender': 'skyvern', 'rep': rep, 'events': []}
    chrome = None
    try:
        # ---- untimed setup ----
        t0 = time.perf_counter()
        try:
            urllib.request.urlopen(BASE_URL + '/api/v1/heartbeat', timeout=5)
        except Exception as e:
            raise RuntimeError(f'Skyvern server not reachable at {BASE_URL}: {e}')
        chrome = cft_chrome.Chrome(CDP, start_url=benchlib.URL_TASK)
        chrome.launch()
        cdp_eval_node("localStorage.removeItem('react-todos'); location.reload(); 'cleared'")
        time.sleep(2)
        obs = cdp_eval_node(benchlib.OBS_JS)
        log['setup_s'] = round(time.perf_counter() - t0, 3)

        # ---- timed: ONE native Skyvern agent run ----
        driver = f'''
import sys, os, json, asyncio
sys.path.insert(0, {SKYVERN_DIR!r})
os.chdir({SKYVERN_DIR!r})
from skyvern import Skyvern
sk = Skyvern(base_url={BASE_URL!r}, api_key={TOKEN!r})
async def go():
    r = await sk.run_task(prompt=sys.argv[1], url={benchlib.URL_TASK!r},
                          browser_address='http://127.0.0.1:{CDP}',
                          wait_for_completion=True, max_steps=20, timeout=900,
                          title='bench-todomvc')
    out = {{'run_id': getattr(r,'run_id',None), 'status': str(getattr(r,'status',None)),
             'output': str(getattr(r,'output',None))[:2000],
             'failure_reason': str(getattr(r,'failure_reason',None))[:800]}}
    try:
        run = await sk.get_run(out['run_id'])
        d = run.model_dump() if hasattr(run,'model_dump') else dict(run)
        for k in ('total_tokens','prompt_tokens','completion_tokens','total_cost','llm_cost','step_count'):
            if k in d: out[k] = d[k]
        steps = d.get('steps') or []
        out['steps'] = len(steps)
        tok = 0
        for s in steps:
            tok += (s.get('input_token_count') or 0) + (s.get('output_token_count') or 0)
        out['steps_token_sum'] = tok
    except Exception as e:
        out['get_run_error'] = str(e)[:300]
    print('BENCHJSON' + json.dumps(out))
asyncio.run(go())
'''
        start = time.perf_counter()
        r = subprocess.run([VENV_PY, '-c', driver, benchlib.TASK], capture_output=True, text=True,
                           timeout=1200, cwd=SKYVERN_DIR)
        log['total_s'] = round(time.perf_counter() - start, 3)
        log['model_calls'] = 1
        log['tokens'] = {'input': 0, 'output': 0, 'cached': 0, 'reasoning': 0}
        log['tokens_source'] = 'skyvern run record (unobservable via shared loop)'
        m = re.search(r'BENCHJSON(\{.*\})', r.stdout)
        if m:
            try:
                info = json.loads(m.group(1))
            except Exception:
                info = {'raw': m.group(1)[:800]}
        else:
            info = {'raw_stdout': r.stdout[-800:], 'raw_stderr': r.stderr[-800:]}
        log['agent_result'] = info
        if info.get('steps_token_sum'):
            log['tokens']['input'] = info.get('steps_token_sum')
        fr = info.get('failure_reason')
        fr_none = (fr is None) or str(fr).strip().lower() in ('none', 'null', '')
        log['done'] = str(info.get('status', '')).lower() in ('completed', 'terminated') and fr_none
        # Skyvern's own token/cost telemetry lives in its DB (steps table), keyed by task_id
        try:
            rid_db = info.get('run_id')
            if rid_db:
                q = ("select coalesce(sum(input_token_count),0), coalesce(sum(output_token_count),0), "
                     "coalesce(sum(cached_token_count),0), coalesce(sum(reasoning_token_count),0), "
                     "coalesce(sum(step_cost),0), count(*) from steps where task_id='%s';" % rid_db)
                out = subprocess.run(['docker', 'exec', 'skyvern-postgres', 'psql', '-U', 'skyvern',
                                      '-d', 'skyvern', '-t', '-A', '-F', ',', '-c', q],
                                     capture_output=True, text=True, timeout=30).stdout.strip()
                if out:
                    a = [x.strip() for x in out.split(',')]
                    log['tokens'] = {'input': int(a[0]), 'output': int(a[1]), 'cached': int(a[2]),
                                     'reasoning': int(a[3])}
                    log['cost'] = float(a[4])
                    log['step_count_db'] = int(a[5])
                    log['tokens_source'] = 'skyvern steps table (its own telemetry)'
        except Exception as e:
            log['telemetry_error'] = str(e)[:200]

        # ---- untimed verification ----
        vout = cdp_eval_node(benchlib.VERIFY_JS)
        log['verification'] = vout
        log['pass'] = bool(benchlib.check_pass(benchlib.parse_verify(vout)) and log['done'])
        try:
            cdp_eval_node("1")
            subprocess.run(['node', '/Users/rajeev/Code/web-automation-microbench/bench-ext/cdp.mjs',
                            str(CDP), 'shot', 'todomvc', str(benchlib.RES / f'{rid}.png')],
                           capture_output=True, text=True, timeout=60)
        except Exception as e:
            log['screenshot_error'] = str(e)
    except Exception as e:
        import traceback
        log['error'] = f'{type(e).__name__}: {e}'
        log['trace'] = traceback.format_exc()[-1500:]
        log.setdefault('pass', False)
    finally:
        try:
            if chrome: chrome.kill()
        except Exception:
            pass
    (benchlib.RES / f'{rid}.json').write_text(json.dumps(log, indent=2))
    print(json.dumps({'id': rid, 'pass': log.get('pass'), 'total_s': log.get('total_s'),
                      'error': log.get('error'), 'agent': (log.get('agent_result') or {}).get('status')}))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '1')
