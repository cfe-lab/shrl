import unittest
import uuid

from shrl import case
from shrl.transform import convert, entities

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

    def compare_fields(self, flds, obj1, obj2):
        def compare_field(fld):
            val1 = getattr(obj1, fld)
            val2 = getattr(obj2, fld)
            msg = "Expected '{fld}' field to be equal".format(fld=fld)
            self.assertEqual(val1, val2, msg)

        for fld in flds:
            compare_field(fld)

    def test_loss_to_followup(self):
        person_id = uuid.uuid4()
        expected_ltfu = entities.LossToFollowUp(
            person_id=person_id, ltfu_year=2018, died=False, cod=None
        )
        constructed_ltfu = convert.loss_to_followup(
            person_id=person_id, c=EXAMPLE_CASE
        )
        self.assertEqual(constructed_ltfu, expected_ltfu)

    def test_behavior_data(self):
        person_id = uuid.uuid4()
        expected_behavior_data = entities.BehaviorData(
            person_id=person_id,
            sex_ori=None,
            idu=True,
            idu_recent=None,
            ndu=False,
            ndu_recent=None,
            prison=None,
            id=None,
        )
        constructed_behavior_data = convert.behavior_data(
            person_id=person_id, c=EXAMPLE_CASE
        )
        flds = (
            "person_id",
            "sex_ori",
            "idu",
            "idu_recent",
            "ndu",
            "ndu_recent",
            "prison",
        )
        self.compare_fields(
            flds, constructed_behavior_data, expected_behavior_data
        )
        self.assertIsInstance(constructed_behavior_data.id, uuid.UUID)
