'''This module contains an integration test of the sequence aligner module. It
verifies that a sequence containing a substitution, an insertion, and a
deletion is correctly characterized by the aligner and that the aligner's
output is correctly parsed into the appropriate entities.
'''
import unittest

from shrl.transform import align, entities

# A portion of raw HCV1a sequence containing the NS5A gene with  the following
# mutations
# 6461 A>C, or NS5A K68N
# 6658_6659insGAG, or NS6A T134_T135insE
# 6858_6861del, or NS5A S201
#
# These correspond to the following mutations in the HCV1a reference sequence
# (GenBank Accession ID: NC_004102.1)
# 6461 a>c
# 6658_6659 ins gag
# 6858_6861 del
RAW_SEQUENCE = '''
ACCACTCCATGCTCCGGTTCCTGGCTAAGGGACATCTGGGACTGGATATGCGAGGTGCTGAGCGACTTTAAGACCTGGC
TGAAAGCCAAGCTCATGCCACAACTGCCTGGGATTCCCTTTGTGTCCTGCCAGCGCGGGTATAGGGGGGTCTGGCGAGG
AGACGGCATTATGCACACTCGCTGCCACTGTGGAGCTGAGATCACTGGACATGTCAACAACGGGACGATGAGGATCGTC
GGTCCTAGGACCTGCAGGAACATGTGGAGTGGGACGTTCCCCATTAACGCCTACACCACGGGCCCCTGTACTCCCCTTC
CTGCGCCGAACTATAAGTTCGCGCTGTGGAGGGTGTCTGCAGAGGAATACGTGGAGATAAGGCGGGTGGGGGACTTCCA
CTACGTATCGGGTATGACTACTGAGGACAATCTTAAATGCCCGTGCCAGATCCCATCGCCCGAATTTTTCACAGAATTG
GACGGGGTGCGCCTACATAGGTTTGCGCCCCCTTGCAAGCCCTTGCTGCGGGAGGAGGTATCATTCAGAGTAGGACTCC
ACGAGTACCCGGTGGGGTCGCAATTACCTTGCGAGCCCGAACCGGACGTAGCCGTGTTGACGATGCTCACTGATCCCTC
CCATATAACAGCAGAGGCGGCCGGGAGAAGGTTGGCGAGAGGGTCACCCCCTTCTATGGCCAGCTCCTCGGCCAGCCAG
CTGTCCGCTCCATCTCTCAAGGCAACTTGCACCGCCAACCATGACTCCCCTGACGCCGAGCTCATAGAGGCTAACCTCC
TGTGGAGGCAGGAGATGGGCGGCAACATCACCAGGGTTGAGTCAGAGAACAAAGTGGTGATTCTGGACTCCTTCGATCC
GCTTGTGGCAGAGGAGGATGAGCGGGAGGTCTCCGTACCCGCAGAAATTCTGCGGAAGTCTCGGAGATTCGCCCGGGCC
CTGCCCGTTTGGGCGCGGCCGGACTACAACCCCCCGCTAGTAGAGACGTGGAAAAAGCCTGACTACGAACCACCTGTGG
TCCATGGCTGCCCGCTACCACCTCCACGGTCCCCTCCTGTGCCTCCGCCTCGGAAAAAGCGTACGGTGGTCCTCACCGA
ATCAACCCTATCTACTGCCTTGGCCGAGCTTGCCACCAAAAGTTTTGGCAGCTCCTCAACTTCCGGCATTACGGGCGAC
AATACGACAACATCCTCTGAGCCCGCCCCTTCTGGCTGCCCCCCCGACTCCGACGTTGAGTCCTATTCTTCCATGCCCC
CCCTGGAGGGGGAGCCTGGGGATCCGGATCTCAGCGACGGGTCATGGTCGACGGTCAGTAGTGGGGCCGACACGGAAGA
TGTCGTGTGCTGCTCAATGTCTTATTC
'''.strip().replace('\n', '')  # noqa

TEST_SEQUENCE = entities.Sequence(
    id=None,
    isolate_id=None,
    genotype="1",
    subgenotype="a",
    strain=None,
    seq_method="sanger",
    cutoff=None,
    raw_nt_seq=RAW_SEQUENCE,
    notes=None,
)


class TestAlignIntegrated(unittest.TestCase):
    def assertPairsEqual(self, pairs) -> None:
        for fst, snd in pairs:
            self.assertEqual(fst, snd)

    def test_alignment(self) -> None:
        aligned_entities = align.make_entities(
            sequence=TEST_SEQUENCE,
            genotype="1",
            subgenotype="a",
            genes=["NS5A"],
        )
        self.assertEqual(
            set(aligned_entities.keys()),
            set(("Alignment", "Substitution")),
        )
        self.assertEqual(
            len(aligned_entities["Alignment"]),
            1,
        )
        self.assertEqual(
            len(aligned_entities["Substitution"]),
            3,
        )
        sub1, sub2, sub3 = aligned_entities["Substitution"]
        self.assertPairsEqual([
            (sub1.kind, "simple"),
            (sub1.position, 68),
            (sub1.sub_aa, "N"),
        ])
        self.assertPairsEqual([
            (sub2.kind, "insertion"),
            (sub2.position, 135),
            (sub2.insertion, "E"),
        ])
        self.assertPairsEqual([
            (sub3.kind, "deletion"),
            (sub3.position, 201),
            (sub3.deletion_length, 1),
        ])
