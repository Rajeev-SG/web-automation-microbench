"""The declarative pass rule is the consumer's only pass/fail authority (issue #27).

Ported semantics from codex-session-orchestration-analysis tools/task_pass_rule.py:
a consumer needs no per-task code, and every rule fails *closed* — an unparseable
finding, a missing measurement or a degenerate page all count as failure.
"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import pass_rule  # noqa: E402


class FindingMatchesTruth(unittest.TestCase):
    RULE = {"kind": "finding_matches_truth", "fields": ["gtm", "aw"],
            "finding_fields": {"aw": "googleAds"}, "presence_fields": ["pinterest"]}

    def test_exact_match_passes(self):
        truth = {"gtm": ["GTM-A", "GTM-B"], "aw": [], "pinterest": False}
        finding = {"gtm": ["GTM-B", "GTM-A"], "googleAds": [], "pinterest": False}
        self.assertTrue(pass_rule.evaluate(self.RULE, truth, finding))

    def test_set_compare_is_order_insensitive(self):
        truth = {"hosts": ["a.com", "b.com"]}
        self.assertTrue(pass_rule.evaluate({"kind": "finding_matches_truth", "fields": ["hosts"]},
                                           truth, {"hosts": ["b.com", "a.com"]}))

    def test_extra_or_missing_member_fails(self):
        truth = {"gtm": ["GTM-A"]}
        self.assertFalse(pass_rule.evaluate({"kind": "finding_matches_truth", "fields": ["gtm"]},
                                            truth, {"gtm": ["GTM-A", "GTM-B"]}))
        self.assertFalse(pass_rule.evaluate({"kind": "finding_matches_truth", "fields": ["gtm"]},
                                            truth, {"gtm": []}))

    def test_finding_field_alias(self):
        truth = {"aw": ["AW-123456"]}
        finding = {"googleAds": ["AW-123456"]}
        rule = {"kind": "finding_matches_truth", "fields": ["aw"], "finding_fields": {"aw": "googleAds"}}
        self.assertTrue(pass_rule.evaluate(rule, truth, finding))

    def test_presence_compared_as_boolean(self):
        truth = {"pinterest": True}
        rule = {"kind": "finding_matches_truth", "presence_fields": ["pinterest"]}
        self.assertTrue(pass_rule.evaluate(rule, truth, {"pinterest": "yes"}))
        self.assertFalse(pass_rule.evaluate(rule, truth, {"pinterest": False}))

    def test_url_field_normalises_a_bare_host_trailing_slash_only(self):
        rule = {"kind": "finding_matches_truth", "exact_fields": ["canonical"], "url_fields": ["canonical"]}
        self.assertTrue(pass_rule.evaluate(rule, {"canonical": "https://rajeevg.com"},
                                           {"canonical": "https://rajeevg.com/"}))
        # a different path or host is still a different page
        self.assertFalse(pass_rule.evaluate(rule, {"canonical": "https://rajeevg.com/a"},
                                            {"canonical": "https://rajeevg.com/b"}))
        self.assertFalse(pass_rule.evaluate(rule, {"canonical": "https://rajeevg.com"},
                                            {"canonical": "https://other.com"}))

    def test_a_rule_without_require_any_of_still_fails_closed_on_an_empty_measurement(self):
        """The seed task's rule declares no `require_any_of`; a bot-walled page that serves
        no tag must not score a pass just because the agent reported nothing too
        (issue #27 false-pass found on chanel-gb-pdp-tag-inspection)."""
        rule = {"kind": "finding_matches_truth", "fields": ["gtm", "aw"],
                "finding_fields": {"aw": "googleAds"}, "presence_fields": ["pinterest"]}
        empty = {"gtm": [], "aw": [], "pinterest": False}
        self.assertFalse(pass_rule.evaluate(rule, empty, {"gtm": [], "googleAds": [], "pinterest": False}))
        # a page that really carries something still compares normally
        truth = {"gtm": ["GTM-A"], "aw": [], "pinterest": False}
        self.assertTrue(pass_rule.evaluate(rule, truth, {"gtm": ["GTM-A"], "googleAds": [], "pinterest": False}))

    def test_allow_empty_truth_is_the_documented_escape_hatch(self):
        rule = {"kind": "finding_matches_truth", "fields": ["gtm"]}
        empty, finding = {"gtm": []}, {"gtm": []}
        self.assertFalse(pass_rule.evaluate(rule, empty, finding))
        pass_rule.ALLOW_EMPTY_TRUTH = True
        try:
            self.assertTrue(pass_rule.evaluate(rule, empty, finding))
        finally:
            pass_rule.ALLOW_EMPTY_TRUTH = False

    def test_require_any_of_fails_closed_on_an_empty_measurement(self):
        rule = {"kind": "finding_matches_truth", "fields": ["gtm"], "require_any_of": ["gtm"]}
        # agent reports nothing, page carries nothing: an invalid measurement, not a pass
        self.assertFalse(pass_rule.evaluate(rule, {"gtm": []}, {"gtm": []}))
        self.assertTrue(pass_rule.evaluate(rule, {"gtm": ["GTM-A"]}, {"gtm": ["GTM-A"]}))

    def test_missing_finding_is_a_failure(self):
        rule = {"kind": "finding_matches_truth", "fields": ["gtm"]}
        self.assertFalse(pass_rule.evaluate(rule, {"gtm": ["GTM-A"]}, None))
        self.assertFalse(pass_rule.check_from_rule(rule)(None))
        self.assertFalse(pass_rule.check_from_rule(rule)({"truth": {"gtm": ["GTM-A"]}, "finding": None}))


class Structural(unittest.TestCase):
    RULE = {"kind": "structural", "expected_labels": ["Runner", "Browser", "Verifier"],
            "expected_arrows": 2, "require_no_overlap": True}

    def finding(self, **o):
        base = {"labels": ["Runner", "Browser", "Verifier"],
                "nodes": [{"label": "Runner"}, {"label": "Browser"}, {"label": "Verifier"}],
                "arrows": 2, "overlap": False}
        base.update(o)
        return base

    def test_matching_structure_passes(self):
        self.assertTrue(pass_rule.evaluate(self.RULE, {}, self.finding()))

    def test_wrong_labels_arrows_or_overlap_fail(self):
        self.assertFalse(pass_rule.evaluate(self.RULE, {}, self.finding(labels=["Runner", "Browser"])))
        self.assertFalse(pass_rule.evaluate(self.RULE, {}, self.finding(arrows=0)))
        self.assertFalse(pass_rule.evaluate(self.RULE, {}, self.finding(overlap=True)))


class RuleKinds(unittest.TestCase):
    def test_test_runner_rules_are_left_to_the_runner(self):
        self.assertIsNone(pass_rule.evaluate({"kind": "test-runner"}, {}, {}))

    def test_unknown_rule_returns_none(self):
        self.assertIsNone(pass_rule.evaluate({"kind": "nonsense"}, {}, {}))

    def test_check_from_rule_only_true_passes(self):
        rule = {"kind": "finding_matches_truth", "fields": ["gtm"]}
        parsed = {"truth": {"gtm": ["GTM-A"]}, "finding": {"gtm": ["GTM-A"]}}
        self.assertIs(pass_rule.check_from_rule(rule)(parsed), True)
        self.assertIs(pass_rule.check_from_rule({"kind": "nonsense"})(parsed), False)


if __name__ == "__main__":
    unittest.main()
