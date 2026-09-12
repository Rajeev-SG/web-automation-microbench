"""No synthetic task debris can re-enter the repo (issue #12 + #27).

The benchmark is a consumer of harvested real work: local invented pages, a
`file://` task URL or a hand-written task module are all rejected here, in code,
so the rule does not depend on a reviewer noticing. The legacy
`bench-ext/fixtures/spa-suite` exemption was removed with issue #27.
"""
import json
import pathlib
import unittest

BASE = pathlib.Path(__file__).resolve().parents[1]
REPO = BASE.parent

#: Directories that legitimately contain vendored third-party HTML (harness checkouts).
SKIP_DIRS = {"work", "node_modules", "artifacts", "__pycache__", ".git", ".playwright-cli"}


def _walk(root, suffixes):
    """Walk `root`, pruning SKIP_DIRS so a vendored harness checkout is never traversed."""
    import os
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            path = pathlib.Path(dirpath) / name
            if path.suffix in suffixes:
                yield path


class NoSyntheticFixtures(unittest.TestCase):
    def test_no_fixture_directories_hold_pages(self):
        offenders = []
        import os
        for dirpath, dirnames, _ in os.walk(BASE):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            if "fixtures" in dirnames:
                offenders.append(str((pathlib.Path(dirpath) / "fixtures").relative_to(REPO)))
        self.assertEqual(offenders, [], f"synthetic fixture directories reintroduced: {offenders}")

    def test_no_repo_local_file_urls_in_task_code(self):
        offenders = []
        for path in _walk(BASE, {".py"}):
            if path.name == pathlib.Path(__file__).name:
                continue  # this guard names the banned strings as data
            text = path.read_text(errors="ignore")
            if "file://" in text or "/fixtures/" in text:
                offenders.append(str(path.relative_to(REPO)))
        self.assertEqual(offenders, [], f"repo-local task URLs reintroduced: {offenders}")

    def test_no_repo_local_urls_in_task_specs(self):
        offenders = []
        for path in _walk(BASE, {".json"}):
            try:
                spec = json.loads(path.read_text())
            except Exception:
                continue
            url = spec.get("url") if isinstance(spec, dict) else None
            if isinstance(url, str) and (url.startswith("file://") or "/fixtures/" in url):
                offenders.append(str(path.relative_to(REPO)))
        self.assertEqual(offenders, [], f"task specs point at repo-local pages: {offenders}")

    def test_the_two_stale_synthetic_modules_are_gone(self):
        for gone in ("tasks_v1.py", "tasks_real.py", "docs/task-suite-v1.md"):
            self.assertFalse((BASE / gone).exists(), f"stale synthetic artifact {gone} is back")

    def test_ci_has_no_legacy_fixture_exemption(self):
        ci = (REPO / ".github" / "workflows" / "ci.yml").read_text()
        self.assertNotIn("Legacy bench-ext/fixtures/spa-suite removal", ci)
        self.assertNotIn("is expected to still exist", ci)
        self.assertIn("No synthetic task fixtures", ci)


if __name__ == "__main__":
    unittest.main()
