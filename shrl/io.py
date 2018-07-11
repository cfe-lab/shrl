"""Procedures for finding and loading input files.

This module contains procedures for listing the files in a directory,
finding the files that are part of a data-load, and providing `File`
handles for parsing procedures to use.
"""

import csv
import itertools
import logging
import pathlib
import typing as ty

log = logging.getLogger(__name__)


def _downcase_csv_headers(rows: ty.Iterator[str]) -> ty.Iterator[str]:
    first = next(rows)
    return itertools.chain([first.lower()], rows)


CsvRow = ty.Dict[str, str]


class CsvSource(ty.NamedTuple):
    filename: ty.Union[str, pathlib.Path]
    reader: csv.DictReader

    @classmethod
    def from_file(
        cls, raw_rows: ty.Iterator[str], filename: str
    ) -> "CsvSource":
        rows = _downcase_csv_headers(raw_rows)
        reader = csv.DictReader(rows)
        return cls(filename=filename, reader=reader)

    @classmethod
    def from_filepath(
        cls, filepath: ty.Union[str, pathlib.Path]
    ) -> "CsvSource":
        filepath = pathlib.Path(filepath)
        if not filepath.is_file():
            msg = f"No file at '{filepath}'"
            raise ValueError(msg)
        infile = open(filepath)
        filename = filepath.name
        return cls.from_file(raw_rows=infile, filename=filename)
