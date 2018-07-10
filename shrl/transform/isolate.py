'''Tools for extracting Isolate, Sequence, and Alignment entities from
raw data in the submission scheme.
'''

import logging
import typing as ty
import uuid

from . import align, entities

log = logging.getLogger(__name__)


def sequence(
        raw_nt_seq: str,
        isolate_id: uuid.UUID,
        seq_params: ty.Dict[ty.Any, ty.Any],
) -> entities.Sequence:
    return entities.Sequence(
        id=uuid.uuid4(),
        isolate_id=isolate_id,
        raw_nt_seq=raw_nt_seq,
        **seq_params,
    )


IsolateEntities = ty.Dict[str, ty.List[ty.NamedTuple]]


def make_entities(
        genotype: str,
        subgenotype: str,
        genes: ty.List[str],
        raw_nt_seq: str,
        sequence_params: ty.Dict[str, ty.Any],
        clinical_isolate_params: ty.Optional[ty.Dict[str, ty.Any]] = None,
) -> IsolateEntities:
    isolate = entities.Isolate(id=uuid.uuid4(), type='clinical')
    if clinical_isolate_params is not None:
        clinical_isolate = entities.ClinicalIsolate(
            isolate_id=isolate.id,
            **clinical_isolate_params,
        )
        clinical_isolate_entities = [clinical_isolate]
    else:
        clinical_isolate_entities = []
    sequence_params.update({
        "genotype": genotype,
        "subgenotype": subgenotype,
    })
    seq = sequence(
        raw_nt_seq=raw_nt_seq,
        isolate_id=isolate.id,
        seq_params=sequence_params,
    )
    alignment_entities = align.make_entities(
        sequence=seq,
        genotype=genotype,
        subgenotype=subgenotype,
        genes=genes,
    )
    return {
        "Isolate": [isolate],
        "ClinicalIsolate": clinical_isolate_entities,
        "Sequence": [seq],
        **alignment_entities,
    }
