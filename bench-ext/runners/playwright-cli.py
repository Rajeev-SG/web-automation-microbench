#!/usr/bin/env python3
# Round 6 adapter: Microsoft playwright-cli (Skills/CLI path, NOT Playwright MCP).
# Source: work/playwright-cli @ 655530f; CLI: npm i -g @playwright/cli -> 0.1.19.
#
# Native interface: the model issues ONE `playwright-cli` command per step (CLI + Skills path);
# GLM 5.3-Flash stays the decision-maker via the shared benchlib loop. Snapshot/ref interaction
# model preserved: `snapshot` returns YAML with eN refs; actions target those refs.
# Browser connection mode: the CLI launches and manages its own Chromium (`playwright-cli open`),
# the tool's default agent path (its `attach --cdp` daemon exits 1 here, so attach was not used).
# Setup (untimed): `playwright-cli close-all` then `open <task url>` -> fresh browser per rep.
import sys, json, subprocess, os, time, pathlib, re
sys.path.insert(0, '/Users/rajeev/Code/web-automation-microbench/bench-ext')
import benchlib

benchlib.RES = pathlib.Path('/Users/rajeev/Code/web-automation-microbench/bench-ext/artifacts/2026-09-14/results')
benchlib.RES.mkdir(parents=True, exist_ok=True)
CWD = '/Users/rajeev/Code/web-automation-microbench/bench-ext'
SESSION = 'bench6'


def _result_json(out):
    """Pull the JSON value out of playwright-cli's `### Result` section.

    `eval` prints:  ### Result\n"{\\"url\\":...}"\n### Ran Playwright code\n...
    Adapter-side output parsing only (no task-specific logic).
    """
    s = out or ''
    m = re.search(r'###\s*Result\s*\n(.*?)(?:\n###|\Z)', s, re.S)
    if not m:
        return s.strip()
    v = m.group(1).strip()
    try:
        d = json.loads(v)
        return d if isinstance(d, str) else json.dumps(d)
    except Exception:
        return v.strip('"').replace('\\"', '"')


class PlaywrightCli:
    name = 'playwright-cli'
    doc = ('Drive a real Chrome ONLY with the playwright-cli CLI (Skills path). One logical action per '
           'step; each response is {"code":"<playwright-cli args, WITHOUT the playwright-cli prefix>"}. '
           'Start by inspecting with `snapshot` (YAML with eN refs). Verbs: snapshot; click <eN>; '
           'fill <eN> "<text>"; press <key> (e.g. press Enter); check <eN>; eval "<fn>"; screenshot; '
           'reload. Adding a todo is TWO commands: fill the textbox ref, then press Enter — issue them '
           'as separate steps. To tick only "Email supplier", click/check the checkbox ref in its row. '
           'Open the Active filter by clicking the "Active" link ref. Default to refs from the latest '
           'snapshot rather than CSS selectors. Respond as strict JSON {"code":"..."} per step, and '
           '{"done":true} once the observed state is: Active filter, only "Review invoice" visible, '
           '1 item left. Strict JSON only, no prose.')
    def __init__(self):
        pass
    def _cli(self, args, timeout=60):
        r = subprocess.run(['playwright-cli', f'-s={SESSION}'] + list(args), capture_output=True,
                           text=True, timeout=timeout, cwd=CWD)
        return (r.stdout + r.stderr).strip()
    def start(self):
        t0 = time.perf_counter()
        self._cli(['close-all'], timeout=30)          # fresh browser per rep (state hygiene)
        time.sleep(0.5)
        self._cli(['open', benchlib.URL_TASK], timeout=90)
        time.sleep(0.8)
        self._cli(['eval', "() => { localStorage.removeItem('react-todos'); location.reload(); }"], timeout=30)
        time.sleep(2.0)
        obs = self._cli(['eval', benchlib.OBS_JS], timeout=45)
        return {'setup_s': round(time.perf_counter() - t0, 3)}, _result_json(obs)
    def act(self, handle, code):
        t = time.perf_counter()
        import shlex
        c = (code or '').strip()
        if c.startswith('playwright-cli'):
            c = c[len('playwright-cli'):].strip()
        try:
            toks = shlex.split(c)
        except ValueError:
            toks = c.split()
        try:
            out = self._cli(toks, timeout=60)
        except Exception as e:
            out = f'error: {e}'
        obs = self._cli(['eval', benchlib.OBS_JS], timeout=45)
        return out + '\n' + _result_json(obs), time.perf_counter() - t
    def verify(self, handle):
        return _result_json(self._cli(['eval', benchlib.VERIFY_JS], timeout=45))
    def screenshot(self, handle, path):
        # playwright-cli's `screenshot` takes an optional *target*, and writes via --filename.
        try:
            self._cli(['screenshot', '--filename', path, '--full-page'], timeout=45)
        except Exception as e:
            print(f'screenshot error: {e}', file=sys.stderr)
    def teardown(self, handle):
        try:
            self._cli(['close-all'], timeout=20)
        except Exception:
            pass


if __name__ == '__main__':
    reps = benchlib.reps_from_argv(sys.argv[1:])
    for rep in reps:
        benchlib.run_rep(PlaywrightCli(), rep, max_steps=14)
