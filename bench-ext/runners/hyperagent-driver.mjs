// HyperAgent bridge: holds a HyperAgent instance and executes one native call per stdin
// JSON command, so the shared benchlib GLM loop stays the decision-maker.
// Native interface: HyperPage.perform(instruction) [accessibility-tree granular action],
// plus the autonomous HyperPage.ai()/executeTask path for the capability row.
//
// Benchmark-side instrumentation (no upstream source modified): global fetch is wrapped so
// every OpenRouter request (a) is tagged with provider.sort="latency" and (b) has its
// usage/provider recorded. HyperAgent itself exposes no token telemetry.
import { createRequire } from 'node:module';
import readline from 'node:readline';
const require = createRequire('/Users/rajeev/Code/web-automation-microbench/bench-ext/work/hyperagent/');
const { HyperAgent } = require('/Users/rajeev/Code/web-automation-microbench/bench-ext/work/hyperagent/dist/index.js');

const KEY = process.env.OPENROUTER_API_KEY;
const MODEL = 'z-ai/glm-5.3-flash';
const usage = { inputTokens: 0, outputTokens: 0, calls: 0, providers: {} };

const realFetch = globalThis.fetch;
globalThis.fetch = async (url, opts = {}) => {
  const u = typeof url === 'string' ? url : (url && url.url) || '';
  if (u.includes('openrouter.ai') && opts && typeof opts.body === 'string') {
    try {
      const b = JSON.parse(opts.body);
      b.provider = { sort: 'latency' };
      opts = { ...opts, body: JSON.stringify(b) };
    } catch {}
  }
  const res = await realFetch(url, opts);
  if (u.includes('openrouter.ai')) {
    try {
      const j = await res.clone().json();
      if (j && j.usage) {
        usage.inputTokens += j.usage.prompt_tokens || 0;
        usage.outputTokens += j.usage.completion_tokens || 0;
        usage.calls += 1;
      }
      if (j && j.provider) usage.providers[j.provider] = (usage.providers[j.provider] || 0) + 1;
    } catch {}
  }
  return res;
};

let agent = null, page = null;
const send = (o) => process.stdout.write(JSON.stringify(o) + '\n');
const TODO_URL = 'https://demo.playwright.dev/todomvc/';

const handlers = {
  async init() {
    if (!agent) {
      agent = new HyperAgent({ llm: { provider: 'openai', apiKey: KEY, model: MODEL, temperature: 0,
        baseURL: 'https://openrouter.ai/api/v1' }, debug: false, localConfig: { headless: true } });
    }
    return { ok: true };
  },
  async reset({ obs_js }) {
    // fresh page per rep (state hygiene), then clear persisted state and reload
    if (page) { try { await page.close(); } catch {} }
    page = await agent.newPage();
    await page.goto(TODO_URL, { waitUntil: 'domcontentloaded' });
    await page.evaluate("localStorage.removeItem('react-todos')");
    await page.goto(TODO_URL, { waitUntil: 'domcontentloaded' });
    return { ok: true, obs: await page.evaluate(obs_js) };
  },
  async act({ code, obs_js }) {
    let out = '';
    try { const r = await page.perform(code); out = typeof r === 'string' ? r : JSON.stringify(r); }
    catch (e) { out = 'perform error: ' + ((e && e.message) || String(e)); }
    return { ok: true, out, obs: await page.evaluate(obs_js) };
  },
  async ai({ code, obs_js }) {
    let out = '';
    try { const r = await page.ai(code); out = typeof r === 'string' ? r : JSON.stringify(r); }
    catch (e) { out = 'ai error: ' + ((e && e.message) || String(e)); }
    return { ok: true, out, obs: await page.evaluate(obs_js) };
  },
  async verify({ verify_js }) { return { ok: true, out: await page.evaluate(verify_js) }; },
  async screenshot({ path }) { await page.screenshot({ path, fullPage: true }); return { ok: true }; },
  async usage() { return { ok: true, usage }; },
  async usage_reset() { const u = JSON.parse(JSON.stringify(usage)); usage.inputTokens = 0; usage.outputTokens = 0; usage.calls = 0; usage.providers = {}; return { ok: true, usage: u }; },
  async quit() { try { await agent.closeAgent(); } catch {} return { ok: true, quit: true }; },
};

readline.createInterface({ input: process.stdin }).on('line', async (line) => {
  line = line.trim(); if (!line) return;
  let m; try { m = JSON.parse(line); } catch { send({ ok: false, error: 'bad json' }); return; }
  const h = handlers[m.cmd];
  if (!h) { send({ ok: false, error: 'unknown cmd ' + m.cmd }); return; }
  try { send(await h(m)); } catch (e) { send({ ok: false, error: (e && e.message) || String(e) }); }
});
