"""Prose claims of "the only harness to pass X" must be true in the scoreboard.

The 2026-09-13 round-7 report and README both stated that Browser Use Pi was "the only harness in
the set to pass `chanel-gb-pdp-tag-inspection`". It was not: browser-relay passed the same task 2/3.
That is a prose claim checked by nobody, drifting away from a table the repo already publishes.

This test derives the per-task passer set from the committed scoreboard and fails any "only harness
to pass `<task-id>`" claim in the README or the round reports that names a harness which is not the
sole passer. Hermetic: reads committed files only.
"""
import json
import pathlib
import re
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
SCOREBOARD = REPO / "bench-ext" / "artifacts" / "2026-09-12" / "corpus" / "capability-scoreboard.json"
PROSE = [REPO / "README.md"] + sorted((REPO / "bench-ext" / "artifacts").glob("*-round*/report.md"))

#: "the only harness ... to pass `task-id`" — the claim shape this test polices.
CLAIM = re.compile(r"only harness[^.]{0,80}?`([a-z0-9-]+)`", re.I)


def passers(agg, task):
    return sorted(h for h in agg["harnesses"]
                  if agg["table"][h].get(task) and agg["table"][h][task]["passes"] > 0)


class UniquenessClaims(unittest.TestCase):
    def setUp(self):
        self.agg = json.loads(SCOREBOARD.read_text())

    def test_the_matcher_catches_the_claim_it_was_written_for(self):
        """Guard the regex against a prose-shape change, not against an empty corpus.

        This is the exact sentence that shipped in round 7 and was wrong.
        """
        sentence = ("Headline: browser-use-pi is the only harness in the whole set to pass "
                    "`chanel-gb-pdp-tag-inspection`.")
        self.assertEqual(CLAIM.findall(sentence), ["chanel-gb-pdp-tag-inspection"])

    def test_only_harness_claims_name_a_sole_passer(self):
        problems = []
        for path in PROSE:
            if not path.is_file():
                continue
            text = path.read_text()
            for task in CLAIM.findall(text):
                if task not in self.agg["tasks"]:
                    problems.append(f"{path.name}: claims a task not in the scoreboard: {task}")
                    continue
                who = passers(self.agg, task)
                if len(who) != 1:
                    problems.append(
                        f"{path.name}: calls a harness 'the only harness' to pass {task}, "
                        f"but {len(who)} harnesses pass it ({', '.join(who)})")
        self.assertEqual(problems, [], "\n".join(problems))


if __name__ == "__main__":
    unittest.main()
