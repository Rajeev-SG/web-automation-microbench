#!/usr/bin/env python3
# Round 8 contender adapter: adaptive-ui-runtime (Rajeev-SG/adaptive-ui-runtime).
#
# OWN-LOOP harness, like notte / skyvern / browser-use-pi: the runtime ships its own
# plan -> route -> act -> verify engine, so ONE runtime run is timed per rep, never
# one primitive action per model call. That preserves its native architecture
# (issue #34 fairness rule).
#
# How it is driven (nothing here forks the runtime):
#   * the microbench launches Chrome for Testing and owns the timing boundary, reset
#     and independent verification;
#   * the runtime attaches to that Chrome over CDP (it ships no CDP transport, so the
#     driver subclasses the runtime's own `IsolatedBrowserTransport` and replaces only
#     the launcher) and runs `Engine.execute` once;
#   * the microbench then verifies INDEPENDENTLY over CDP with the task's own
#     `verify_js` + declarative `pass_rule` via benchlib/pass_rule. The runtime's own
#     `verified` flag is recorded as `runtime_verified` and never trusted for pass.
#
# The runtime runs in its OWN venv (`.venv/bin/python`) as a subprocess, exactly as
# the CLI/MCP would; the contender wall time is that one subprocess call.
#
# Comparability caveats live in bench-ext/runners/ADAPTIVE_UI_RUNTIME.md.
import json, os, pathlib, subprocess, sys, tempfile, time

sys.path.insert(0, '/Users/rajeev/Code/web-automation-microbench/bench-ext')
import benchlib  # noqa: E402
import cft_chrome  # noqa: E402

BASE = pathlib.Path('/Users/rajeev/Code/web-automation-microbench/bench-ext')
AUR = pathlib.Path(os.environ.get('AUR_ROOT', '/Users/rajeev/Code/adaptive-ui-runtime'))
AUR_PY = str(AUR / '.venv' / 'bin' / 'python')
DRIVER = str(BASE / 'runners' / 'aur_driver' / 'driver.py')
CDP_MJS = str(BASE / 'cdp.mjs')
CORPUS = BASE / 'corpus' / 'tasks'
NAME = 'adaptive-ui-runtime'

# One Chrome for Testing instance per rep, on a quiet port, killed at teardown.
_CDP_BASE = 9280 + (os.getpid() % 400)

def _todo_pred_js():
    """Runtime-side criterion for the default TodoMVC task.

    The runtime's verifier has no access to benchlib.check_pass, so we hand it an
    equivalent JS predicate built from benchlib.VERIFY_JS *at call time* (reading the
    task global at import would freeze TodoMVC into every rep — the import-time-freeze
    bug the harness guards against). Harvested tasks instead pass their own verify_js
    + declarative pass_rule straight through.
    """
    return (
        "(function(){var v=JSON.parse(%s);var saved=v.saved;"
        "return (v.url.indexOf('#/active')>=0)&&v.items.length===1&&"
        "v.items[0].text.indexOf('Review invoice')>=0&&!v.items[0].completed&&"
        "JSON.stringify(saved)===JSON.stringify([{title:'Email supplier',completed:true},"
        "{title:'Review invoice',completed:false}]);})()"
    ) % json.dumps(benchlib.VERIFY_JS)


def _compact_events(events, limit=400, str_cap=140):
    """Bounded event record for the committed run JSON (keeps the route/action/
    failure sequence; drops the repeated goal text and run ids that bloat the file).
    The full trace remains available from the runtime itself via `aur trace <run_id>`.
    """
    out = []
    for e in (events or [])[:limit]:
        data = {}
        for k, v in (e.get("data") or {}).items():
            if isinstance(v, str) and len(v) > str_cap:
                v = v[:str_cap] + "…"
            data[k] = v
        out.append({"kind": e.get("kind"), "at_ms": e.get("at_ms"), "data": data})
    return out


def _spec_for(task_id):
    p = CORPUS / f'{task_id}.json'
    if p.is_file():
        try:
            return json.loads(p.read_text())
        except Exception:
            return {}
    return {}


def _criteria_for(task, spec):
    """The runtime's own success criterion, built from the task's own verifier.

    Mirrors `adaptive_ui_runtime.microbench.build`: the verify_js and the declarative
    pass_rule ride on the criterion so the runtime applies them with its own code.
    """
    if task.id == benchlib.DEFAULT_TASK_ID:
        return [{"kind": "js_rule", "description": "todomvc pass predicate",
                 "rule": {"js": _todo_pred_js(), "expected": True}}]
    verification = spec.get("verification") or {}
    return [{"kind": "js_rule",
             "description": verification.get("description", task.instruction),
             "rule": {"js": task.verify_js,
                      "microbench_pass_rule": verification.get("pass_rule") or {}}}]


def _cdp_eval(port, url_sub, js, timeout=60):
    r = subprocess.run(['node', CDP_MJS, str(port), 'eval', url_sub, js],
                       capture_output=True, text=True, timeout=timeout)
    return (r.stdout + r.stderr).strip()


def run_native(rep, task=None, name=NAME):
    """Run one rep of `task` as ONE runtime execute; verify independently afterwards."""
    t = benchlib.get_task(task)
    t.bind()
    rid = f'{rep}-{name}'
    spec = _spec_for(t.id)
    chrome = None
    log = {'id': rid, 'contender': name, 'rep': rep, 'task': t.id, 'events': [],
           'runtimes': 'own-loop (Engine.execute, one run per rep)',
           'browser_mode': 'chrome-for-testing (microbench-launched, CDP attach)',
           'model_config': 'openrouter:z-ai/glm-5.3-flash (strong manager), '
                           'temperature 0, classifier.dev Jev',
           'independence': 'benchlib verify_js + pass_rule over CDP, untimed'}
    try:
        port = _CDP_BASE + (int(rep) if str(rep).isdigit() else 0)
        deadline = t.timeout or benchlib.DEFAULT_TIMEOUT
        # ---- untimed setup: launch Chrome, reset state, build the request file ----
        t0 = time.perf_counter()
        chrome = cft_chrome.Chrome(port, start_url=t.url)
        chrome.launch()
        _cdp_eval(port, '*', "localStorage.clear(); sessionStorage.clear(); 'cleared'")
        time.sleep(0.3)
        request = {
            'task_id': t.id, 'goal': t.instruction, 'start_url': t.url,
            'task_class': spec.get('task_class', '') or 'live_site_audit',
            'criteria': _criteria_for(t, spec),
            'max_actions': int(t.max_steps or benchlib.DEFAULT_MAX_STEPS),
            'max_wall_seconds': float(deadline),
        }
        req_path = pathlib.Path(tempfile.mkdtemp(prefix=f'aur-{rid}-')) / 'request.json'
        req_path.write_text(json.dumps(request))
        log['setup_s'] = round(time.perf_counter() - t0, 3)

        # ---- timed: ONE runtime execute (the subprocess is the run) ----
        env = {k: v for k, v in os.environ.items()
               if not any(x in k.upper() for x in ['KEY', 'TOKEN', 'SECRET', 'PASSWORD'])}
        if benchlib.KEY:
            env['OPENROUTER_API_KEY'] = benchlib.KEY
        env['AUR_DURABILITY'] = 'file'
        env['PYDANTIC_AI_NO_BANNER'] = '1'
        t0 = time.perf_counter()
        proc = subprocess.run(
            [AUR_PY, DRIVER, '--request', str(req_path), '--cdp', f'http://127.0.0.1:{port}'],
            env=env, cwd=str(AUR), capture_output=True, text=True, timeout=deadline + 120)
        wall = time.perf_counter() - t0
        log['wall_s'] = round(wall, 3)
        log['total_s'] = round(wall, 3)
        m = None
        for line in proc.stdout.splitlines():
            if line.startswith('AURJSON'):
                try:
                    m = json.loads(line[len('AURJSON'):])
                except Exception:
                    m = None
        if m is None:
            log['driver_stdout'] = proc.stdout[-1500:]
            log['driver_stderr'] = proc.stderr[-1500:]
            log['error'] = log.get('error') or 'no AURJSON from runtime driver'
            m = {}
        log['run_id'] = m.get('run_id')
        log['runtime_verified'] = bool(m.get('verified'))
        log['runtime_status'] = m.get('status')
        log['runtime_failure_class'] = m.get('failure_class') or m.get('error')
        log['events'] = _compact_events(m.get('events'))
        metrics = m.get('metrics') or {}
        log['metrics'] = metrics
        log['manager_calls'] = metrics.get('manager_calls', 0)
        log['jev_calls'] = metrics.get('jev_calls', 0)
        log['fara_calls'] = metrics.get('fara_calls', 0)
        log['showui_calls'] = metrics.get('showui_calls', 0)
        log['actions'] = metrics.get('actions', 0)
        log['model_calls'] = (metrics.get('manager_calls', 0) or 0) + (metrics.get('jev_calls', 0) or 0)
        log['tool_calls'] = metrics.get('transport_commands', metrics.get('actions', 0))
        tokens = {'input': metrics.get('manager_input_tokens', 0) or 0,
                  'output': metrics.get('manager_output_tokens', 0) or 0,
                  'cached': 0, 'reasoning': 0}
        log['tokens'] = tokens
        log['tokens_source'] = 'runtime manager usage (Jev is a classifier.dev call, no tokens)'
        log['cost'] = benchlib.estimate_cost(tokens)
        log['done'] = bool(log['runtime_verified'])

        # ---- untimed: INDEPENDENT verification over CDP with the task's own verifier ----
        host = t.url.split('/')[2].lower() if '//' in t.url else '*'
        vout = _cdp_eval(port, host, t.verify_js)
        log['verification'] = vout
        log['independent_pass'] = bool(t.check(benchlib.parse_verify(vout)))
        # pass = independent evidence only; the runtime's own flag is reported separately.
        log['pass'] = log['independent_pass']
        log['verdict_agreement'] = (log['independent_pass'] == log['runtime_verified'])
        try:
            subprocess.run(['node', CDP_MJS, str(port), 'shot', host,
                            str(benchlib.RES / f'{rid}.png')],
                           capture_output=True, timeout=45)
        except Exception:
            pass
    except Exception as e:
        log['error'] = f'{type(e).__name__}: {e}'
        log['independent_pass'] = False
        log['pass'] = False
    finally:
        try:
            if chrome:
                chrome.kill()
        except Exception:
            pass

    (benchlib.RES / f'{rid}.json').write_text(json.dumps(log, indent=2))
    print(json.dumps({'id': rid, 'task': t.id, 'pass': log.get('pass'),
                      'runtime_verified': log.get('runtime_verified'),
                      'total_s': log.get('total_s'), 'manager_calls': log.get('manager_calls'),
                      'jev_calls': log.get('jev_calls'), 'tokens': log.get('tokens'),
                      'error': log.get('error')}))
    return log


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    reps, task = benchlib.cli_reps_and_task(argv)
    return [run_native(rep, task=task) for rep in reps]


if __name__ == '__main__':
    main()
