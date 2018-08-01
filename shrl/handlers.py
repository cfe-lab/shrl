"""Functions that perform CLI tasks (load, check, report)"""
import argparse
import logging
import os
import pathlib
import secrets
import sys
import textwrap
import typing as ty

import shared_schema.dao
import shrl.case
import shrl.io
import shrl.metadata
import shrl.row
import shrl.transform

log = logging.getLogger(__name__)


def check(args: argparse.Namespace) -> None:
    "Check that a data directory is formatted as expected"
    # Exhaust the entity iterator to make sure everything is actually loaded
    log.info("Performing format check")
    base_dir = pathlib.Path(args.directory)
    rreg = shrl.transform.RegimenRegistry()
    sreg = _init_sequence_registry(base_dir)
    study_data = _init_meta(args)
    entity_sets = _load_entities(
        args, rreg=rreg, sreg=sreg, study_data=study_data
    )
    for entity_set in entity_sets:
        for entities in entity_set.values():
            for entity in entities:
                pass
    log.info("All rows loaded successfully")


def report(args: argparse.Namespace) -> None:
    ...


def load(args: argparse.Namespace) -> None:
    db_url = args.database
    if not db_url:
        _halt_with("Missing database url")

    base_dir = pathlib.Path(args.directory)
    if not base_dir:
        _halt_with(f"Invlaid data directory: {args.directory}")

    study_data = _init_meta(args)
    if study_data is None:
        _halt_with("Study metadata is required for loading data")
        return  # Lets mypy know that study_data is not None hereafter.

    dao = shared_schema.dao.DAO(db_url)
    if args.init_db:
        dao.init_db()
    if args.load_regimens:
        dao.load_standard_regimens()

    rreg = shrl.transform.RegimenRegistry.init_from_dao(dao)
    sreg = _init_sequence_registry(base_dir)

    # Force evaluation of the entity sets so that the regimen registry is
    # populated before we start inserting case entities. This is necessary
    # because case entities depend on the entities from the registry.
    entity_sets = list(
        _load_entities(args, rreg=rreg, sreg=sreg, study_data=study_data)
    )

    db_connection = dao.engine.connect()

    with db_connection.begin() as trn:
        try:
            _save_entities(
                entity_sets=entity_sets,
                sreg=sreg,
                rreg=rreg,
                dao=dao,
                study_data=study_data,
            )
        except Exception as e:
            log.error(e)
            trn.rollback()
    db_connection.close()


EntitySet = ty.Dict[str, ty.List[ty.NamedTuple]]


def _load_entities(
    args: argparse.Namespace,
    rreg: shrl.transform.RegimenRegistry,
    sreg: shrl.transform.SequenceRegistry,
    study_data: ty.Optional[shrl.metadata.StudyData],
) -> ty.Iterable[EntitySet]:
    if study_data is not None:
        study_name = study_data.source_study.name
    else:
        study_name = secrets.token_hex()
        log.info(f"Using dummy study_name: {study_name}")
    base_dir = pathlib.Path(args.directory)
    participants_file = base_dir / "participants.csv"
    if not participants_file.is_file():
        _halt_with(f"{participants_file} isn't a file")
    csv_source = shrl.io.CsvSource.from_filepath(participants_file)
    log.info("Loading Rows")
    loaded_rows = list(shrl.row.load_rows(csv_source))
    cases = shrl.case.cases(loaded_rows)
    for case in cases:
        yield shrl.transform.case_entities(sreg, rreg, case, study_name)


def _save_entities(
    entity_sets: ty.Iterable[EntitySet],
    rreg: shrl.transform.RegimenRegistry,
    sreg: shrl.transform.SequenceRegistry,
    dao: shared_schema.dao.DAO,
    study_data: shrl.metadata.StudyData,
) -> None:

    # Create Collaborator, SourceStudy, and References
    meta_handle = shrl.metadata.StudyDataDatabaseHandle(study_data, dao)
    meta_handle.check_existing()
    meta_handle.create_new()

    # Create Regimens and RegimenDrugInclusions
    rreg.sync_to_dao(dao)

    # Create case entities
    for ents in entity_sets:
        # This is written out explicitly because the order of insertions
        # matters; records referred to by foreign keys must be created before
        # their dependents.
        dao.insert("person", _as_items(ents["Person"]))
        dao.insert("case", _as_items(ents["Case"]))
        dao.insert("losstofollowup", _as_items(ents["LossToFollowUp"]))
        dao.insert("behaviordata", _as_items(ents["BehaviorData"]))
        dao.insert("clinicaldata", _as_items(ents["ClinicalData"]))
        dao.insert("treatmentdata", _as_items(ents["TreatmentData"]))
        dao.insert("isolate", _as_items(ents["Isolate"]))
        dao.insert("clinicalisolate", _as_items(ents["ClinicalIsolate"]))
        dao.insert("sequence", _as_items(ents["Sequence"]))
        dao.insert("alignment", _as_items(ents["Alignment"]))
        dao.insert("substitution", _as_items(ents["Substitution"]))


def _as_items(
    entities: ty.List[ty.NamedTuple]
) -> ty.List[ty.Dict[str, ty.Any]]:
    return [t._asdict() for t in entities]


def _halt_with(msg: str) -> None:
    log.error(msg)
    sys.exit(1)


def _init_sequence_registry(
    base_path: pathlib.Path
) -> shrl.transform.SequenceRegistry:
    seq_dir = base_path / "sequences"
    log.info(f"Loading sequences from {seq_dir}")
    files = os.listdir(seq_dir)
    filepaths = [
        seq_dir / fname for fname in files if fname.lower().endswith("fasta")
    ]
    file_list = textwrap.indent("\n".join(str(p) for p in filepaths), " - ")
    log.info(f"Sequence files: \n{file_list}")
    return shrl.transform.SequenceRegistry.from_files(filepaths)


def _init_meta(
    args: argparse.Namespace
) -> ty.Optional[shrl.metadata.StudyData]:
    study_data: ty.Optional[shrl.metadata.StudyData]
    if args.with_metadata is not None:
        study_data = shrl.metadata.parse(args.with_metadata)
    else:
        log.info("No metadata provided")
        study_data = None
    return study_data
