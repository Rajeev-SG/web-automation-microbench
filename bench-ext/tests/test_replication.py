"""Rep counts are centralized (issue #20 step 2) and follow the issue #1 topology."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import benchlib  # noqa: E402


class Replication(unittest.TestCase):
    def test_topology_matches_issue_1(self):
        self.assertEqual(benchlib.REP_TOPOLOGY['screen'], 2)
        self.assertEqual(benchlib.REP_TOPOLOGY['promote'], 5)
        self.assertGreaterEqual(benchlib.REP_TOPOLOGY['tiebreak'], 10)

    def test_default_reps_are_the_screening_plan(self):
        self.assertEqual(benchlib.DEFAULT_REPS, ['1', '2'])
        self.assertEqual(benchlib.reps_from_argv([]), ['1', '2'])
        self.assertEqual(benchlib.reps_from_argv(['1', '2', '3', '4', '5']), ['1', '2', '3', '4', '5'])

    def test_repeated_failure_stops(self):
        verdict = benchlib.promotion_verdict([{'pass': False}, {'pass': False}])
        self.assertEqual(verdict['stage'], 'stop')

    def test_plausible_candidate_promotes_to_five(self):
        verdict = benchlib.promotion_verdict([{'pass': True}, {'pass': False}])
        self.assertEqual(verdict['stage'], 'promote')
        self.assertEqual(verdict['reps'], benchlib.REP_TOPOLOGY['promote'])

    def test_no_runner_hardcodes_two_reps(self):
        runners = pathlib.Path(__file__).resolve().parents[1] / 'runners'
        offenders = [p.name for p in runners.glob('*.py')
                     if "['1', '2']" in p.read_text() or "['1','2']" in p.read_text()]
        self.assertEqual(offenders, [], f"runners still hardcoding reps: {offenders}")


if __name__ == "__main__":
    unittest.main()
