import unittest

import hypothesis
import hypothesis.strategies as st

import shrl.case
import shrl.exceptions
import shrl.field
import shrl.row

from . import test_row

key_field = "key field"
example_fields = [key_field, "superfluous field", "extra field"]


@st.composite
def location_strat(draw):
    filename_id = draw(st.text(min_size=1, max_size=8))
    filename = f"generated_filename_{filename_id}"
    line = draw(st.integers(min_value=1, max_value=1000))
    return shrl.exceptions.SourceLocation(filename=filename, line=line)


@st.composite
def field_strat(draw, field_name):
    src = str(draw(st.integers(min_value=0, max_value=1000)))
    loc = draw(location_strat())
    field = shrl.field.NumberField(name=field_name, required=True)
    return shrl.field.LoadedField(src=src, fld=field, loc=loc)


@st.composite
def loaded_row_strat(draw):
    return {fld: draw(field_strat(fld)) for fld in example_fields}


start_row = {
    key_field:
    shrl.field.LoadedField(
        src="3",
        fld=shrl.field.NumberField(name=key_field, required=True),
        loc=location_strat().example(),
    )
}


@st.composite
def loaded_rows_strat(draw):
    rest = draw(st.lists(loaded_row_strat(), min_size=1))
    return [start_row] + rest


def pred(row: shrl.row.LoadedRow) -> bool:
    fld = row[key_field]
    value = fld._parse()
    return value % 3 == 0


class TestSplitRows(unittest.TestCase):
    def test_empty(self):
        expected = ([], [])
        self.assertEqual(shrl.case.split_rows(lambda x: True, []), expected)

    def test_single(self):
        expected = ([1], [])
        self.assertEqual(shrl.case.split_rows(lambda x: True, [1]), expected)

    @hypothesis.given(loaded_rows_strat())
    def test_returned_items_satisfy_predicate(self, items):
        items = items
        taken, rest = shrl.case.split_rows(pred, items)
        assert all(pred(i) for i in taken)

    @hypothesis.given(loaded_rows_strat())
    def test_rest_items_dont_match_predicate(self, items):
        items = items
        taken, rest = shrl.case.split_rows(pred, items)
        assert len(rest) == 0 or not pred(rest[0])

    @hypothesis.given(loaded_rows_strat())
    def test_no_items_are_lost(self, items):
        items = items
        taken, rest = shrl.case.split_rows(pred, items)
        assert len(taken) + len(rest) == len(items)

    @hypothesis.given(loaded_rows_strat())
    def test_random_application(self, items):
        _, _ = shrl.case.split_rows(pred, items)


class TestGroupRows(unittest.TestCase):
    def test_one(self):
        rows = [start_row]
        grouped = shrl.case.group_rows(key_field=key_field, rows=rows)
        self.assertEqual(grouped, [rows])

    @hypothesis.given(loaded_rows_strat())
    def test_no_fields_left_out(self, items):
        grouped = shrl.case.group_rows(key_field=key_field, rows=items)
        assert len(items) == sum(len(g) for g in grouped)

    @hypothesis.given(loaded_rows_strat())
    def test_no_empty_groups(self, items):
        grouped = shrl.case.group_rows(key_field=key_field, rows=items)
        assert all(len(g) > 0 for g in grouped)

    @hypothesis.given(loaded_rows_strat())
    def test_groups_have_same_pred_values(self, items):
        grouped = shrl.case.group_rows(key_field=key_field, rows=items)

        def make_pred(first_row):
            key_val = first_row[key_field]._parse()
            assert key_val is not None

            def pred(row):
                return row[key_field]._parse_or(key_val) == key_val

            return pred

        for group in grouped:
            pred = make_pred(group[0])
            assert all(pred(g) for g in group)


class TestGetNamedField(unittest.TestCase):
    @hypothesis.given(loaded_row_strat(), st.sampled_from(example_fields))
    def test_basic_application(self, row, fieldname):
        named_fields = shrl.case.get_named_fields([fieldname], row)
        assert fieldname in named_fields

    @hypothesis.given(loaded_row_strat())
    def test_all_and_only_requested_fields_are_retrieved(self, row):

        combos = [
            ("key field", ),
            ("key field", "extra field"),
            ("extra field", ),
            ("extra field", "superfluous field"),
        ]

        def verify_combo(fieldnames):
            named_fields = shrl.case.get_named_fields(fieldnames, row)
            assert set(named_fields.keys()) == set(fieldnames)

        for combo in combos:
            verify_combo(combo)


class TestCaseRows(unittest.TestCase):
    def test_basics(self):
        source_data = test_row.fake_source()
        parsed = list(shrl.row.load_rows(source_data))
        cases = list(shrl.case.cases(parsed))
        self.assertEqual(len(cases), 5)
        example_case = cases[0]
        self.assertEqual(len(example_case.clinical), 1)
        self.assertEqual(len(example_case.clinical[0].sequences), 2)
