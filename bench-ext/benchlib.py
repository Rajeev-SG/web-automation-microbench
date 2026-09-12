# Shared library for Round 3 contenders. Derived from artifacts/2026-09-11/bench-py.py (Round 2).
# Contender runners implement: start() -> handle + observation string, act(handle, code) -> observation,
# teardown(handle), plus optional verify(handle) returning verify stdout.
#
# Issue #20: the library is task-parameterized. A benchmark task is a `Task`
# {id, instruction, url, observe_js, verify_js, check, capabilities[], provenance{}, reset/observe/verify};
# tasks live in a registry (`TASKS` / `get_task`). `run_rep(adapter, rep, task=...)` runs one rep of a
# chosen task. For backwards compatibility the default task (`todomvc`) is also bound to the historical
# module globals `TASK`, `URL_TASK`, `OBS_JS`, `VERIFY_JS`, so the 29 existing runners keep working
# unchanged: each adapter reads those globals, and `run_rep` rebinds them to the selected task.
import os, sys, json, time, subprocess, pathlib, re, urllib.request

BASE = pathlib.Path(__file__).parent
RES = pathlib.Path(os.environ.get('BENCH_RES', BASE / 'artifacts' / '2026-09-12' / 'results'))
RES.mkdir(exist_ok=True, parents=True)
KEY = os.environ.get('OPENROUTER_API_KEY', '')
ENV = {k: v for k, v in os.environ.items() if not any(x in k.upper() for x in ['KEY','TOKEN','SECRET','PASSWORD'])}
ENV['OPENROUTER_API_KEY'] = KEY
ENV['OPENROUTER_BASE_URL'] = 'https://openrouter.ai/api/v1'

# --- TodoMVC task text (verbatim; a golden-file test in bench-ext/tests guards these strings) ---
URL_TASK = 'https://demo.playwright.dev/todomvc/'

VERIFY_JS = '''JSON.stringify({url:location.href,items:Array.from(document.querySelectorAll('.todo-list li')).map(e=>({text:e.innerText.trim(),completed:e.classList.contains('completed')})),saved:JSON.parse(localStorage.getItem('react-todos')||'[]').map(x=>({title:x.title,completed:x.completed}))})'''

TASK = 'Add exactly two todos: "Email supplier" then "Review invoice". Mark ONLY "Email supplier" complete. Click the Active filter. Verify only "Review invoice" is shown and 1 item left. Do not clear completed. Work efficiently with ONE logical UI action per response (adding a todo is one action); observe before next action. Finish only after observing the final state.'

OBS_JS = '''JSON.stringify({url:location.href,text:document.body.innerText,controls:Array.from(document.querySelectorAll('input,button,a,label')).filter(e=>e.getClientRects().length).map(e=>({tag:e.tagName,type:e.type,class:e.className,text:e.textContent.trim().slice(0,60),placeholder:e.placeholder,checked:e.checked,forAttr:e.htmlFor,id:e.id})),items:Array.from(document.querySelectorAll('.todo-list li')).map(e=>({text:e.innerText.trim(),class:e.className}))})'''

# --- model / provider config (unchanged; every call goes through openrouter_payload) ---
PRICE_PER_MTOK = {'input': 0.075, 'output': 0.25, 'cached': 0.0375}  # Makora latency-sorted published rates

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
    """TodoMVC pass predicate (kept for backwards compatibility; tasks carry their own `check`)."""
    if not v: return False
    try:
        saved = v['saved']
        return ('#/active' in v['url']) and len(v['items']) == 1 and 'Review invoice' in v['items'][0]['text'] \
            and not v['items'][0]['completed'] \
            and sorted((x['title'], x['completed']) for x in saved) == [('Email supplier', True), ('Review invoice', False)]
    except Exception:
        return False

def estimate_cost(tokens):
    """Cost in USD from token counts at the latency-sorted provider's published rate."""
    return round(sum((tokens.get(k) or 0) * v for k, v in PRICE_PER_MTOK.items()) / 1_000_000, 8)


# --- replication config (issue #1: adaptive replication; issue #20 step 2) -----------------------
# One place for rep counts, so no runner is hardcoded to ['1', '2'].
REP_TOPOLOGY = {
    'screen': 2,      # Stage A: cheap screening of every harness x task
    'promote': 5,     # Stage B: plausible Pareto-frontier candidates
    'tiebreak': 10,   # only genuine near-ties / high variance
}
DEFAULT_REPS = [str(i) for i in range(1, REP_TOPOLOGY['screen'] + 1)]   # ['1', '2']


def reps_from_argv(argv):
    """Standard runner main(): explicit reps from argv, else the screening plan."""
    return list(argv) or list(DEFAULT_REPS)


def promotion_verdict(results, screen=REP_TOPOLOGY['screen']):
    """Decide a contender's next stage from its screening reps (issue #1 topology).

    Returns {'stage': 'stop'|'promote', 'reps': N, 'reason': ...}. Every failed rep is
    preserved as evidence; a failure is never replaced by a retry. 'dominated'/'near-tie'
    are supplied by the caller's Pareto analysis because they are cross-contender facts.
    """
    reps = [r for r in results if isinstance(r, dict)]
    passes = sum(1 for r in reps if r.get('pass'))
    n = len(reps)
    if n == 0:
        return {'stage': 'promote', 'reps': screen, 'reason': 'no reps yet'}
    if passes == 0:
        return {'stage': 'stop', 'reps': n, 'reason': 'repeatedly failing (0 passes)'}
    return {'stage': 'promote', 'reps': REP_TOPOLOGY['promote'],
            'reason': f'{passes}/{n} passed screening'}


# --- task registry -------------------------------------------------------------------------------
class Task:
    """A benchmark task.

    Documented shape (issue #20): ``{id, instruction, reset, observe, verify, url, capabilities[], provenance{}}``.
    In this adapter-based library the tool mechanics live on the adapter (start/act/verify/screenshot),
    so a task supplies the *what* and the *check*, and the adapter supplies the *how*:

    - ``instruction``  : the verbatim text handed to the model (bound to ``benchlib.TASK``).
    - ``url``          : the task's start URL (bound to ``benchlib.URL_TASK``).
    - ``observe_js``   : state-snapshot JS the adapter evaluates (bound to ``benchlib.OBS_JS``).
    - ``verify_js``    : independent verification JS the adapter evaluates (bound to ``benchlib.VERIFY_JS``).
    - ``check``        : pass predicate over the parsed verify output (never the agent's own "done").
    - ``capabilities`` : capability tags this task stresses.
    - ``provenance``   : REQUIRED {source_session_id, source_url, verified_against} for real-work tasks
                         (``source: controlled-instrument`` for TodoMVC). Enforced by ``validate_task``.
    - ``reset``/``observe``/``verify`` : optional overrides; default to the adapter's own mechanics.
    """

    REQUIRED_PROVENANCE = ('source_session_id', 'source_url', 'verified_against')

    def __init__(self, id, instruction, url, observe_js, verify_js, check,
                 capabilities=(), provenance=None, reset=None, level='deterministic'):
        self.id = id
        self.instruction = instruction
        self.url = url
        self.observe_js = observe_js
        self.verify_js = verify_js
        self.check = check
        self.capabilities = list(capabilities)
        self.provenance = dict(provenance or {})
        self.reset_override = reset
        self.level = level

    # --- spec-facing helpers (default to the adapter's own mechanics) ---
    def reset(self, adapter):
        """Pre-timer state hygiene; default no-op because ``adapter.start()`` resets state."""
        return self.reset_override(adapter) if self.reset_override else None

    def observe(self, adapter, handle):
        return adapter.observe(handle) if hasattr(adapter, 'observe') else None

    def verify(self, adapter, handle):
        return adapter.verify(handle)

    def bind(self):
        """Bind this task to the historical module globals so existing adapters see it."""
        global TASK, URL_TASK, OBS_JS, VERIFY_JS
        TASK, URL_TASK, OBS_JS, VERIFY_JS = self.instruction, self.url, self.observe_js, self.verify_js
        return self


TASKS = {}


def register(task):
    TASKS[task.id] = task
    return task


_TASK_MODULES = ('tasks_real',)


def get_task(task=None):
    """Resolve a task id (or Task, or None -> the default TodoMVC task).

    Real-work tasks live in separate modules (e.g. `tasks_real`); they are imported
    lazily the first time an unknown id is requested, so runners can name any task id.
    """
    if isinstance(task, Task):
        return task
    tid = task or DEFAULT_TASK_ID
    if tid not in TASKS:
        for mod in _TASK_MODULES:
            try:
                __import__(mod)
            except Exception:
                continue
    return TASKS[tid]


DEFAULT_TASK_ID = 'todomvc'

# TodoMVC: latency microbenchmark only, never capability evidence (see docs/task-suite-v1.md).
register(Task(
    id='todomvc',
    instruction=TASK,
    url=URL_TASK,
    observe_js=OBS_JS,
    verify_js=VERIFY_JS,
    check=check_pass,
    capabilities=['dom', 'state'],
    provenance={
        'source': 'controlled-instrument',
        'source_session_id': 'a308af6a96316e9f148c7ce6d4153c10f1fe3b25cfb873de00c754f26051967f',
        'source_url': 'https://demo.playwright.dev/todomvc/',
        'verified_against': 'benchlib.check_pass(dom-state): #/active, one item "Review invoice", react-todos persisted',
    },
    level='deterministic',
))


# --- generic GLM agent loop over a contender handle ----------------------------------------------
# adapter must provide:
#   name, doc (system prompt), start() -> (handle, initial_observation)  [pre-timer]
#   act(handle, code) -> (observation string, elapsed_seconds)  [in-loop; may be a bare string]
#   verify(handle) -> verify stdout  [post-timer]
#   screenshot(handle, path)  [post-timer]
#   teardown(handle)
def cli_reps_and_task(argv):
    """Parse runner argv into (reps, task_id). `--task=<id>` may appear anywhere."""
    task, reps = None, []
    for a in argv:
        if a.startswith('--task='):
            task = a.split('=', 1)[1] or None
        else:
            reps.append(a)
    return reps_from_argv(reps), task


def run_cli(factory, argv=None, max_steps=10, timeout=180):
    """Standard runner entrypoint: reps + `--task=<id>` from argv, one run_rep per rep.

    `factory` is any zero-argument callable returning a fresh adapter (usually the class).
    Keeps runner `__main__` blocks one line and makes every contender able to run any
    registered task, which is the point of the task-parameterized library (issue #20).
    """
    argv = list(sys.argv[1:] if argv is None else argv)
    reps, task = cli_reps_and_task(argv)
    return [run_rep(factory(), rep, task=task, max_steps=max_steps, timeout=timeout) for rep in reps]


def run_rep(adapter, rep, task=None, max_steps=10, timeout=180):
    task = get_task(task)
    task.bind()
    rid = f'{rep}-{adapter.name}'
    log = {'id': rid, 'contender': adapter.name, 'rep': rep, 'task': task.id, 'events': []}
    if task.reset_override:
        task.reset(adapter)
    handle, obs = adapter.start()
    log['setup_s'] = handle.get('setup_s', 0) if isinstance(handle, dict) else 0
    msgs = [{'role': 'system', 'content': adapter.doc}, {'role': 'user', 'content': task.instruction + '\nInitial browser observation:\n' + obs[-6000:]}]
    start = time.perf_counter(); api = 0; browser = 0
    tokens = {'input':0,'output':0,'cached':0,'reasoning':0}
    providers = []
    done = False; error = None
    tool_calls = 0; tool_errors = 0; retries = 0; recoveries = 0
    seen_codes = set(); last_code = None; last_errored = False
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
            if data.get('provider'):
                providers.append(data['provider'])
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
            # diagnostics: retries / recovery (cheaply observable)
            if code and code == last_code:
                retries += 1
            if code and code in seen_codes and last_errored:
                recoveries += 1
            seen_codes.add(code); last_code = code
            tool_calls += 1
            try:
                result = adapter.act(handle, code)
                if isinstance(result, tuple):
                    obs, bdt = result
                else:
                    obs, bdt = result, 0.0
                tool_err = False
            except Exception as e:
                obs, bdt = f'error: {type(e).__name__}: {e}', 0.0
                tool_err = True; tool_errors += 1
            last_errored = tool_err
            browser += bdt
            ev.update(browser_s=round(bdt,3), code=code, tool_error=tool_err, observation=obs[-4000:])
            msgs.append({'role': 'user', 'content': 'Browser observation:\n' + obs[-6000:]})
            if time.perf_counter() - start > timeout:
                error = 'timeout'; break
    except Exception as e:
        error = f'{type(e).__name__}: {e}'
    log.update(total_s=round(time.perf_counter()-start,3), api_s=round(api,3), browser_s=round(browser,3),
               model_calls=len(log['events']), tool_calls=tool_calls, tool_errors=tool_errors,
               retries=retries, recovery=recoveries,
               provider=sorted(set(providers)) or None,
               tokens=tokens, cost=estimate_cost(tokens), done=done, error=error)
    try:
        vout = task.verify(adapter, handle)
        log['verification'] = vout
        log['pass'] = bool(task.check(parse_verify(vout)) and done)
    except Exception as e:
        log['verification'] = f'verify error: {e}'; log['pass'] = False
    try: adapter.screenshot(handle, str(RES / f'{rid}.png'))
    except Exception as e: log['screenshot_error'] = str(e)
    try: adapter.teardown(handle)
    except Exception: pass
    (RES / f'{rid}.json').write_text(json.dumps(log, indent=2))
    print(json.dumps({'id': rid, 'task': task.id, 'pass': log['pass'], 'total_s': log['total_s'], 'model_calls': log['model_calls'], 'tool_calls': tool_calls, 'tokens': tokens, 'error': error}))
    return log
