// Node preload shim for the cdp-browser contender.
//
// cdp-browser hardcodes http://localhost:9222 and ws://localhost:9222, while the benchmark
// launches its own Chrome on a private debug port. This shim rewrites only those CDP URLs to
// the bench port (default 127.0.0.1:9243); no cdp-browser source file is modified.
//
// Previously this file lived only in /tmp (which macOS clears), so the contender silently
// became unrunnable. It is versioned in-repo from issue #27 onward.
const TARGET_HOST = '127.0.0.1';
const TARGET_PORT = Number(process.env.CDP_FWD_PORT || 9243);

const rewrite = (u) => {
  if (typeof u !== 'string') return u;
  return u.replace(/\/\/(localhost|127\.0\.0\.1):9222\b/g, `//${TARGET_HOST}:${TARGET_PORT}`);
};

const retarget = (opts) => {
  if (opts && typeof opts === 'object' && (opts.hostname === 'localhost' || opts.hostname === '127.0.0.1')
      && String(opts.port) === '9222') {
    opts.hostname = TARGET_HOST;
    opts.port = TARGET_PORT;
  }
  return opts;
};

try {
  const http = require('http');
  for (const name of ['request', 'get']) {
    const orig = http[name].bind(http);
    http[name] = (a, b, c) => {
      if (typeof a === 'string') return orig(rewrite(a), b, c);
      return orig(retarget(a), b, c);
    };
  }
} catch (e) { /* http unavailable — leave it alone */ }

if (typeof globalThis.fetch === 'function') {
  const origFetch = globalThis.fetch;
  globalThis.fetch = (input, init) => origFetch(typeof input === 'string' ? rewrite(input) : input, init);
}

if (typeof globalThis.WebSocket === 'function') {
  const OrigWS = globalThis.WebSocket;
  globalThis.WebSocket = class extends OrigWS {
    constructor(url, protocols) { super(rewrite(url), protocols); }
  };
}
