#!/usr/bin/env python3
# Round 3 fix-up runner: Notte (nottelabs/notte) 1.9.0 in a Python 3.12 uv venv.
# Blocker cleared 2026-09-12: Notte runs locally (patchright) and its agent LLM is pointed at
# OpenRouter/GLM via NOTTE_CONFIG_PATH -> reasoning_model="openrouter/z-ai/glm-5.3-flash" plus
# ENABLE_OPENROUTER=true and OPENROUTER_API_KEY. Notte ships its own agent runtime, so it is timed
# as ONE Agent.run (like Magnitude/BrowserCode/page-agent), not driven by the shared benchlib loop.
# TASK / VERIFY_JS / check_pass / URL_TASK / JSON schema come from benchlib.
import sys, os, json, time
sys.path.insert(0, '/Users/rajeev/Code/web-automation-microbench/bench-ext')
import benchlib

os.environ.setdefault('ENABLE_OPENROUTER', 'true')
os.environ.setdefault('NOTTE_CONFIG_PATH', '/tmp/notte-bench.toml')

VENV = '/tmp/notte-venv/bin/python'


def main(rep):
    rid = f'{rep}-notte'
    log = {'id': rid, 'contender': 'notte', 'rep': rep, 'events': []}
    try:
        # the runner file is literally named notte.py, so drop its own dir from sys.path
        _here = os.path.dirname(os.path.abspath(__file__))
        sys.path[:] = [q for q in sys.path if os.path.abspath(q or '.') != _here]
        import notte
        from notte import Session, Agent
        t_setup = time.perf_counter()
        session = Session(headless=True)
        session.start()
        log['setup_s'] = round(time.perf_counter() - t_setup, 3)
        agent = Agent(session=session)
        start = time.perf_counter()
        resp = agent.run(task=benchlib.TASK, url=benchlib.URL_TASK)
        log['total_s'] = round(time.perf_counter() - start, 3)
        try:
            log['agent_result'] = {'success': bool(getattr(resp, 'success', False)),
                                   'answer': str(getattr(resp, 'answer', resp))[:2000]}
        except Exception:
            log['agent_result'] = str(resp)[:2000]
        log['model_calls'] = 1
        log['done'] = bool(getattr(resp, 'success', False))
        log['tokens'] = {'input': 0, 'output': 0, 'cached': 0, 'reasoning': 0}
        log['tokens_source'] = 'n/a (agent runs inside notte)'
        vout = session.evaluate_js(benchlib.VERIFY_JS)
        log['verification'] = vout
        log['pass'] = bool(benchlib.check_pass(benchlib.parse_verify(vout)) and log['done'])
        try:
            shot = session.screenshot()
            raw = getattr(shot, 'raw', None) or (shot if isinstance(shot, (bytes, bytearray)) else None)
            if raw:
                (benchlib.RES / f'{rid}.png').write_bytes(raw)
            else:
                log['screenshot_error'] = f'unexpected screenshot type {type(shot)}'
        except Exception as e:
            log['screenshot_error'] = str(e)
        try: session.stop()
        except Exception: pass
    except Exception as e:
        import traceback
        log['error'] = f'{type(e).__name__}: {e}'
        log['trace'] = traceback.format_exc()[-1500:]
        log.setdefault('pass', False)
    (benchlib.RES / f'{rid}.json').write_text(json.dumps(log, indent=2))
    print(json.dumps({'id': rid, 'pass': log.get('pass'), 'total_s': log.get('total_s'), 'error': log.get('error')}))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '1')
