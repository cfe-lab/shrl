"Functions for extracting shared-schema entities from submission-scheme cases"

import typing as ty
import uuid

from shrl import case

from . import entities


def loss_to_followup(
    person_id: uuid.UUID, c: case.Case
) -> entities.LossToFollowUp:
    ltfu_year = c.participant["ltfu_year"]
    died = c.participant["died"]
    cod = c.participant["cod"]

    return entities.LossToFollowUp(
        person_id=person_id, ltfu_year=ltfu_year, died=died, cod=cod
    )


def behavior_data(person_id: uuid.UUID, c: case.Case) -> entities.BehaviorData:
    id = uuid.uuid4()

    bhv = c.behavior

    return entities.BehaviorData(
        id=id,
        person_id=person_id,
        sex_ori=bhv.get("sex_ori"),
        idu=bhv.get("idu"),
        idu_recent=bhv.get("idu_recent"),
        ndu=bhv.get("ndu"),
        ndu_recent=bhv.get("ndu_recent"),
        prison=bhv.get("prison"),
    )


def clinical_data(
    person_id: uuid.UUID, c: case.Case
) -> ty.List[entities.ClinicalData]:
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

    def parse_one(src: case.Clinical) -> entities.ClinicalData:
        kwargs = {fld: src.values[fld] for fld in flds}
        return entities.ClinicalData(
            id=uuid.uuid4(), person_id=person_id, **kwargs
        )

    return [parse_one(clinical) for clinical in c.clinical]
