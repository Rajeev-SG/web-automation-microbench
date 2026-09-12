# Shared library for Round 3 contenders. Derived from artifacts/2026-09-11/bench-py.py (Round 2).
# Contender runners implement: setup() -> handle + observation string, step(handle, code) -> observation,
# teardown(handle), plus optional verify(handle) returning verify stdout. Uses shared TASK, VERIFY_JS,
# OpenRouter config, pass predicate, and JSON schema from the spec.
import os, json, time, subprocess, pathlib, re, urllib.request

BASE = pathlib.Path(__file__).parent
RES = BASE / 'artifacts' / '2026-09-12' / 'results'
RES.mkdir(exist_ok=True, parents=True)
URL_TASK = 'https://demo.playwright.dev/todomvc/'
KEY = os.environ.get('OPENROUTER_API_KEY', '')
ENV = {k: v for k, v in os.environ.items() if not any(x in k.upper() for x in ['KEY','TOKEN','SECRET','PASSWORD'])}
ENV['OPENROUTER_API_KEY'] = KEY
ENV['OPENROUTER_BASE_URL'] = 'https://openrouter.ai/api/v1'

VERIFY_JS = '''JSON.stringify({url:location.href,items:Array.from(document.querySelectorAll('.todo-list li')).map(e=>({text:e.innerText.trim(),completed:e.classList.contains('completed')})),saved:JSON.parse(localStorage.getItem('react-todos')||'[]').map(x=>({title:x.title,completed:x.completed}))})'''

TASK = 'Add exactly two todos: "Email supplier" then "Review invoice". Mark ONLY "Email supplier" complete. Click the Active filter. Verify only "Review invoice" is shown and 1 item left. Do not clear completed. Work efficiently with ONE logical UI action per response (adding a todo is one action); observe before next action. Finish only after observing the final state.'

OBS_JS = '''JSON.stringify({url:location.href,text:document.body.innerText,controls:Array.from(document.querySelectorAll('input,button,a,label')).filter(e=>e.getClientRects().length).map(e=>({tag:e.tagName,type:e.type,class:e.className,text:e.textContent.trim().slice(0,60),placeholder:e.placeholder,checked:e.checked,forAttr:e.htmlFor,id:e.id})),items:Array.from(document.querySelectorAll('.todo-list li')).map(e=>({text:e.innerText.trim(),class:e.className}))})'''

def openrouter_payload(msgs):
    return {'model': 'z-ai/glm-5.3-flash', 'messages': msgs, 'max_tokens': 2200, 'temperature': 0,
            'reasoning': {'effort': 'low', 'exclude': True}, 'response_format': {'type': 'json_object'},
            'provider': {'sort': 'latency'}}

def openrouter_call(msgs):
    req = urllib.request.Request('https://openrouter.ai/api/v1/chat/completions', data=json.dumps(openrouter_payload(msgs)).encode(),
                                 headers={'Authorization': 'Bearer ' + KEY, 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=90) as response:
        return json.load(response)

def parse_verify(out):
    # agent-browser eval returns the VERIFY_JS JSON as a quoted/escaped string: peel the
    # outer quotes first, then unescape \" so the regex sees a plain object.
    s = (out or '').strip()
    if len(s) >= 2 and s[0] == s[-1] == '"':
        try:
            inner = json.loads(s)  # strip one layer of quoting
            if isinstance(inner, str):
                s = inner
        except Exception:
            s = s[1:-1]
        s = s.replace('\\"', '"')
    m = re.search(r'\{.*\}', s, re.S)
    if not m: return None
    try: return json.loads(m.group(0))
    except Exception: return None

def check_pass(v):
    if not v: return False
    try:
        saved = v['saved']
        return ('#/active' in v['url']) and len(v['items']) == 1 and 'Review invoice' in v['items'][0]['text'] \
            and not v['items'][0]['completed'] \
            and sorted((x['title'], x['completed']) for x in saved) == [('Email supplier', True), ('Review invoice', False)]
    except Exception:
        return False

# Generic GLM agent loop over a contender handle. adapter must provide:
#   name, doc (system prompt), start() -> (handle, initial_observation)  [pre-timer]
#   act(handle, code) -> observation string  [in-loop]
#   verify(handle) -> verify stdout  [post-timer]
#   screenshot(handle, path)  [post-timer]
#   teardown(handle)
def run_rep(adapter, rep, max_steps=10, timeout=180):
    rid = f'{rep}-{adapter.name}'
    log = {'id': rid, 'contender': adapter.name, 'rep': rep, 'events': []}
    handle, obs = adapter.start()
    log['setup_s'] = handle.get('setup_s', 0) if isinstance(handle, dict) else 0
    msgs = [{'role': 'system', 'content': adapter.doc}, {'role': 'user', 'content': TASK + '\nInitial browser observation:\n' + obs[-6000:]}]
    start = time.perf_counter(); api = 0
    tokens = {'input':0,'output':0,'cached':0,'reasoning':0}
    done = False; error = None
    try:
        for step in range(max_steps):
            t = time.perf_counter()
            data = openrouter_call(msgs)
            dt = time.perf_counter() - t; api += dt
            u = data.get('usage') or {}
            tokens['input'] += u.get('prompt_tokens') or 0
            tokens['output'] += u.get('completion_tokens') or 0
            tokens['cached'] += (u.get('prompt_tokens_details') or {}).get('cached_tokens') or 0
            tokens['reasoning'] += (u.get('completion_tokens_details') or {}).get('reasoning_tokens') or 0
            content = data['choices'][0]['message'].get('content') or ''
            try: a = json.loads(content)
            except Exception:
                a = {'code': content, 'parse_error': True}
            ev = {'step': step+1, 'api_s': round(dt,3), 'provider': data.get('provider'), 'request_id': data.get('id'), 'usage': u, 'answer': a if not a.get('parse_error') else 'UNPARSEABLE'}
            log['events'].append(ev)
            msgs.append({'role': 'assistant', 'content': content})
            if a.get('done'):
                done = True; break
            code = a.get('code') or a.get('command') or ''
            obs, bdt = adapter.act(handle, code)
            ev.update(browser_s=round(bdt,3), code=code, observation=obs[-4000:])
            msgs.append({'role': 'user', 'content': 'Browser observation:\n' + obs[-6000:]})
            if time.perf_counter() - start > timeout:
                error = 'timeout'; break
    except Exception as e:
        error = f'{type(e).__name__}: {e}'
    log.update(total_s=round(time.perf_counter()-start,3), api_s=round(api,3), model_calls=len(log['events']),
               tokens=tokens, done=done, error=error)
    try:
        vout = adapter.verify(handle)
        log['verification'] = vout
        log['pass'] = bool(check_pass(parse_verify(vout)) and done)
    except Exception as e:
        log['verification'] = f'verify error: {e}'; log['pass'] = False
    try: adapter.screenshot(handle, str(RES / f'{rid}.png'))
    except Exception as e: log['screenshot_error'] = str(e)
    try: adapter.teardown(handle)
    except Exception: pass
    (RES / f'{rid}.json').write_text(json.dumps(log, indent=2))
    print(json.dumps({'id': rid, 'pass': log['pass'], 'total_s': log['total_s'], 'model_calls': log['model_calls'], 'tokens': tokens, 'error': error}))
    return log
