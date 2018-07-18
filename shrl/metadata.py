import configparser
import typing as ty
import uuid

import shrl.exceptions


class MetadataError(shrl.exceptions.ShrlException):
    "Indicates a fatal problem in the study metadata"

    def __init__(self, section: str, detail: str) -> None:
        self.section = section
        self.detail = detail

    def __str__(self) -> str:
        tmpl = "Metadata error ({section}): {detail}"
        return tmpl.format(section=self.section, detail=self.detail)


class Collaborator(ty.NamedTuple):
    id: uuid.UUID
    name: str


class SourceStudy(ty.NamedTuple):

    name: str
    start_year: int
    end_year: int
    notes: ty.Optional[str]


class Reference(ty.NamedTuple):
    id: uuid.UUID
    author: str
    title: str
    journal: ty.Optional[str]
    url: ty.Optional[str]  # TODO(nknight): make this a urllib ParseResult?
    publication_dt: str
    pubmed_id: ty.Optional[str]


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
        reference = Reference(
            id=ref_id,
            author=raw_args["author"],
            title=raw_args["title"],
            journal=raw_args.get("journal"),
            url=raw_args.get("url"),
            publication_dt=raw_args["publication_dt"],
            pubmed_id=raw_args.get("pubmed_id"),
        )
        result.append(reference)
    return result


def get_parser() -> configparser.ConfigParser:
    return configparser.ConfigParser(interpolation=None, allow_no_value=True)

