import re
import unittest

import hypothesis
import hypothesis.strategies as st

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


class TestEnsureFastaFormat(unittest.TestCase):
    @hypothesis.given(st.text())
    def test_fasta_formatted_leaves_formatted(self, content):
        tmpl = "> Sequence-Ish\n{seq}"
        seq = tmpl.format(seq=content)
        self.assertEqual(seq, align.ensure_fasta_formatted(seq))

    @hypothesis.given(st.text())
    def test_fasta_formatter_is_idempotent(self, seq):
        self.assertEqual(
            align.ensure_fasta_formatted(seq),
            align.ensure_fasta_formatted(align.ensure_fasta_formatted(seq)),
        )

    HEADER_PATTERN = re.compile("> [a-zA-Z0-9_ ]+")

    @hypothesis.given(st.text())
    def test_fasta_formatter_output_looks_like_a_fasta_file(self, seq):
        outp = align.ensure_fasta_formatted(seq)
        assert outp.startswith("> ")
        assert self.HEADER_PATTERN.match(outp)
