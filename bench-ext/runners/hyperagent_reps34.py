import sys, json
sys.path.insert(0, '/Users/rajeev/Code/web-automation-microbench/bench-ext')
sys.path.insert(0, '/Users/rajeev/Code/web-automation-microbench/bench-ext/runners')
import benchlib
from hyperagent import HyperAgent
for rep in ['3','4']:
    a = HyperAgent()
    benchlib.run_rep(a, rep)
    try: inner = a.inner_usage()
    except Exception as e: inner = {'error': str(e)}
    p = benchlib.RES / f'{rep}-{a.name}.json'
    d = json.loads(p.read_text()); d['tool_internal_llm'] = inner
    d['note'] = ('HyperAgent opens its own local Playwright Chromium (headless); bench-side fetch wrapper '
                 'injects provider.sort=latency and tallies tool-internal usage. Extra reps for variance.')
    p.write_text(json.dumps(d, indent=2))
    print(json.dumps({'id': d['id'], 'pass': d['pass'], 'total_s': d['total_s'], 'inner': inner}))
