#!/usr/bin/env python3
"""Round 6 summary builder: reads artifacts/2026-09-12-round6/results/*.json and emits summary.json."""
import json, pathlib, statistics

RES = pathlib.Path('/Users/rajeev/Code/web-automation-microbench/bench-ext/artifacts/2026-09-12-round6/results')
IN_RATE, OUT_RATE = 0.075 / 1e6, 0.25 / 1e6


def cost_of(tok):
    if not tok:
        return None
    inp = tok.get('input') or 0
    cached = min(tok.get('cached') or 0, inp)
    return round((inp - cached) * IN_RATE + cached * IN_RATE / 2 + (tok.get('output') or 0) * OUT_RATE, 8)


rows = {}
for p in sorted(RES.glob('*.json')):
    if p.name.startswith('_'):
        continue
    d = json.loads(p.read_text())
    name = d.get('contender')
    if not name or name not in p.name:
        continue
    r = rows.setdefault(name, {'contender': name, 'reps': [], 'passes': 0})
    r['reps'].append(d)
    r['passes'] += 1 if d.get('pass') else 0

out = []
for name, r in sorted(rows.items()):
    reps = r['reps']
    times = sorted(d['total_s'] for d in reps if d.get('total_s'))
    toks = [d.get('tokens') or {} for d in reps]
    inner = [d.get('tool_internal_llm') or {} for d in reps]
    total_in = sum(t.get('input') or 0 for t in toks) + sum(i.get('inputTokens') or 0 for i in inner)
    total_out = sum(t.get('output') or 0 for t in toks) + sum(i.get('outputTokens') or 0 for i in inner)
    costs = [d['cost'] for d in reps if d.get('cost') is not None]
    costs += [d['cost_usd'] for d in reps if d.get('cost_usd') is not None]
    if costs:
        cpr, csrc = round(statistics.mean(costs), 8), 'tool-reported'
    else:
        cpr, csrc = cost_of({'input': total_in, 'output': total_out}), 'tokens x rate card'
    out.append({
        'contender': name, 'reps': len(reps), 'passes': r['passes'],
        'median_s': round(statistics.median(times), 2) if times else None,
        'times_s': [round(t, 2) for t in times],
        'tok_in_avg': round(total_in / len(reps)), 'tok_out_avg': round(total_out / len(reps)),
        'cost_per_run_usd': cpr, 'cost_source': csrc,
        'inner_llm_calls_avg': round(sum(i.get('calls') or 0 for i in inner) / len(reps), 1) if any(inner) else None,
        'tok_cache_avg': round(sum(t.get('cached') or 0 for t in toks) / len(reps)),
        'note': next((d.get('note') for d in reps if d.get('note')), ''),
    })

path = RES.parent / 'summary.json'
path.write_text(json.dumps(out, indent=2))
print(json.dumps(rows and out, indent=1)[:60])
for r in out:
    print(f"{r['contender']:22s} {r['passes']}/{r['reps']}  median={r['median_s']}  in/out={r['tok_in_avg']}/{r['tok_out_avg']}  ${r['cost_per_run_usd']}")
