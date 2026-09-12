#!/usr/bin/env python3
"""Runner: Taylor-Bayouth/browser-agent — the ORIGINAL of the two same-name `browser-agent` projects.

Not benchlib-loop driven: it ships its own agent loop, so it is timed as ONE `agent.js`
run (like notte / page-agent / Magnitude).

How it is driven
----------------
- Provider: a small OpenRouter adapter (setup-written) lives at lib/providers/openrouter.js and is
  registered by run-openrouter.js; the stock agent entry point is then invoked with
  --provider openrouter. Config points every model role at z-ai/glm-5.3-flash and the adapter
  sends provider.sort=latency.
- Browser: the tool insists on its own isolated profile (~/.browser-agent/profile). That profile
  PERSISTS, so a previous run's tabs get restored and the agent works the wrong page. We therefore
  reset the profile, pre-launch Chrome via the tool's own `launch()`, and navigate the page to the
  task URL before the timer starts — the tool's preflight then finds that Chrome alive and attaches.
- Its OpenAI-tuned 10s per-call timeout is raised to 30s in config (OpenRouter/GLM is slower; the
  benchlib contenders use 90s). Both deviations are recorded in the run artifact + README.
"""
import sys, os, re, json, time, subprocess, pathlib, shutil
sys.path.insert(0, '/Users/rajeev/Code/web-automation-microbench/bench-ext')
import benchlib, cft_chrome

BA = '/Users/rajeev/Code/web-automation-microbench/bench-ext/work/browser-agent'
CFT = cft_chrome.CFT
CDPJS = '/Users/rajeev/Code/web-automation-microbench/bench-ext/cdp.mjs'
PROFILE = str(pathlib.Path.home() / '.browser-agent' / 'profile')
PORT = 9296


def kill_own_profile_chrome():
    """Kill ONLY Chrome running the tool's isolated profile (never the user's browser)."""
    try:
        out = subprocess.run(['pgrep', '-f', '--', '--user-data-dir=' + PROFILE],
                             capture_output=True, text=True, timeout=20)
    except Exception:
        return
    pids = [x for x in out.stdout.split() if x.strip()]
    for pid in pids:
        subprocess.run(['kill', '-9', pid], capture_output=True)
    if pids:
        time.sleep(1.5)


def cdp(mode, url_sub, arg, timeout=90):
    r = subprocess.run(['node', CDPJS, str(PORT), mode, url_sub, arg],
                       capture_output=True, text=True, timeout=timeout)
    return (r.stdout + r.stderr).strip()


def main(rep):
    global PORT
    rid = f'{rep}-browser-agent-tb'
    log = {'id': rid, 'contender': 'browser-agent-tb', 'rep': rep, 'events': []}
    key = os.environ.get('OPENROUTER_API_KEY', '')
    try:
        t_setup = time.perf_counter()
        # The tool's Chrome uses a PERSISTENT isolated profile and launch() EARLY-RETURNS the
        # existing port if a previous run's Chrome is still alive — so a stale browser (with a
        # stale session on the wrong page) would be reused. Kill that instance first, then wipe
        # the profile. Only ever this profile's Chrome; the user's own browser is untouched.
        kill_own_profile_chrome()
        if os.path.exists(PROFILE):
            shutil.rmtree(PROFILE)          # no restored tabs from a previous run
        env = {**os.environ, 'OPENROUTER_API_KEY': key, 'BROWSER_AGENT_CHROME_PATH': CFT}
        # 1) pre-launch the tool's own isolated Chrome through its own launch()
        r = subprocess.run(
            ['node', '-e',
             "require('./lib/launch').launch({port:%d, executablePath:process.env.BROWSER_AGENT_CHROME_PATH})"
             ".then(p=>{console.log('PORT='+p);process.exit(0)})"
             ".catch(e=>{console.error('launch failed: '+e.message);process.exit(1)})" % PORT],
            cwd=BA, env=env, capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            raise RuntimeError('pre-launch failed: ' + (r.stdout + r.stderr)[-400:])
        m = re.search(r'PORT=(\d+)', r.stdout)
        if not m:
            raise RuntimeError('could not read the launch port: ' + (r.stdout + r.stderr)[-300:])
        PORT = int(m.group(1))
        log['port'] = PORT
        # 2) put the task page in front, clean state
        time.sleep(1)
        # '*' = first page target: a fresh Chrome opens chrome://newtab/, so matching on
        # about:blank silently no-ops and the agent starts on a blank tab.
        cdp('eval', '*', f"location.href={json.dumps(benchlib.URL_TASK)}", timeout=60)
        time.sleep(3)
        cdp('eval', 'todomvc', "localStorage.removeItem('react-todos'); location.reload();", timeout=60)
        time.sleep(3)
        # assert the task page really is in front before the timer starts
        probe = cdp('eval', 'todomvc', "location.href")
        if 'todomvc' not in probe:
            raise RuntimeError('pre-navigation failed; page is: ' + probe[:160])
        log['setup_url'] = probe[:120]
        log['setup_s'] = round(time.perf_counter() - t_setup, 3)
        log['setup_notes'] = ('fresh profile; Chrome pre-launched via the tool\'s own launch(); '
                              'task URL pre-loaded; model timeouts raised 10s->30s for OpenRouter')
        # 3) timed run
        start = time.perf_counter()
        run = subprocess.run(
            ['node', 'run-openrouter.js', '--task', benchlib.TASK,
             '--provider', 'openrouter', '--model-id', 'z-ai/glm-5.3-flash'],
            cwd=BA, env=env, capture_output=True, text=True, timeout=900)
        log['total_s'] = round(time.perf_counter() - start, 3)
        log['returncode'] = run.returncode
        log['stderr_tail'] = run.stderr[-2500:]
        log['stdout_tail'] = run.stdout[-2500:]
        log['model_calls'] = 'n/a (own loop)'
        log['tokens'] = {'input': 0, 'output': 0, 'cached': 0, 'reasoning': 0}
        log['tokens_source'] = 'in-process; stats in stdout_tail (stats.inputTokens/outputTokens)'
        log['done'] = run.returncode == 0
        # 4) independent verification (own JS, not the agent's word)
        vout = cdp('eval', 'todomvc', benchlib.VERIFY_JS)
        log['verification'] = vout
        log['pass'] = bool(benchlib.check_pass(benchlib.parse_verify(vout)))
        try: cdp('shot', 'todomvc', str(benchlib.RES / f'{rid}.png'))
        except Exception as e: log['screenshot_error'] = str(e)
    except Exception as e:
        import traceback
        log['error'] = f'{type(e).__name__}: {e}'
        log['trace'] = traceback.format_exc()[-1200:]
        log.setdefault('pass', False)
    finally:
        # only our own isolated profile's Chrome; the user's browser is untouched
        try:
            kill_own_profile_chrome()
        except Exception: pass
    (benchlib.RES / f'{rid}.json').write_text(json.dumps(log, indent=2))
    print(json.dumps({'id': rid, 'pass': log.get('pass'), 'total_s': log.get('total_s'),
                      'rc': log.get('returncode'), 'error': log.get('error')}))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '1')
