import unittest
import uuid

from shared_schema import regimens as ss_regimens
from shrl import case
from shrl.transform import convert, entities, util

EXAMPLE_CASE = case.Case(
    participant={
        "id": 1,
        "country": "ca",
        "sex": "other",
        "ethnicity": "white",
        "year_of_birth": None,
        "ltfu": True,
        "ltfu_year": 2018,
        "died": False,
        "cod": None,
    },
    behavior={
        "sex_ori": None,
        "idu": True,
        "idu_recent": None,
        "ndu": False,
        "ndu_recent": None,
        "prison": None,
    },
    clinical=[
        case.Clinical(
            values={
                "kind": "bl",
                "hiv": False,
                "hbv": False,
                "ost": True,
                "cirr": None,
                "fibrosis": None,
                "inflamation": None,
                "metavir_by": None,
                "stiff": None,
                "alt": 0.5,
                "ast": 1.5,
                "crt": 2.5,
                "egfr": None,
                "ctp": None,
                "meld": None,
                "ishak": None,
                "bil": None,
                "hemo": None,
                "alb": 3.5,
                "inr": None,
                "phos": 4.5,
                "urea": 5.5,
                "plate": 6,
                "CD4": None,
                "crp": None,
                "il28b": "TC",
                "asc": None,
                "var_bleed": True,
                "hep_car": False,
                "transpl": False,
                "vl": 1778,
                "first_treatment": False,
                "duration_act": None,
                "regimen": "DAKLINZA",
                "prev_regimen": "EPCLUSA",
                "pprev_regimen": None,
                "response": None,
                "treatment_notes": "It's a pretty good treatment.",
            },
            sequences=[
                {
                    "seq_kind": "bl",
                    "genotype": "1",
                    "subgenotype": "a",
                    "strain": None,
                    "seq_id": "example-seq-id",
                    "gene": "ns5a",
                    "seq_method": "sanger",
                    "cutoff": 15,
                    "seq_notes": "It's a pretty good sequence.",
                }
            ],
        ),
        case.Clinical(
            sequences=[],
            values={
                "kind": "eot",
                "hiv": False,
                "hbv": False,
                "ost": True,
                "cirr": None,
                "fibrosis": None,
                "inflamation": None,
                "metavir_by": None,
                "stiff": None,
                "alt": 0.5,
                "ast": 1.5,
                "crt": 2.5,
                "egfr": None,
                "ctp": None,
                "meld": None,
                "ishak": None,
                "bil": None,
                "hemo": None,
                "alb": 3.5,
                "inr": None,
                "phos": 4.5,
                "urea": 5.5,
                "plate": 6,
                "CD4": None,
                "crp": None,
                "il28b": "TC",
                "asc": None,
                "var_bleed": True,
                "hep_car": False,
                "transpl": False,
                "vl": 1888,
                "first_treatment": False,
                "duration_act": 89,
                "regimen": "DAKLINZA",
                "prev_regimen": "EPCLUSA",
                "pprev_regimen": None,
                "response": "bt",
                "treatment_notes": "On second thought, not so good.",
            },
        ),
    ],
)


class TestBasicConversionFunctions(unittest.TestCase):
    "Test conversion functions that reorganize data but don't change it."

    def compare_fields(self, flds, src, trn):
        def compare_field(fld):
            val1 = src[fld]
            val2 = getattr(trn, fld)
            msg = "Expected '{fld}' field to be equal".format(fld=fld)
            self.assertEqual(val1, val2, msg)

        for fld in flds:
            compare_field(fld)

    def test_loss_to_followup(self):
        case_id = uuid.uuid4()
        expected_ltfu = entities.LossToFollowUp(
            case_id=case_id, ltfu_year=2018, died=False, cod=None
        )
        constructed_ltfu = convert.loss_to_followup(
            case_id=case_id, c=EXAMPLE_CASE
        )
        self.assertEqual(constructed_ltfu, expected_ltfu)

    def test_behavior_data(self):
        case_id = uuid.uuid4()
        constructed_behavior_data = convert.behavior_data(
            case_id=case_id, c=EXAMPLE_CASE
        )
        flds = ("sex_ori", "idu", "idu_recent", "ndu", "ndu_recent", "prison")
        self.compare_fields(
            flds, EXAMPLE_CASE.behavior, constructed_behavior_data
        )
        self.assertIsInstance(constructed_behavior_data.id, uuid.UUID)
        self.assertEqual(constructed_behavior_data.case_id, case_id)

    def test_clinical_data(self):
        case_id = uuid.uuid4()
        constructed_clinical_data = convert.clinical_data(
            case_id, c=EXAMPLE_CASE
        )
        self.assertEqual(
            2,
            len(constructed_clinical_data),
            "Expected two clinical records to be transformed.",
        )
        flds = (
            "kind",
            "hiv",
            "hbv",
            "ost",
            "cirr",
            "fibrosis",
            "inflamation",
            "metavir_by",
            "stiff",
            "alt",
            "ast",
            "crt",
            "egfr",
            "ctp",
            "meld",
            "ishak",
            "bil",
            "hemo",
            "alb",
            "inr",
            "phos",
            "urea",
            "plate",
            "CD4",
            "crp",
            "il28b",
            "asc",
            "var_bleed",
            "hep_car",
            "transpl",
            "vl",
        )
        for src, trn in zip(EXAMPLE_CASE.clinical, constructed_clinical_data):
            self.assertEqual(trn.case_id, case_id)
            self.assertIsInstance(trn.id, uuid.UUID)
            self.compare_fields(flds, src.values, trn)

    def test_treatment_data(self):
        case_id = uuid.uuid4()
        rreg = util.RegimenRegistry()
        constructed_treatment_data = convert.treatment_data(
            rreg, case_id, EXAMPLE_CASE
        )
        expected_regimen = ss_regimens.cannonical.from_string("DAKLINZA")
        for tx in constructed_treatment_data:
            self.assertEqual(tx.case_id, case_id)
            self.assertIsInstance(tx.id, uuid.UUID)
            self.assertIsInstance(tx.regimen, uuid.UUID)
            self.assertIn(expected_regimen, rreg)
