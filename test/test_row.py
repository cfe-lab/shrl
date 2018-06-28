import unittest

import shrl.exceptions
from shrl import field, row

# ---------------------------------------------------------------------
# Test Fixtures

id_field = field.NumberField(name='id', required=True)
flag_field = field.BoolField(name='flag', required=False)
notes_field = field.StringField(name='notes', required=False)
example_fields = (id_field, flag_field, notes_field)
example_rowspec = row.RowSpec(
    fields=example_fields,
    rules=[],
)

# ---------------------------------------------------------------------
# Tests
fake_location = shrl.exceptions.SourceLocation(
    filename="fake_filename",
    line=0,
)


class TestRowSpec(unittest.TestCase):
    def test_parse_success(self):
        source = {'id': '3', 'flag': 'true', 'notes': ''}
        parsed = example_rowspec.parse(source, fake_location)
        expected = {'id': 3, 'flag': True, 'notes': None}
        self.assertEqual(parsed, expected)

    def test_parse_blank_unrequired(self):
        source = {'id': '3', 'flag': '', 'notes': ''}
        parsed = example_rowspec.parse(source, fake_location)
        expected = {'id': 3, 'flag': None, 'notes': None}
        self.assertEqual(parsed, expected)

    def test_parse_blank_required(self):
        source = {'id': '7f8c83ed9df2d', 'flag': '', 'notes': ''}
        self.assertRaises(
            shrl.field.FieldParsingError,
            example_rowspec.parse,
            source,
            fake_location,
        )

    def test_parse_missing_required(self):
        source = {'flag': 'True', 'notes': ''}
        self.assertRaises(
            shrl.field.FieldParsingError,
            example_rowspec.parse,
            source,
            fake_location,
        )

    def test_table_equality(self):
        flds = (
            field.NumberField(name='id', required=True),
            field.BoolField(name='flag', required=False),
            field.StringField(name='notes', required=False),
        )
        other_example_rowspec = row.RowSpec(fields=flds, rules=tuple())

        self.assertEqual(example_rowspec, example_rowspec)
        self.assertNotEqual(example_rowspec, other_example_rowspec)
