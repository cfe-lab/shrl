"""Functions for grouping and parsing sequences of raw CSV records into
participant cases (which include participant info, clinical tests, treatment
history, and one or more sequences).
"""
import typing as ty

import shrl.exceptions
import shrl.field
import shrl.io
import shrl.row

# Raw input data
LoadedRows = ty.List[shrl.row.LoadedRow]

# This type is an intermediate parsing step
ParsedRow = ty.Dict[str, ty.Optional[shrl.field.FieldType]]

# This type should be ready to insert into the database.
Values = ty.Dict[str, ty.Optional[shrl.field.FieldType]]


class Clinical(ty.NamedTuple):
    values: Values
    sequences: ty.List[Values]


class Case(ty.NamedTuple):
    participant: Values
    behavior: Values
    clinical: ty.List[Clinical]


class ParsingError(shrl.exceptions.BaseParsingException):
    pass


# ------------------------------------------------------------------
# Utils

T = ty.TypeVar("T")


def split_rows(
    pred: ty.Callable[[shrl.row.LoadedRow], bool], rows: LoadedRows
) -> ty.Tuple[LoadedRows, LoadedRows]:
    if len(rows) == 0:
        return ([], [])
    if not pred(rows[0]):
        loc = next(f.loc for f in rows[0].values())
        msg = "Tried to split rows but predicate was invalid on first row"
        raise ParsingError(location=loc, msg=msg)
    if len(rows) == 1:
        return (rows, [])
    else:
        idx = 0
        while True:
            if idx == len(rows):
                break
            if not pred(rows[idx]):
                break
            idx += 1
        return (rows[:idx], rows[idx:])


def group_rows(key_field: str, rows: LoadedRows) -> ty.List[LoadedRows]:
    result: ty.List[LoadedRows] = []
    rest = rows

    while True:
        fld_val = rest[0][key_field]._parse()

        def pred(row: shrl.row.LoadedRow) -> bool:
            return row[key_field]._parse_or(fld_val) == fld_val

        chunk, rest = split_rows(pred, rest)
        result.append(chunk)
        if len(rest) == 0:
            break

    return result


def get_named_fields(
    field_names: ty.Iterable[str], source: shrl.row.LoadedRow
) -> ParsedRow:
    result: ParsedRow = {}
    for field_name in field_names:
        loaded_fld = source[field_name]
        result[field_name] = loaded_fld._parse()
    return result


# ------------------------------------------------------------------
# Parsing Fields


def parse_participant(row: shrl.row.LoadedRow) -> Values:
    fields = (
        "id",
        "country",
        "sex",
        "ethnicity",
        "year_of_birth",
        "ltfu",
        "ltfu_year",
        "died",
        "cod",
    )
    values = {}
    values["id"] = row["id"]._parse()
    values.update(get_named_fields(fields, row))
    return values


def parse_behavior(row: shrl.row.LoadedRow) -> Values:
    fields = ("sex_ori", "idu", "idu_recent", "ndu", "ndu_recent", "prison")
    return get_named_fields(fields, row)


def parse_clinical(row: shrl.row.LoadedRow) -> Values:
    fields = (
        "kind",
        "hiv",
        "hbv",
        "ost",
        "cirr",
        "fibrosis",
        "inflamation",
        "metavir_by",
        "stiff",
        "alt",
        "ast",
        "crt",
        "egfr",
        "ctp",
        "meld",
        "ishak",
        "bil",
        "hemo",
        "alb",
        "inr",
        "phos",
        "urea",
        "plate",
        "CD4",
        "crp",
        "il28b",
        "asc",
        "var_bleed",
        "hep_car",
        "transpl",
        "vl",
        "first_treatment",
        "duration_act",
        "regimen",
        "prev_regimen",
        "pprev_regimen",
        "response",
        "treatment_notes",
    )
    return get_named_fields(fields, row)


def parse_sequence(row: shrl.row.LoadedRow) -> Values:
    fields = (
        "seq_kind",
        "genotype",
        "subgenotype",
        "strain",
        "seq_id",
        "gene",
        "seq_method",
        "cutoff",
        "seq_notes",
    )
    return get_named_fields(fields, row)


def parse_case(case_rows: LoadedRows) -> Case:
    "Transform one case's worth of rows into a Case object."
    case_id = case_rows[0]["id"]._parse()

    if case_id is None:
        msg = "Unexpected null case id"
        loc = next(f.loc for f in case_rows[0].values())
        raise ParsingError(location=loc, msg=msg)
    for row in case_rows:
        cid = row["id"]._parse_or(case_id)
        if cid != case_id:
            loc = next(f.loc for f in row.values())
            msg = f"Inconsistent case id: {cid}"
            raise ParsingError(location=loc, msg=msg)

    participant = parse_participant(case_rows[0])
    behavior = parse_behavior(case_rows[0])
    clinical: ty.List[Clinical] = []
    for clinical_rows in group_rows("kind", case_rows):
        values = parse_clinical(clinical_rows[0])
        sequences = [parse_sequence(r) for r in clinical_rows]
        clinical.append(Clinical(values=values, sequences=sequences))

    return Case(participant=participant, behavior=behavior, clinical=clinical)


# ------------------------------------------------------------------
# Iterating through a strucutred CSV file


def case_rows(rows: LoadedRows) -> ty.Tuple[LoadedRows, LoadedRows]:
    "Pop one case's worth of rows from a list of loaded rows."
    case_id = rows[0]["id"]._parse()
    if case_id is None:
        location = next(f.loc for f in rows[0].values())
        raise ParsingError(location=location, msg="Missing Case ID")

    def matches_case(row: shrl.row.LoadedRow) -> bool:
        try:
            row_id = row["id"]._parse()
        except shrl.exceptions.BaseParsingException:
            row_id = None
        return row_id == case_id or row_id is None

    return split_rows(matches_case, rows)


def get_one_case(rows: LoadedRows) -> ty.Tuple[ty.Optional[Case], LoadedRows]:
    "Pop and parse one case from a list of loaded rows."
    if len(rows) == 0:
        return None, []
    else:
        cr, rest = case_rows(rows)
        return parse_case(cr), rest


# ------------------------------------------------------------------
# Synthesis


def cases(rows: LoadedRows) -> ty.Iterable[Case]:
    "Separate and parse rows into data for individual cases"
    while True:
        case, rows = get_one_case(rows)
        if case is None:
            if len(rows) > 0:
                location = next(fld.loc for fld in rows[0].values())
                raise ParsingError(
                    location=location, msg="Leftover rows while parsing cases"
                )
            return
        else:
            yield case
