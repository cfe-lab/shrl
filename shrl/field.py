"""Parse and validate individual fields from a CSV file

This module contains an abstract base class which holds common behavior for
defining fields and a concrete class for each type of value that we parse
(strings, enums, numbers, etc.).
"""

import datetime
import enum
import typing as ty

import shrl.exceptions


class FieldDefinitionError(shrl.exceptions.ShrlException):
    pass


class FieldParsingError(shrl.exceptions.BaseParsingException):
    pass


T = ty.TypeVar("T")

FieldType = ty.Union[str, bool, int, float, enum.Enum, datetime.date]


class LoadedField(ty.NamedTuple):
    src: str
    fld: "BaseField"
    loc: shrl.exceptions.SourceLocation

    def _parse(self) -> ty.Optional[FieldType]:
        return self.fld.parse(self.src, self.loc)

    def _parse_or(self, default: ty.Optional[FieldType]) -> ty.Optional[FieldType]:
        try:
            return self._parse()
        except FieldParsingError:
            return default


class BaseField:
    "Abstract base class for field parsers"

    def __init__(self, name: str, required: bool = False) -> None:
        self.name = name
        self.required = required

    def handle_none(
        self, loc: shrl.exceptions.SourceLocation
    ) -> ty.Optional[FieldType]:
        "What to do with an empty field"
        if not self.required:
            return None
        else:
            msg = f"Missing required field: {self.name}"
            raise FieldParsingError(location=loc, msg=msg)

    def parse(
        self, src: ty.Optional[str], loc: shrl.exceptions.SourceLocation
    ) -> ty.Optional[FieldType]:
        if src is None:
            return self.handle_none(loc)
        try:
            return self.parse_type(src, loc)
        except FieldParsingError as err:
            # If the field looks blank, treat it as None.
            if type(src) is str and src.strip() == "":
                return self.handle_none(loc)
            else:
                raise err

    def load(self, src: str, loc: shrl.exceptions.SourceLocation) -> LoadedField:
        return LoadedField(src=src, fld=self, loc=loc)

    def parse_type(
        self, src: str, loc: shrl.exceptions.SourceLocation
    ) -> ty.Optional[FieldType]:
        "Implemented by concrete field parsers that handle specific types"
        raise NotImplementedError()

    def __str__(self) -> str:
        tmpl = "<{} {}>"
        return tmpl.format(self.__class__.__name__, self.name)

    def __eq__(self, other: ty.Any) -> bool:
        if type(self) is not type(other):
            return False
        else:
            return all([self.name == other.name, self.required == other.required])


class BoolField(BaseField):

    trues = frozenset(["1", "true", "y", "t", "yes"])
    falses = frozenset(["0", "false", "n", "f", "no"])
    nones = frozenset(["none", "null", ""])

    def parse_type(
        self, src: str, loc: shrl.exceptions.SourceLocation
    ) -> ty.Optional[bool]:
        try:
            normed_src = src.lower().strip()
            if normed_src in self.falses:
                return False
            elif normed_src in self.trues:
                return True
            elif normed_src in self.nones:
                return None
            else:
                msg = "Expected one of 'true', 'false', '0', or '1'; got '{}'"
                raise FieldParsingError(loc, msg.format(src))
        except Exception as e:
            msg = "Unexpected exception while parsing {}: {}"
            raise FieldParsingError(loc, msg.format(self.name, e))


class DateField(BaseField):
    def parse_type(
        self, src: str, loc: shrl.exceptions.SourceLocation
    ) -> datetime.date:
        try:
            dt = datetime.datetime.strptime(src, "%Y-%m-%d")
            return dt.date()
        except ValueError as v:
            msg = "Expected a date in the format YYYY-MM-DD; got '{}' instead"
            raise FieldParsingError(loc, msg.format(v))
        except Exception as e:
            msg = "Unexpected exception while parsing date: {}"
            raise FieldParsingError(loc, msg.format(e))


class NumberField(BaseField):
    def parse_type(
        self, src: str, loc: shrl.exceptions.SourceLocation
    ) -> ty.Union[int, float]:
        # First, try to convert the input to a number
        try:
            return int(src)
        except Exception:
            pass
        try:
            return float(src)
        except Exception:
            pass
        raise FieldParsingError(loc, f"Unexpected error parsing numeric field: '{src}'")


class StringField(BaseField):
    def handle_blank(self, loc: shrl.exceptions.SourceLocation) -> ty.Optional[str]:
        if self.required:
            raise FieldParsingError(loc, "Unexpected blank field")
        else:
            return None

    def parse_type(
        self, src: str, loc: shrl.exceptions.SourceLocation
    ) -> ty.Optional[str]:
        try:
            parsed = src.strip()
            if parsed == "":
                return self.handle_blank(loc)
            else:
                return parsed
        except Exception as e:
            msg = "Unepected exception while parsing {}: {}"
            raise FieldParsingError(loc, msg.format(self.name, e))


class EnumField(BaseField):

    target: enum.Enum

    def __init__(
        self, name: str, options: ty.Iterable[str], required: bool = False
    ) -> None:
        super(EnumField, self).__init__(name=name, required=required)
        if options is None:
            msg = "EnumFields required a list of options"
            raise FieldDefinitionError(msg)
        self.target = enum.Enum(name, options)

    # This function returns an enum that's constructed at runtime. I'm not sure
    # how to represent that with `typing`.
    def parse_type(self, src: str, loc: shrl.exceptions.SourceLocation) -> enum.Enum:
        # NOTE(nknight): typing doesn't support iterating enums yet.
        try:
            normed_src = src.lower().strip()
            # NOTE(nknight): typing doesn't support indexing enums yet
            return self.target[normed_src]  # type: ignore
        except KeyError:
            opts = ", ".join([e.name for e in self.target])  # type: ignore
            msg = f"Unexpected value {src} for enum {self.name} ({opts})"
            raise FieldParsingError(loc, f"Unexpected value '{src}' for {self.name}")
        except Exception as e:
            tmpl = "Unexpected exception trying to parse '{}' as {}"
            msg = tmpl.format(src, self.name)
            raise FieldParsingError(location=loc, msg=msg)


class ForeignKeyField(StringField):
    """Like a string field, but gets more checking at the Schema level"""

    def __init__(self, name: str, target: str, required: bool = True) -> None:
        super(ForeignKeyField, self).__init__(name, required)
        if target is None:
            msg = "ForeignKeyField missing a target: {}"
            raise FieldDefinitionError(msg.format(name))
        else:
            self.target = target
