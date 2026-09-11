// Node benchmark runner: Stagehand v4 and Magnitude
// Same task and verification as the 2026-09-10 benchmark:
//   Add two todos (Email supplier, Review invoice), complete Email supplier,
//   click Active filter, verify only Review invoice remains with 1 item left.
import { writeFileSync } from 'fs';
import path from 'path';

const BASE = '/Users/rajeev/.codex/visualizations/2026/09/11/01a09153-79f1-7be2-bf68-f8d575dbcc84/extend-benchmark';
const URL_TASK = 'https://demo.playwright.dev/todomvc/';
const contender = process.argv[2]; // 'stagehand' | 'magnitude'
const rep = parseInt(process.argv[3] || '1', 10);
const rid = `${rep}-${contender}`;

const t0 = Date.now();
const result = { id: rid, contender, rep, events: [], errors: [] };

function log(ev) { result.events.push(ev); }

let passes = null;
let tokens = { input: 0, output: 0, reasoning: 0, cached: 0 };
let modelCalls = 0;
let totalCost = 0;

if (contender === 'stagehand') {
  const { Stagehand, localBrowser } = await import('./stagehand/node_modules/@browserbasehq/stagehand/dist/index.mjs');
  const { default: OpenAI } = await import("./stagehand/node_modules/openai/index.js");
  const openai = new OpenAI({
    apiKey: process.env.OPENROUTER_API_KEY,
    baseURL: 'https://openrouter.ai/api/v1',
    defaultHeaders: { 'HTTP-Referer': 'https://magnitude.run', 'X-Title': 'Magnitude' },
  });
  const llm = {
    generate: async (params) => {
      const structured = params.responseFormat?.type === 'json_schema';
      const toParts = (content) => {
        const blocks = Array.isArray(content) ? content : [content];
        return blocks.map((b) =>
          b.type === 'text' ? { type: 'text', text: b.text } :
          { type: 'image_url', image_url: { url: `data:${b.mimeType};base64,${b.data}` } }
        );
      };
      const messages = [
        ...(params.systemPrompt ? [{ role: 'system', content: params.systemPrompt }] : []),
        ...params.messages.map((m) => ({ role: m.role, content: toParts(m.content) })),
      ];
      const body = {
        model: 'z-ai/glm-5.3-flash',
        messages,
        max_tokens: 3000,
        temperature: params.temperature ?? 0,
        reasoning: { effort: 'low', exclude: true },
        provider: { sort: 'latency' },
      };
      if (params.responseFormat?.type === 'json_schema') {
        body.response_format = { type: 'json_schema', json_schema: { name: params.responseFormat.name, strict: false, schema: params.responseFormat.schema } };
      }
      modelCalls++;
      const r = await openai.chat.completions.create(body);
      const text = r.choices[0].message?.content ?? '';
      const usage = r.usage ?? {};
      tokens.input += usage.prompt_tokens ?? 0;
      tokens.output += usage.completion_tokens ?? 0;
      tokens.reasoning += usage.completion_tokens_details?.reasoning_tokens ?? 0;
      tokens.cached += usage.prompt_tokens_details?.cached_tokens ?? 0;
      const ev = { model: 'z-ai/glm-5.3-flash', provider: r.provider, request_id: r.id, usage: usage, structured, text: text.slice(0, 400) };
      log(ev);
      if (params.responseFormat?.type === 'json_schema') {
        let parsed = {};
        try { parsed = JSON.parse(text); } catch {}
        return {
          role: 'assistant', content: { type: 'text', text },
          outputFormat: 'json_schema', structuredContent: parsed,
          usage: { inputTokens: usage.prompt_tokens ?? 0, outputTokens: usage.completion_tokens ?? 0, totalTokens: usage.total_tokens ?? 0, reasoningTokens: usage.completion_tokens_details?.reasoning_tokens ?? 0, cachedInputTokens: usage.prompt_tokens_details?.cached_tokens ?? 0 },
        };
      }
      return {
        role: 'assistant', content: { type: 'text', text }, outputFormat: 'text',
        usage: { inputTokens: usage.prompt_tokens ?? 0, outputTokens: usage.completion_tokens ?? 0, totalTokens: usage.total_tokens ?? 0 },
      };
    },
  };
  const browser = await localBrowser.launch({ headless: true });
  const stagehand = await Stagehand.create({ browser, model: llm });
  const page = await browser.context.activePage();
  const setup0 = Date.now();
  await page.goto(URL_TASK, { waitUntil: 'domcontentloaded' });
  await page.evaluate(() => localStorage.removeItem('react-todos'));
  await page.reload({ waitUntil: 'domcontentloaded' });
  const setup = (Date.now() - setup0) / 1000;
  result.setup_s = setup;
  const t1 = Date.now();
  try {
    // Deterministic primitives: observe to get the input selector, then fill + Enter
    const inp = await stagehand.observe('find the new todo input field');
    const inpSel = inp.data[0].selector;
    async function ensureTodo(text) {
      const before = await page.locator('.todo-list li').count();
      await stagehand.act('Add a todo item: fill the "What needs to be done?" input with "' + text + '" then press Enter in it');
      let after = await page.locator('.todo-list li').count();
      if (after <= before) {
        await stagehand.act('Press the Enter key in the new todo input field');
        after = await page.locator('.todo-list li').count();
      }
      log({ phase: 'act', action: 'add:' + text, before, after });
    }
    await ensureTodo('Email supplier');
    await ensureTodo('Review invoice');
    const chk = await stagehand.observe('find the checkbox toggle for the todo item Email supplier');
    if (chk.data && chk.data.length > 0) {
      const sel = chk.data[0].selector;
      await page.locator(sel).first().click();
    } else {
      await stagehand.act('Click the checkbox for the Email supplier todo item');
    }
    log({ phase: 'act', action: 'complete' });
    await stagehand.act('Click the Active filter link at the bottom of the page');
    log({ phase: 'act', action: 'filter' });
  } catch (e) { result.errors.push(String(e).slice(0, 300)); }
  const total = (Date.now() - t1) / 1000;
  result.total_s = total;
  // independent verification
  const verify = await page.evaluate(() => JSON.stringify({
    url: location.href,
    items: Array.from(document.querySelectorAll('.todo-list li')).map(e => ({ text: e.innerText.trim(), completed: e.classList.contains('completed') })),
    saved: JSON.parse(localStorage.getItem('react-todos') || '[]').map(x => ({ title: x.title, completed: x.completed })),
  }));
  result.verification = verify;
  try {
    const v = JSON.parse(verify);
    passes = v.url.includes('#/active') && Array.isArray(v.items) && v.items.length === 1
      && v.items[0].text.includes('Review invoice') && !v.items[0].completed
      && JSON.stringify(v.saved.sort((a,b)=>a.title.localeCompare(b.title))) === JSON.stringify([{ title: 'Email supplier', completed: true }, { title: 'Review invoice', completed: false }]);
  } catch { passes = false; }
  await page.screenshot({ path: path.join(BASE, 'results', `${rid}.png`) });
  await stagehand.close();
}

if (contender === 'magnitude') {
  const { startBrowserAgent } = await import('./magnitude/node_modules/magnitude-core/dist/index.cjs');
  const agent = await startBrowserAgent({
    llm: {
      provider: 'openai-generic',
      options: {
        baseUrl: 'https://openrouter.ai/api/v1',
        model: 'z-ai/glm-5.3-flash',
        apiKey: process.env.OPENROUTER_API_KEY,
        temperature: 0,
        headers: { 'HTTP-Referer': 'https://magnitude.run', 'X-Title': 'Magnitude' },
      },
    },
    browserOptions: { launchOptions: { headless: true } },
  });
  agent.events.on('tokensUsed', (u) => {
    tokens.input += u.inputTokens || 0;
    tokens.output += u.outputTokens || 0;
    tokens.cached += u.cacheReadInputTokens || 0;
    log({ phase: 'tokens', ...u });
  });
  const setup0 = Date.now();
  await agent.nav(URL_TASK);
  await agent.page.evaluate(() => localStorage.removeItem('react-todos'));
  await agent.page.goto(URL_TASK, { waitUntil: 'domcontentloaded' });
  const setup = (Date.now() - setup0) / 1000;
  result.setup_s = setup;
  const t1 = Date.now();
  try {
    await agent.act('Add a todo item with the text "Email supplier"');
    log({ phase: 'act', action: 'add1' });
    await agent.act('Add a todo item with the text "Review invoice"');
    log({ phase: 'act', action: 'add2' });
    await agent.act('Mark the todo item "Email supplier" as complete by clicking its checkbox');
    log({ phase: 'act', action: 'complete' });
    await agent.act('Click the "Active" filter link to show only incomplete items');
    log({ phase: 'act', action: 'filter' });
  } catch (e) { result.errors.push(String(e).slice(0, 300)); }
  const total = (Date.now() - t1) / 1000;
  result.total_s = total;
  const verify = await agent.page.evaluate(() => JSON.stringify({
    url: location.href,
    items: Array.from(document.querySelectorAll('.todo-list li')).map(e => ({ text: e.innerText.trim(), completed: e.classList.contains('completed') })),
    saved: JSON.parse(localStorage.getItem('react-todos') || '[]').map(x => ({ title: x.title, completed: x.completed })),
  }));
  result.verification = verify;
  try {
    const v = JSON.parse(verify);
    passes = v.url.includes('#/active') && Array.isArray(v.items) && v.items.length === 1
      && v.items[0].text.includes('Review invoice') && !v.items[0].completed
      && JSON.stringify(v.saved.sort((a, b) => a.title.localeCompare(b.title))) === JSON.stringify([{ title: 'Email supplier', completed: true }, { title: 'Review invoice', completed: false }]);
  } catch { passes = false; }
  await agent.page.screenshot({ path: path.join(BASE, 'results', `${rid}.png`) });
  await agent.stop();
}

result.tokens = tokens;
result.model_calls = modelCalls;
result.cost = totalCost;
result.pass = passes;
result.wall_s = (Date.now() - t0) / 1000;
writeFileSync(path.join(BASE, 'results', `${rid}.json`), JSON.stringify(result, null, 2));
console.log(JSON.stringify({ id: rid, pass: passes, total_s: result.total_s, model_calls: modelCalls, tokens }));
process.exit(0);
