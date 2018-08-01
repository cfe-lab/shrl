"""Parse and load metadata from a .conf file

The supported items in the configuration file are one Collaborator,
one SourceStudy, and any number of References.

```conf
[collaborator]
id = A UUID (e.g. 206a5262-d158-4c5f-b1d7-415e2fcded4b)
name = The collaborator's name (be it an individual or an organization)

[sourcestudy]
name = The study's name
start_year = The year data collection began
end_year = The year data collection ended
notes =
  Any notes that might be helpful, which can
  span several lines as long as they're indented.

[reference.1]
id = A unique ID (for linking to an existing Reference in the database)
author = The reference's author
title = The reference's title
journal = The journal where this reference was published
publication_dt = The reference's date of publication (YYYY-MM-DD)
url = A URL where this reference can be accessed
pubmed_id = If applicable, the reference's PubMed ID
```

Person records loaded with metadata will be associated with the
SourceStudy. The SourceStudy will be associated with the
Collaborator, and with any references provided in the metadata file.
"""

import configparser
import datetime
import logging
import typing as ty
import uuid

import shared_schema.dao
import shrl.exceptions

log = logging.getLogger(__name__)


class MetadataError(shrl.exceptions.ShrlException):
    "Indicates a fatal problem in the study metadata"

    def __init__(self, section: str, detail: str) -> None:
        self.section = section
        self.detail = detail

    def __str__(self) -> str:
        tmpl = "Metadata error ({section}): {detail}"
        return tmpl.format(section=self.section, detail=self.detail)


class DatabaseMismatchError(shrl.exceptions.ShrlException):
    def __init__(self, tbl: str, detail: str) -> None:
        self.tbl = tbl
        self.detail = detail

    def __str__(self) -> str:
        return f"Existing data mismatch error in {self.tbl}: {self.detail}"


class Collaborator(ty.NamedTuple):
    id: uuid.UUID
    name: str


class SourceStudy(ty.NamedTuple):

    name: str
    start_year: int
    end_year: ty.Optional[int]
    notes: ty.Optional[str]


class Reference(ty.NamedTuple):
    id: uuid.UUID
    author: str
    title: str
    journal: ty.Optional[str]
    url: ty.Optional[str]
    publication_dt: ty.Optional[datetime.date]
    pubmed_id: ty.Optional[str]


class StudyData(ty.NamedTuple):
    source_study: SourceStudy
    collaborators: ty.List[Collaborator]
    references: ty.List[Reference]


def collaborators(parser: configparser.ConfigParser) -> ty.List[Collaborator]:
    collab_sections = [
        secname
        for secname in parser.sections()
        if secname.startswith("collaborator")
    ]
    if len(collab_sections) <= 0:
        raise MetadataError(
            "collaborator", "We need at least one collaborator section"
        )
    result = []
    for section_name in collab_sections:
        raw_args = parser[section_name]
        collab_id_src = raw_args.get("id")
        if collab_id_src is None:
            raise MetadataError(section_name, "Missing field: id")
        try:
            collab_id = uuid.UUID(collab_id_src)
        except ValueError as ve:
            msg = "invalid uuid: {}".format(ve)
            raise MetadataError(section_name, msg)
        result.append(Collaborator(id=collab_id, name=raw_args["name"]))
    return result


def source_study(parser: configparser.ConfigParser) -> SourceStudy:
    if "sourcestudy" not in parser:
        raise MetadataError(
            "sourcestudy", "Missing required section 'sourcestudy'"
        )
    raw_args = parser["sourcestudy"]
    raw_notes = raw_args["notes"]
    if raw_notes is None:
        notes = None
    else:
        notes = raw_notes.strip()
    try:
        return SourceStudy(
            name=raw_args["name"],
            start_year=int(raw_args["start_year"]),
            end_year=int(raw_args["end_year"]),
            notes=notes,
        )
    except ValueError:
        raise MetadataError("sourcestudy", "Invalid field")


def references(parser: configparser.ConfigParser) -> ty.List[Reference]:
    reference_sections = (
        secname
        for secname in parser.sections()
        if secname.startswith("reference")
    )
    result = []
    for secname in reference_sections:
        raw_args = parser[secname]
        if raw_args.get("id") is None:
            ref_id = uuid.uuid4()
        else:
            ref_id = uuid.UUID(raw_args.get("id"))
        publication_dt_src = raw_args.get("publication_dt")
        if publication_dt_src is not None:
            date_fmt = "%Y-%m-%d"
            dt = datetime.datetime.strptime(publication_dt_src, date_fmt)
            pub_date = dt.date()
        else:
            pub_date = None

        reference = Reference(
            id=ref_id,
            author=raw_args["author"],
            title=raw_args["title"],
            journal=raw_args.get("journal"),
            url=raw_args.get("url"),
            publication_dt=pub_date,
            pubmed_id=raw_args.get("pubmed_id"),
        )
        result.append(reference)
    return result


def extract(parser: configparser.ConfigParser) -> StudyData:
    if not parser.has_section("collaborator"):
        raise MetadataError(
            "collaborator", "Missing required section 'collaborator'"
        )
    collab = collaborators(parser)
    sstudy = source_study(parser)
    refs = references(parser)
    return StudyData(
        collaborators=collab, source_study=sstudy, references=refs
    )


def get_parser() -> configparser.ConfigParser:
    return configparser.ConfigParser(interpolation=None, allow_no_value=True)


def parse(filepath: str) -> StudyData:
    """Load metadata from a Conf file"""
    log.info("Loading metadata from {}".format(filepath))
    parser = get_parser()
    parser.read(filepath)
    return extract(parser)


class StudyDataDatabaseHandle:
    "Manage verifying existing reference data records and creating new ones."

    def __init__(self, data: StudyData, dao: shared_schema.dao.DAO) -> None:
        self.data = data
        self.dao = dao

    @staticmethod
    def db_mismatch_fields(
        item: ty.Any, db_item: ty.Mapping, flds: ty.List[str]
    ) -> ty.List[str]:
        item_flds = [getattr(item, fld) for fld in flds]
        db_flds = [db_item[fld] for fld in flds]
        return [f for (i, d, f) in zip(item_flds, db_flds, flds) if i != d]

    def db_items_match(
        self,
        table_name: str,
        items: ty.List[ty.Any],
        match_fld: str,
        flds: ty.List[str],
    ) -> None:
        "Check that existing entities match the given items."
        tbl = getattr(self.dao, table_name)
        if tbl is None:
            raise DatabaseMismatchError(table_name, f"Invalid Table: {tbl}")
        col = getattr(tbl.c, match_fld)
        if col is None:
            raise DatabaseMismatchError(
                table_name, f"Invalid column {match_fld} on {table_name}"
            )
        for item in items:
            match_val = getattr(item, match_fld)
            existing = next(self.dao.query(tbl.select(col == match_val)), None)
            if existing is not None:
                mismatch_flds = self.db_mismatch_fields(item, existing, flds)
                if mismatch_flds:
                    msg = "Fields don't match: {}".format(
                        ", ".join(mismatch_flds)
                    )
                    raise DatabaseMismatchError(table_name, msg)

    def check_existing(self) -> None:
        """Check if the provided reference data exists, and the existing
        records match the given data."""
        self.db_items_match(
            "sourcestudy",
            [self.data.source_study],
            "name",
            ["start_year", "end_year", "notes"],
        )
        self.db_items_match(
            "reference",
            self.data.references,
            "id",
            [
                "id",
                "author",
                "title",
                "journal",
                "url",
                "publication_dt",
                "pubmed_id",
            ],
        )
        self.db_items_match(
            "collaborator", self.data.collaborators, "id", ["name"]
        )

    def create_new(self) -> None:
        with self.dao.engine.begin():
            self.dao.insert_or_check_identical(
                "sourcestudy", self.data.source_study._asdict()
            )
            source_study_name = self.data.source_study.name
            for ref in self.data.references:
                self.dao.insert_or_check_identical("reference", ref._asdict())
                self.dao.insert_or_check_identical(
                    "sourcestudyreference",
                    {
                        "sourcestudy_name": source_study_name,
                        "reference_id": ref.id,
                    },
                )
            for collaborator in self.data.collaborators:
                self.dao.insert_or_check_identical(
                    "collaborator", collaborator._asdict()
                )
                self.dao.insert_or_check_identical(
                    "sourcestudycollaborator",
                    {
                        "collaborator_id": collaborator.id,
                        "study_name": source_study_name,
                    },
                )
