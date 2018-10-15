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
import shared_schema.data
import shared_schema.tables
import shrl.case
import shrl.io
import shrl.metadata
import shrl.report
import shrl.row
import shrl.transform

log = logging.getLogger(__name__)

SCHEMA_DATA = shared_schema.data.schema_data


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
    # Exhaust any iterators
    for entity_set in entity_sets:
        for entities in entity_set.values():
            for entity in entities:
                pass
    log.info("All rows loaded successfully")
    shrl.report.print_report()


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
            raise e
        finally:
            db_connection.close()


EntitySet = ty.Dict[str, ty.List[ty.NamedTuple]]


class EntityManager:
    def __init__(self, dao: shared_schema.dao.DAO, eset: EntitySet) -> None:
        self.dao = dao
        self.eset = eset

    def insert_entity(self, entityname: str) -> None:
        entities = self.eset[entityname]
        if len(entities) != 1:
            raise ValueError(
                "Expected a single entity; got {}".format(len(entities))
            )
        entity = entities[0]
        tablename = entityname.lower()
        self.dao.insert(tablename, entity._asdict())

    def insert_entities_if_not_empty(self, entityname: str) -> None:
        """Insert any entities that have non-null 'value fields'

        A 'value field' is any field that's not a foreign key or a UUID

        Note that this doesn't guarantee that the insertion will succeed. For
        example, fields might have invalid types, or required fields might be
        missing.
        """
        ent_def = SCHEMA_DATA.get_entity(entityname)
        value_fields: ty.List[shared_schema.tables.Field] = [
            fld.name
            for fld in ent_def.fields
            if ("foreign key" not in fld.type)
            and (fld.name != "id")
            and (not fld.name == "uuid")
        ]
        entities = self.eset[entityname]
        tablename = entityname.lower()
        for ent in entities:
            item = ent._asdict()
            if any(item.get(fldname) for fldname in value_fields):
                self.dao.insert(tablename, item)


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
        entities = shrl.transform.case_entities(sreg, rreg, case, study_name)
        shrl.report.count_entities(entities)
        yield entities


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

    # Create Case and ClinicalIsolate Entities
    for ents in entity_sets:
        # This is written out explicitly because the order of insertions
        # matters; records referred to by foreign keys must be created before
        # their dependents.
        emanager = EntityManager(dao, ents)
        emanager.insert_entity("Person")
        emanager.insert_entity("Case")
        emanager.insert_entities_if_not_empty("LossToFollowUp")
        emanager.insert_entities_if_not_empty("BehaviorData")
        emanager.insert_entities_if_not_empty("ClinicalData")
        emanager.insert_entities_if_not_empty("TreatmentData")
        emanager.insert_entities_if_not_empty("Isolate")
        emanager.insert_entities_if_not_empty("ClinicalIsolate")
        emanager.insert_entities_if_not_empty("Sequence")
        emanager.insert_entities_if_not_empty("Alignment")
        emanager.insert_entities_if_not_empty("Substitution")


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
