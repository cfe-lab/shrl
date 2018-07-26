"Functions for extracting shared-schema entities from submission-scheme cases"

import enum
import typing as ty
import uuid

from Bio import SeqRecord as seqrecord

import shared_schema.regimens as ss_regimens
from shrl import case, exceptions, field

from . import align, entities, util


class TransformationException(exceptions.ShrlException):
    pass


def make_case(
    person_id: uuid.UUID, study_id: uuid.UUID, c: case.Case
) -> entities.Case:
    return entities.Case(
        id=uuid.uuid4(),
        person_id=person_id,
        study_id=study_id,
        country=c.participant["country"],
        study_participant_id=c.participant["id"],
    )


def make_person(c: case.Case) -> entities.Person:
    return entities.Person(
        id=uuid.uuid4(),
        sex=c.participant["sex"],
        ethnicity=c.participant["ethnicity"],
        year_of_birth=c.participant["year_of_birth"],
    )


def make_loss_to_followup(
    case_id: uuid.UUID, c: case.Case
) -> entities.LossToFollowUp:
    ltfu_year = c.participant["ltfu_year"]
    died = c.participant["died"]
    cod = c.participant["cod"]

    return entities.LossToFollowUp(
        case_id=case_id, ltfu_year=ltfu_year, died=died, cod=cod
    )


def make_behavior_data(
    case_id: uuid.UUID, c: case.Case
) -> entities.BehaviorData:
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


def make_clinical_data(
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

    def parse_one(src: case.Clinical) -> ty.Optional[entities.ClinicalData]:
        kwargs = {fld: src.values[fld] for fld in flds}
        if all(v is None for v in kwargs.values()):
            return None
        return entities.ClinicalData(
            id=uuid.uuid4(), case_id=case_id, **kwargs
        )

    return [
        parse_one(clinical)
        for clinical in c.clinical
        if parse_one(clinical) is not None
    ]


def make_treatment_data(
    rreg: util.RegimenRegistry, case_id: uuid.UUID, c: case.Case
) -> ty.List[entities.TreatmentData]:
    def tx_data(cln: case.Clinical) -> entities.TreatmentData:
        tx_id = uuid.uuid4()

        def get_reg_id(key: str) -> ty.Optional[uuid.UUID]:
            src = cln.values.get(key)
            if src is None:
                return None
            expanded = ss_regimens.standard.expand(src)
            reg = ss_regimens.cannonical.from_string(expanded)
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


def _get_enum_name(e_member: ty.Optional[field.FieldType]) -> str:
    assert e_member is not None
    assert isinstance(e_member, enum.Enum)
    return str(e_member.name)


def make_isolate_entities(
    case_id: uuid.UUID, seq_registry: util.SequenceRegistry, c: case.Case
) -> align.AlignmentEntities:
    results: align.AlignmentEntities = {
        "Isolate": [],
        "ClinicalIsolate": [],
        "Sequence": [],
        "Alignment": [],
        "Substitution": [],
    }
    for clinical in c.clinical:
        isolate = entities.Isolate(id=uuid.uuid4(), type="clinical")
        results["Isolate"].append(isolate)
        clinical_isolate = entities.ClinicalIsolate(
            isolate_id=isolate.id,
            case_id=case_id,
            sample_kind=str(clinical.values["kind"]),
        )
        results["ClinicalIsolate"].append(clinical_isolate)
        for seq in clinical.sequences:
            seq_id = seq.get("seq_id")
            if seq_id is None:
                msg = f"Missing sequence id for case:\n{c}"
                raise TransformationException(msg)
            else:
                seq_id = str(seq_id)
            raw_seq: seqrecord.SeqRecord = seq_registry.get(seq_id)
            sub_gt_src = seq.get("subegnotype", None)
            sub_gt = str(sub_gt_src) if sub_gt_src is not None else None
            gene_str = _get_enum_name(seq["gene"]).upper()
            genotype_str = _get_enum_name(seq["genotype"])
            sequence = entities.Sequence(
                id=uuid.uuid4(),
                isolate_id=isolate.id,
                genotype=genotype_str,
                subgenotype=sub_gt,
                strain=seq["strain"],
                seq_method=seq["seq_method"],
                cutoff=seq["cutoff"],
                raw_nt_seq=str(raw_seq.seq),
                notes=seq["seq_notes"],
            )
            aln_entities = align.make_entities(
                sequence=sequence,
                genotype=genotype_str,
                subgenotype=sub_gt,
                genes=[gene_str],
            )
            for kind, ents in aln_entities.items():
                results[kind].extend(ents)
            results["Sequence"].append(sequence)

    return results


EntitiesMapping = ty.Dict[str, ty.List[ty.NamedTuple]]


def case_entities(
    seq_registry: util.SequenceRegistry,
    rreg: util.RegimenRegistry,
    c: case.Case,
    study_id: uuid.UUID,
) -> EntitiesMapping:
    person = make_person(c)
    case_entity = make_case(person.id, study_id, c)
    case_id = case_entity.id
    ltfu = make_loss_to_followup(case_id, c)
    behavior_data = make_behavior_data(case_id, c)
    clinical_data = make_clinical_data(case_id, c)
    results = {
        "Person": [person],
        "Case": [case_entity],
        "LossToFollowUp": [ltfu],
        "BehaviorData": [behavior_data],
        "ClinicalData": clinical_data,
        "TreatmentData": make_treatment_data(rreg, case_id, c),
    }
    isolate_entities = make_isolate_entities(case_id, seq_registry, c)
    assert all(k not in results for k in isolate_entities)
    results.update(isolate_entities)
    return results
