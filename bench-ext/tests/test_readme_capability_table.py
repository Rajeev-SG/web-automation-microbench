"""The README's capability numbers must equal the scoreboard (issue #30).

The README quotes screening results, and a hand-copied number goes stale the moment the
evidence is rescored — that happened once already (chanel-gb-pdp-tag-inspection was quoted
at its pre-fix 5/9 after the fail-closed rule dropped it to 2/9). This test makes the
README's tables derived data: edit one without the other and CI fails.

Hermetic: it reads two committed files (README.md and the scoreboard JSON). No network.
"""
import json
import pathlib
import re
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
README = REPO / "README.md"
SCOREBOARD = REPO / "bench-ext" / "artifacts" / "2026-09-12" / "corpus" / "capability-scoreboard.json"

#: README display name -> scoreboard harness id (the README labels two rows for readers).
#: README citations that resolve in the producer repo, not this one.
PRODUCER_CITED = {"docs/implementation/task-harvesting-v1.md"}

HARNESS_ALIASES = {
    "browser-relay": "browser-relay",
    "raw-playwright baseline": "raw-playwright",
    "agent-browser": "agent-browser",
    "cdp-browser": "cdp-browser",
    "BrowserSkill": "BrowserSkill",
    "browser-use-pi": "browser-use-pi",
}


def _load():
    return json.loads(SCOREBOARD.read_text()), README.read_text()


def _totals(agg, harness):
    cells = [c for c in agg["table"][harness].values() if c]
    return sum(c["passes"] for c in cells), sum(c["reps"] for c in cells)


def _task_totals(agg, task):
    cells = [agg["table"][h][task] for h in agg["harnesses"] if agg["table"][h].get(task)]
    return sum(c["passes"] for c in cells), sum(c["reps"] for c in cells)


class ReadmeMatchesScoreboard(unittest.TestCase):
    #: the capability table's header, used to scope the parse (several README tables
    #: start their rows with a bold harness name, so a bare "| **" match is not enough)
    HEADER = ["Harness", "Repo", "Fast-path (TodoMVC)", "Real-work capability",
              "Capability reps", "Note"]
    #: column index (0-based, after splitting on "|") of the capability cell
    CAPABILITY_COL = 3

    def _harness_rows(self, readme):
        """{display name: capability cell} from the README capability table only."""
        lines = readme.splitlines()
        start = next((i for i, l in enumerate(lines)
                      if self._cells(l) == self.HEADER), None)
        self.assertIsNotNone(start, "README capability table header not found")
        rows = {}
        for line in lines[start + 2:]:          # skip the header and the |---| separator
            cells = self._cells(line)
            if not cells:
                break
            rows[cells[0]] = cells[self.CAPABILITY_COL]
        return rows

    @staticmethod
    def _cells(line):
        if not line.strip().startswith("|"):
            return []
        return [c.strip().strip("*") for c in line.strip().strip("|").split("|")]

    def test_every_screened_harness_row_matches(self):
        agg, readme = _load()
        rows = self._harness_rows(readme)
        for name, hid in HARNESS_ALIASES.items():
            self.assertIn(name, rows, f"no README capability row for {name}")
            passes, reps = _totals(agg, hid)
            self.assertEqual(rows[name], f"{passes}/{reps}",
                             f"{name}: README says {rows[name]}, scoreboard says {passes}/{reps}")
        self.assertEqual(set(rows), set(HARNESS_ALIASES), "README capability rows drifted")

    def test_every_task_row_matches(self):
        agg, readme = _load()
        for task in agg["tasks"]:
            m = re.search(r"\|\s*`" + re.escape(task) + r"`[^|]*\|[^|]*\|\s*(\d+/\d+)\s*\|", readme)
            self.assertIsNotNone(m, f"no README per-task row for {task}")
            passes, reps = _task_totals(agg, task)
            self.assertEqual(m.group(1), f"{passes}/{reps}",
                             f"{task}: README says {m.group(1)}, scoreboard says {passes}/{reps}")

    def test_the_task_list_is_complete(self):
        agg, readme = _load()
        for task in agg["tasks"]:
            self.assertIn(f"`{task}`", readme, f"{task} missing from the README")
        listed = set(re.findall(r"^\|\s*`([a-z0-9-]+)`\s*\|", readme, re.M))
        self.assertEqual(listed, set(agg["tasks"]))

    def test_every_path_the_readme_cites_exists(self):
        """A docs path that no longer resolves is how the layout section rotted.

        Scans inline-code spans (the way the README cites paths anywhere in the file) and
        requires each repo-relative path to exist. Patterns (`<tool>`, `*`) are skipped.
        """
        _, readme = _load()
        cited = set()
        for span in re.findall(r"`([^`\n]+)`", readme):
            span = span.strip()
            if any(ch in span for ch in "<>*|") or not span.startswith(
                    ("bench-ext/", "artifacts/", "docs/", ".github/")):
                continue
            if span in PRODUCER_CITED:
                continue
            cited.add(span)
        self.assertTrue(cited, "no repo paths cited in the README — did the format change?")
        missing = sorted(p for p in cited if not (REPO / p).exists())
        self.assertEqual(missing, [], f"README cites paths that do not exist: {missing}")

    def test_repo_layout_lists_bench_ext_and_the_corpus(self):
        _, readme = _load()
        rest = readme[readme.index("## Repo layout"):]
        block = rest[:rest.index("\n## ")]
        for needed in ("bench-ext/", "benchlib.py", "runners/", "corpus/", "artifacts/", "docs/"):
            self.assertIn(needed, block, f"Repo layout omits {needed}")

    def test_no_future_dated_headings(self):
        """The rig's clock is the only source of a run date (issue #27/#30)."""
        import datetime
        _, readme = _load()
        today = datetime.date.today()
        for m in re.finditer(r"^#{2,3}\s+.*?(\d{1,2}) (Sep|Oct|Nov|Dec) (\d{4})", readme, re.M):
            day, month, year = int(m.group(1)), m.group(2), int(m.group(3))
            month_n = {"Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}[month]
            self.assertLessEqual(datetime.date(year, month_n, day), today,
                                 f"future-dated heading: {m.group(0).strip()}")


if __name__ == "__main__":
    unittest.main()
