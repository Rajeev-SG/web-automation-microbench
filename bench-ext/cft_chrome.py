#!/usr/bin/env python3
"""Reusable Chrome for Testing launcher for bench-ext.

The Round 3 blocker for extension-based contenders (browser-cli, BrowserSkill,
browser-relay, page-agent, sitegeist) was "extension install not automatable
headlessly". Branded Google Chrome silently ignores --load-extension
("--load-extension is not allowed in Google Chrome, ignoring"); Chrome for
Testing honours it. This module launches CFT with one or more unpacked
extensions and exposes the CDP HTTP endpoint.

Proven 2026-09-12: an unpacked MV3 extension's service_worker target appears in
GET /json/list within ~3s of launch.
"""
import json, os, pathlib, subprocess, tempfile, time, urllib.request

CFT = ("/Users/rajeev/Library/Caches/ms-playwright/chromium-1243/"
       "chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing")


class Chrome:
    def __init__(self, port, extensions=(), start_url="about:blank", profile=None,
                 extra=(), log=None):
        self.port = int(port)
        self.extensions = [str(pathlib.Path(e).resolve()) for e in extensions]
        self.start_url = start_url
        self.profile = profile or tempfile.mkdtemp(prefix=f"bench-cft-{port}-")
        self.extra = list(extra)
        self.log_path = log or f"/tmp/bench-cft-{self.port}.log"
        self.proc = None

    @property
    def cdp(self):
        return f"http://127.0.0.1:{self.port}"

    def launch(self, wait=True, timeout=25):
        args = [CFT, f"--remote-debugging-port={self.port}", f"--user-data-dir={self.profile}",
                "--no-first-run", "--no-default-browser-check", "--no-default-app-window",
                "--disable-features=DialMediaRouteProvider"]
        for e in self.extensions:
            args.append(f"--load-extension={e}")
        args += self.extra + [self.start_url]
        self._log = open(self.log_path, "w")
        self.proc = subprocess.Popen(args, stdout=self._log, stderr=self._log)
        if wait:
            self.wait_cdp(timeout)
        return self

    def wait_cdp(self, timeout=25):
        end = time.time() + timeout
        while time.time() < end:
            try:
                json.load(urllib.request.urlopen(self.cdp + "/json/version", timeout=2))
                return True
            except Exception:
                time.sleep(0.4)
        raise TimeoutError(f"CDP not up on {self.cdp}; see {self.log_path}")

    def targets(self):
        return json.load(urllib.request.urlopen(self.cdp + "/json/list", timeout=5))

    def extension_workers(self):
        out = []
        for t in self.targets():
            if t.get("type") == "service_worker" and t.get("url", "").startswith("chrome-extension://"):
                out.append(t)
        return out

    def kill(self):
        if self.proc:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=10)
            except Exception:
                self.proc.kill()
        try:
            self._log.close()
        except Exception:
            pass

    def __enter__(self):
        return self.launch()

    def __exit__(self, *a):
        self.kill()


if __name__ == "__main__":
    import sys
    ext = sys.argv[1] if len(sys.argv) > 1 else None
    c = Chrome(9261, extensions=[ext] if ext else [], start_url="https://demo.playwright.dev/todomvc/")
    c.launch()
    for t in c.targets():
        print(t["type"], "|", t.get("url", "")[:90])
    c.kill()
