import unittest

import shrl.transform.align as align


class TestProfileName(unittest.TestCase):
    def test_finding_profile_names(self):
        cases = [
            ("1", "a", "hcv1a"),
            ("1", "b", "hcv1b"),
            ("2", "a", "hcv2"),
            ("2", None, "hcv2"),
        ]
        cases.extend([(str(gt), None, f"hcv{gt}") for gt in (3, 4, 5, 6)])
        for gt, subgt, expected_profile in cases:
            self.assertEqual(align.profile_name(gt, subgt), expected_profile)

    def test_raising_on_unhandleable_profile_names(self):
        cases = [
            ("mixed", "a"),
            ("indeterminate", "b"),
            ("recombinant", "c"),
            (1, None),
            (None, None),
            ("1", "asdf"),
        ]
        for case in cases:
            self.assertRaises(ValueError, align.profile_name, *case)
