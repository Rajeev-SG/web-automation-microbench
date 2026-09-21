"""F4: the vacuous-self-pass predicate must catch every empty finding shape.

The runtime's verifier already demonstrated it will self-pass on a null finding
(tldraw). A self-pass on an empty list/string/false finding is the same vacuous
case, so the predicate must cover all shapes, not only dict/None.
"""
import importlib.util
import pathlib
import unittest

RUNNER = pathlib.Path(__file__).resolve().parents[1] / "runners" / "adaptive-ui-runtime.py"


def _load():
    spec = importlib.util.spec_from_file_location("aur_adapter_probe", str(RUNNER))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class VacuousSelfPass(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def test_every_empty_shape_is_vacuous(self):
        for finding in (None, {}, [], "", 0, False):
            self.assertTrue(
                self.mod.is_vacuous_self_pass(True, False, finding),
                f"empty finding {finding!r} must be flagged vacuous")

    def test_non_empty_finding_is_not_vacuous(self):
        for finding in ({"gtm": ["GTM-A"]}, ["x"], "x", 1, True):
            self.assertFalse(self.mod.is_vacuous_self_pass(True, False, finding),
                             f"non-empty finding {finding!r} must not be flagged vacuous")

    def test_requires_runtime_pass_and_independent_fail(self):
        self.assertFalse(self.mod.is_vacuous_self_pass(False, False, None))
        self.assertFalse(self.mod.is_vacuous_self_pass(True, True, None))
        self.assertTrue(self.mod.is_vacuous_self_pass(True, False, None))


if __name__ == "__main__":
    unittest.main()
