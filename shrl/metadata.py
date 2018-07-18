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


def get_parser() -> configparser.ConfigParser:
    return configparser.ConfigParser(interpolation=None, allow_no_value=True)

