import unittest

from shrl.transform import isolate

from . import test_integrated_align


class TestSimpleIsolateIntegrated(unittest.TestCase):
    def is_namedtuple_with_attrs(self, item, attrs):
        self.assertIsInstance(item, tuple)
        self.assertGreater(
            len(item.__class__.__mro__),
            2,
            "Expected more than two classes in NamedTuple's MRO",
        )
        for attr in attrs:
            self.assertTrue(
                hasattr(item, attr),
                "Missing expected attribute: {attr}".format(attr=attr),
            )

    def test_integrated(self):
        clinical_isolate_params = {
            "person_id": 0,
            "sample_kind": "bl",
        }
        sequence_params = {
            "strain": None,
            "seq_method": "sanger",
            "cutoff": 0.15,
            "notes": None,
        }
        entities = isolate.make_entities(
            genotype="1",
            subgenotype="a",
            genes=["NS5A"],
            raw_nt_seq=test_integrated_align.RAW_SEQUENCE,
            sequence_params=sequence_params,
            clinical_isolate_params=clinical_isolate_params,
        )
        self.assertEqual(
            set(entities.keys()),
            set((
                "Isolate",
                "ClinicalIsolate",
                "Sequence",
                "Alignment",
                "Substitution",
            )),
        )
        for key in ("Isolate", "ClinicalIsolate", "Sequence", "Alignment"):
            self.assertEqual(
                len(entities[key]),
                1,
            )
        self.is_namedtuple_with_attrs(
            entities["Isolate"][0],
            ("id", "type"),
        )
        self.is_namedtuple_with_attrs(
            entities["ClinicalIsolate"][0],
            ("isolate_id", "person_id", "sample_kind"),
        )
        self.is_namedtuple_with_attrs(entities["Sequence"][0], (
            "id",
            "isolate_id",
            "genotype",
            "subgenotype",
            "strain",
            "seq_method",
            "cutoff",
            "raw_nt_seq",
            "notes",
        ))
