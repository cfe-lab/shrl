"Parse and validate rows from a CSV file"

import typing as ty

import shrl.exceptions
import shrl.field

CsvRow = ty.Dict[str, str]
ParsedRow = ty.Dict[str, shrl.field.ParsedField]
# A RuleFunction will raise an exception if the row is somehow invalid.
RuleFunction = ty.Callable[[ParsedRow, shrl.exceptions.SourceLocation], None]


class RowSpec(object):
    "Specifies the fields in a row, and any row-level validation rules"

    fields: ty.List[shrl.field.BaseField]
    rules: ty.List[RuleFunction]

    def __init__(
            self,
            fields: ty.List[shrl.field.BaseField],
            rules: ty.List[RuleFunction],
    ) -> None:
        assert len(set(fld.name for fld in fields)) == len(fields)
        self.fields = fields
        self._fields_index = {fld.name: fld for fld in fields}
        self.rules = rules

    def parse(
            self,
            src_dict: CsvRow,
            loc: shrl.exceptions.SourceLocation,
    ) -> ty.Dict[str, shrl.field.ParsedField]:
        "Given a dict of column name to source string, parse it into a row"

        result = {}
        for fld in self.fields:
            colname = fld.name
            src = src_dict.get(colname)
            parsed = fld.parse(src, loc)
            result[colname] = parsed
        for fn in self.rules:
            fn(result, loc)
        return result
