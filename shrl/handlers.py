"""Functions that perform high-level tasks"""
import argparse
import logging
import os
import pathlib
import secrets
import sys
import textwrap
import typing as ty

import shrl.case
import shrl.io
import shrl.metadata
import shrl.row
import shrl.transform

log = logging.getLogger(__name__)


def init_sequence_registry(
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


EntitySet = ty.Dict[str, ty.List[ty.NamedTuple]]


def _load_entities(args: argparse.Namespace) -> ty.Iterable[EntitySet]:
    metadata: ty.Optional[shrl.metadata.StudyData]
    if args.with_metadata is not None:
        log.info(f"Loading study data from {args.with_metadata}")
        metadata = shrl.metadata.parse(args.with_metadata)
        study_name = metadata.source_study.name
    else:
        study_name = secrets.token_hex()
        log.info(f"Using dummy study_name: {study_name}")
        metadata = None
    base_dir = pathlib.Path(args.directory)
    participants_file = base_dir / "participants.csv"
    if not participants_file.is_file():
        log.error(f"{participants_file} isn't a file")
        sys.exit(1)
    rreg = shrl.transform.RegimenRegistry()
    sreg = init_sequence_registry(base_dir)
    csv_source = shrl.io.CsvSource.from_filepath(participants_file)
    log.info("Loading Rows")
    loaded_rows = list(shrl.row.load_rows(csv_source))
    cases = shrl.case.cases(loaded_rows)
    for case in cases:
        yield shrl.transform.case_entities(sreg, rreg, case, study_name)
    log.info("All rows loaded successfully")


def check(args: argparse.Namespace) -> None:
    "Check that a data directory is formatted as expected"
    # Exhaust the entity iterator to make sure everything is actually loaded
    log.info("Performing format check")
    for entity_set in _load_entities(args):
        for entities in entity_set.values():
            for entity in entities:
                pass


def report(args: argparse.Namespace) -> None:
    ...


def load(args: argparse.Namespace) -> None:
    ...
