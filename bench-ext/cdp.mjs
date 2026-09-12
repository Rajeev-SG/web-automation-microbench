// Minimal CDP helper: eval JS in, or screenshot, a target matched by URL substring.
// usage: node cdp.mjs <port> <mode:eval|shot> <urlSub> <arg>
const WS = '/Users/rajeev/Code/web-automation-microbench/bench-ext/work/browser-relay/node_modules/ws/index.js';
const { default: WebSocket } = await import(WS);
const [port, mode, urlSub, arg] = process.argv.slice(2);
const list = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
// urlSub '*' = first page target of any URL (fresh Chrome opens chrome://newtab/, not about:blank)
const cands = list.filter(t => t.webSocketDebuggerUrl);
const t = urlSub === '*'
  ? (cands.find(x => x.type === 'page') || cands.find(x => (x.url || '').startsWith('http')))
  : cands.find(x => (x.url || '').includes(urlSub));
if (!t) { console.error('no target matching ' + urlSub + ' :: ' + list.map(x=>x.url).join(' , ')); process.exit(2); }
const ws = new WebSocket(t.webSocketDebuggerUrl);
await new Promise((res, rej) => { ws.on('open', res); ws.on('error', rej); });
let id = 0;
const call = (method, params) => new Promise((res) => {
  const mid = ++id;
  const h = (d) => { const m = JSON.parse(d); if (m.id === mid) { ws.off('message', h); res(m); } };
  ws.on('message', h);
  ws.send(JSON.stringify({ id: mid, method, params }));
});
let out;
if (mode === 'eval') {
  const r = await call('Runtime.evaluate', { expression: arg, awaitPromise: true, returnByValue: true });
  out = r.result?.result?.value ?? r.result ?? r;
  console.log(typeof out === 'string' ? out : JSON.stringify(out));
} else if (mode === 'shot') {
  const r = await call('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true });
  const { writeFileSync } = await import('node:fs');
  writeFileSync(arg, Buffer.from(r.result.data, 'base64'));
  console.log('saved ' + arg);
}
ws.close();
