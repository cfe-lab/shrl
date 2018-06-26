import textwrap
import typing as ty


class SourceLocation(ty.NamedTuple):
    filename: str
    line: int

    def __str__(self) -> str:
        return f"{self.filename}:{self.line}"


class ShrlException(Exception):
    '''Root exception for anything specific to parsing and validating data'''
    pass


class BaseParsingException(ShrlException):
    "Indicates that an error has arisen while parsing source data"
    location: SourceLocation
    msg: str

    def __init__(self, location: SourceLocation, msg: str = "") -> None:
        self.location = location
        self.msg = msg

    def __str__(self) -> str:
        title = self.__class__.__name__
        header = f"{title} at {self.location}"
        body = textwrap.indent(textwrap.fill(self.msg), "  ")
        return "{header}\n{body}".format(header=header, body=body)
