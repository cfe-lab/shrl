"Parse and validate rows from a CSV file"

import typing as ty

import shared_schema.datatypes as datatypes
import shared_schema.submission_scheme.simple as scheme
import shared_schema.util
import shrl.exceptions
import shrl.field
import shrl.io

LoadedRow = ty.Dict[str, shrl.field.LoadedField]
# A RuleFunction will raise an exception if the row is somehow invalid.
RuleFunction = ty.Callable[[LoadedRow, shrl.exceptions.SourceLocation], None]


class InvalidColumns(shrl.exceptions.BaseParsingException):
    pass


class RowSpec:
    "Specifies the fields in a row, and any row-level validation rules"

    fields: ty.List[shrl.field.BaseField]

    def __init__(
            self,
            fields: ty.List[shrl.field.BaseField],
    ) -> None:
        assert len(set(fld.name for fld in fields)) == len(fields)
        self.fields = fields
        self._fields_index = {fld.name: fld for fld in fields}
        self._field_set = set(f.name for f in fields)

    def load(
            self,
            src: shrl.io.CsvRow,
            loc: shrl.exceptions.SourceLocation,
    ) -> LoadedRow:
        "Given a dict of column name to source string, parse it into a row"

        result = {}
        if not set(src.keys()).issubset(self._field_set):
            extra_cols = set(src.keys()) - self._field_set
            msg = "Unexpected columns: {}".format(", ".join(extra_cols))
            raise InvalidColumns(loc, msg)
        for fld in self.fields:
            colname = fld.name
            fld_src = src.get(colname, "")
            loaded = fld.load(fld_src, loc)
            result[colname] = loaded
        return result


_SIMPLE_TYPE_MAP: ty.Dict[ty.Any, ty.Type[shrl.field.BaseField]] = {
    datatypes.Datatype.INTEGER: shrl.field.NumberField,
    datatypes.Datatype.FLOAT: shrl.field.NumberField,
    datatypes.Datatype.STRING: shrl.field.StringField,
    datatypes.Datatype.DATE: shrl.field.DateField,
    datatypes.Datatype.UUID: shrl.field.StringField,
    datatypes.Datatype.BOOL: shrl.field.BoolField,
}

_SPECIAL_TYPE_MAP: ty.Dict[ty.Any, ty.Type[shrl.field.BaseField]] = {
    datatypes.Datatype.ENUM: shrl.field.EnumField,
    datatypes.Datatype.FOREIGN_KEY: shrl.field.ForeignKeyField,
}


class SchemaDefinitionError(shrl.exceptions.ShrlException):
    pass


def _schema_field_as_field(scm_field: scheme.Field) -> shrl.field.BaseField:
    '''Convert submission scheme fields to shrl fields.

     This function constructs a  a shrl.field.Field from a
     shared_schema.submission_scheme.field.Field'''
    scm_type = scm_field.type

    shrl_type = _SIMPLE_TYPE_MAP.get(scm_type)
    if shrl_type is not None:
        return shrl_type(name=scm_field.name, required=scm_field.required)
    shrl_type = _SPECIAL_TYPE_MAP.get(scm_type)
    if shrl_type is not None:
        if shrl_type is shrl.field.EnumField:
            options = shared_schema.util.enum_members(scm_field.schema_type)
            return shrl.field.EnumField(
                name=scm_field.name,
                required=scm_field.required,
                options=[opt.lower() for opt in options],
            )
        if shrl_type is shrl.field.ForeignKeyField:
            target = shared_schema.util.foreign_key_target(
                scm_field.schema_type)
            return shrl.field.ForeignKeyField(
                name=scm_field.name,
                required=scm_field.required,
                target=target,
            )
    # If we haven't returned by now, we don't know how to parse this type.
    raise SchemaDefinitionError(f"Can't convert schema field: {scm_field}")


submission_spec = RowSpec(
    fields=[_schema_field_as_field(f) for f in scheme.fields], )


def load_rows(source: shrl.io.CsvSource) -> ty.Iterable[LoadedRow]:
    for idx, row in enumerate(source.reader):
        location = shrl.exceptions.SourceLocation(
            filename=str(source.filename),
            line=idx + 2,  # +1 for 0 indexing, +1 for headers
        )
        yield submission_spec.load(row, location)
