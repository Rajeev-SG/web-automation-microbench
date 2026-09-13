// Browser Use Pi native driver (issue #34). Keeps the tool's real architecture:
// Pi Mono agent loop -> persistent V8 REPL -> raw CDP -> Chrome. One agent.run() per rep,
// never one primitive action per model call.
// Config via env (set by browser-use-pi.py): BUPI_* variables.
import { spawn } from 'node:child_process';
import { readFile, writeFile, mkdir, rm } from 'node:fs/promises';
import { join } from 'node:path';

const ROOT = process.env.BUPI_ROOT;
const env = process.env;
const cfg = {
  model: env.BUPI_MODEL || 'openrouter/z-ai/glm-5.3-flash',
  instruction: env.BUPI_INSTRUCTION || '',
  url: env.BUPI_URL || '',
  verifyJs: env.BUPI_VERIFY_JS || 'JSON.stringify({url:location.href})',
  out: env.BUPI_OUT,
  workspace: env.BUPI_WORKSPACE,
  profile: env.BUPI_PROFILE,
  mode: env.BUPI_MODE || 'chromium',       // 'chromium' (local, isolated) | 'chrome' (attach)
  cdpUrl: env.BUPI_CDP_URL || '',
  maxSteps: parseInt(env.BUPI_MAX_STEPS || '14', 10),
  timeoutMs: parseInt(env.BUPI_TIMEOUT_MS || '300000', 10),
  maxCostUsd: env.BUPI_MAX_COST_USD ? parseFloat(env.BUPI_MAX_COST_USD) : undefined,
  screenshot: env.BUPI_SCREENSHOT || '',
  reasoning: env.BUPI_REASONING || 'low',
  costIn: parseFloat(env.BUPI_COST_IN || '0.075'),
  costOut: parseFloat(env.BUPI_COST_OUT || '0.25'),
  costCache: parseFloat(env.BUPI_COST_CACHE || '0.0375'),
};

const pi = await import(`${ROOT}/dist/index.js`);
const { createModels, createProvider, openrouterProvider } = {
  ...(await import(`${ROOT}/node_modules/@earendil-works/pi-ai/dist/index.js`)),
  openrouterProvider: (await import(`${ROOT}/node_modules/@earendil-works/pi-ai/dist/providers/openrouter.js`)).openrouterProvider,
};

// GLM 5.3 Flash is not in Pi's pinned OpenRouter catalog; register it explicitly with the
// benchmark's latency-sorted provider routing (compat.openRouterRouting -> body.provider).
const [providerId, ...rest] = cfg.model.split('/');
const modelId = rest.join('/');
const GLM = {
  id: modelId,
  name: 'GLM-5.3-Flash (OpenRouter, latency-sorted)',
  api: 'openai-completions',
  provider: providerId,
  baseUrl: 'https://openrouter.ai/api/v1',
  reasoning: true,
  thinkingLevelMap: { off: null, minimal: null, low: 'low', medium: null, high: 'high', xhigh: null, max: null },
  input: ['text', 'image'],
  cost: { input: cfg.costIn, output: cfg.costOut, cacheRead: cfg.costCache, cacheWrite: 0 },
  contextWindow: 1000000,
  maxTokens: 131072,
  compat: { openRouterRouting: { sort: 'latency' } },
};
let models;
if (providerId === 'openrouter') {
  const base = openrouterProvider();
  const wrapped = { ...base, getModels: () => [...base.getModels(), GLM] };
  models = createModels();
  models.setProvider(wrapped);
}

const browser = cfg.mode === 'chrome'
  ? pi.Browser.chrome(cfg.cdpUrl ? { cdpUrl: cfg.cdpUrl } : {})
  : pi.Browser.chromium({ headless: true, profileDir: cfg.profile });

await mkdir(cfg.workspace, { recursive: true });
await mkdir(cfg.profile, { recursive: true });

const out = { ok: false };
let agent;
try {
  agent = await pi.BrowserUse.create({
    model: cfg.model,
    models,
    reasoning: cfg.reasoning,
    browser,
    workspace: cfg.workspace,
    telemetry: false,
    log: 'json',
  });
  const instruction = cfg.url ? `Open ${cfg.url} and complete this task. ${cfg.instruction}` : cfg.instruction;
  const t0 = Date.now();
  const result = await agent.run(instruction, {
    maxSteps: cfg.maxSteps,
    timeoutMs: cfg.timeoutMs,
    ...(cfg.maxCostUsd ? { maxCostUsd: cfg.maxCostUsd } : {}),
  });
  const wallMs = Date.now() - t0;
  out.ok = true;
  out.status = result.status;
  out.done = result.status === 'completed';
  out.output = result.status === 'completed' ? result.output : (result.partial?.value ?? result.text);
  out.text = (result.text || '').slice(0, 4000);
  out.steps = result.steps;
  out.durationMs = result.durationMs;
  out.wallMs = wallMs;
  out.checkpointPath = result.partial?.path;
  out.usage = result.usage || null;
  out.model = result.model;
  out.providerRetries = result.providerRetries ?? 0;
  out.runId = result.runId;
} catch (e) {
  out.error = `${e?.name || 'Error'}: ${e?.message || String(e)}`;
  out.trace = (e?.stack || '').slice(-2000);
}

// --- independent verification on the SAME live browser, before close -------------------------
const cdpPort = async () => {
  if (cfg.mode === 'chrome' && cfg.cdpUrl) {
    const m = cfg.cdpUrl.match(/127\.0\.0\.1:(\d+)/);
    return m ? parseInt(m[1], 10) : null;
  }
  try {
    const txt = await readFile(join(cfg.profile, 'DevToolsActivePort'), 'utf8');
    return parseInt(txt.trim().split('\n')[0], 10) || null;
  } catch { return null; }
};

async function withTarget(fn) {
  const port = await cdpPort();
  if (!port) throw new Error('no DevToolsActivePort for verification');
  const list = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  const host = (cfg.url || '').split('/')[2] || '';
  const pages = list.filter((t) => t.webSocketDebuggerUrl && (t.type === 'page' || t.type === 'tab'));
  const t = pages.find((x) => host && (x.url || '').includes(host)) || pages.find((x) => (x.url || '').startsWith('http'));
  if (!t) throw new Error('no page target: ' + list.map((x) => x.url).join(' , '));
  const ws = new WebSocket(t.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
  let id = 0;
  const call = (method, params) => new Promise((res) => {
    const mid = ++id;
    const h = (ev) => {
      let m; try { m = JSON.parse(typeof ev === 'string' ? ev : ev.data); } catch { return; }
      if (m && m.id === mid) { ws.removeEventListener('message', h); res(m); }
    };
    ws.addEventListener('message', h);
    ws.send(JSON.stringify({ id: mid, method, params }));
  });
  try { return await fn(call, t); } finally { ws.close(); }
}

try {
  out.verification = await withTarget(async (call) => {
    const r = await call('Runtime.evaluate', { expression: cfg.verifyJs, awaitPromise: true, returnByValue: true });
    return r.result?.result?.value ?? JSON.stringify(r.result);
  });
} catch (e) { out.verification = `verify error: ${e.message}`; }

try {
  if (cfg.screenshot) {
    const b64 = await withTarget(async (call) => {
      const r = await call('Page.captureScreenshot', { format: 'png' });
      return r.result?.data;
    });
    if (b64) await writeFile(cfg.screenshot, Buffer.from(b64, 'base64'));
  }
} catch (e) { out.screenshotError = e.message; }

if (agent) { try { await agent.close(); } catch {} }
out.url_final = cfg.url;
await writeFile(cfg.out, JSON.stringify(out, null, 2));
console.log(JSON.stringify({ ok: out.ok, status: out.status, steps: out.steps, wallMs: out.wallMs, error: out.error, verification: (out.verification || '').slice(0, 200) }));
process.exit(0);
