"Functions for extracting shared-schema entities from submission-scheme cases"

import typing as ty
import uuid

import shared_schema.regimens as ss_regimens
from shrl import case

from . import entities, util


def loss_to_followup(
    case_id: uuid.UUID, c: case.Case
) -> entities.LossToFollowUp:
    ltfu_year = c.participant["ltfu_year"]
    died = c.participant["died"]
    cod = c.participant["cod"]

    return entities.LossToFollowUp(
        case_id=case_id, ltfu_year=ltfu_year, died=died, cod=cod
    )


def behavior_data(case_id: uuid.UUID, c: case.Case) -> entities.BehaviorData:
    id = uuid.uuid4()

    bhv = c.behavior

    return entities.BehaviorData(
        id=id,
        case_id=case_id,
        sex_ori=bhv.get("sex_ori"),
        idu=bhv.get("idu"),
        idu_recent=bhv.get("idu_recent"),
        ndu=bhv.get("ndu"),
        ndu_recent=bhv.get("ndu_recent"),
        prison=bhv.get("prison"),
    )


def clinical_data(
    case_id: uuid.UUID, c: case.Case
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
            id=uuid.uuid4(), case_id=case_id, **kwargs
        )

    return [parse_one(clinical) for clinical in c.clinical]


def treatment_data(
    rreg: util.RegimenRegistry, case_id: uuid.UUID, c: case.Case
) -> ty.List[entities.TreatmentData]:
    def tx_data(cln: case.Clinical) -> entities.TreatmentData:
        tx_id = uuid.uuid4()

        def get_reg_id(key: str) -> ty.Optional[uuid.UUID]:
            src = cln.values.get(key)
            if src is None:
                return None
            reg = ss_regimens.cannonical.from_string(src)
            reg_id = rreg.get_or_create_id(reg)
            return reg_id

        return entities.TreatmentData(
            id=tx_id,
            case_id=case_id,
            first_treatment=cln.values.get("first_treatment"),
            duration_act=cln.values.get("duration_act"),
            regimen_id=get_reg_id("regimen"),
            prev_regimen_id=get_reg_id("prev_regimen"),
            pprev_regimen_id=get_reg_id("pprev_regimen"),
            response=cln.values.get("response"),
            notes=cln.values.get("treatment_notes"),
        )

    return [tx_data(cln) for cln in c.clinical]
