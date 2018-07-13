"Functions for extracting shared-schema entities from submission-scheme cases"

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
