import unittest

import shrl.exceptions
from shrl import field

fake_loc = shrl.exceptions.SourceLocation(filename="fake_file.csv", line=0)


class BaseFieldTest(unittest.TestCase):
    def setUp(self):
        super(BaseFieldTest, self).setUp()
        self.fld = self.fld_class(name="test field", required=True)


class TestBoolField(BaseFieldTest):

    fld_class = field.BoolField

    def test_parse_true(self):
        true_cases = ["True", "true", "TRUE", "1", "y", "t", "yes"]
        for case in true_cases:
            parsed = self.fld.parse(case, fake_loc)
            self.assertTrue(
                parsed, "Expected '{}' to be parsed as 'True'".format(case)
            )

    def test_parse_false(self):
        false_cases = ["0", "false", "False", "FALSE", "n", "f", "no"]
        for case in false_cases:
            parsed = self.fld.parse(case, fake_loc)
            self.assertFalse(
                parsed, "Expected '{}' to be parsed as 'False'".format(case)
            )

    def test_parse_none(self):
        none_cases = ["none", "null"]
        for case in none_cases:
            parsed = self.fld.parse(case, fake_loc)
            self.assertIsNone(
                parsed, "Expected '{}' to be parsed as 'None'".format(case)
            )

    def test_parse_err(self):
        err_cases = ["asdf", "2", "tru ue", None]
        for case in err_cases:
            msg = "Expected '{}' to not parse as Boolean".format(case)
            with self.assertRaises(field.FieldParsingError, msg=msg):
                self.fld.parse(case, fake_loc)


class TestDateField(BaseFieldTest):

    fld_class = field.DateField

    def test_parse_success(self):
        ok_cases = ["2016-01-01", "2019-3-12", "1918-2-09"]
        for case in ok_cases:
            self.fld.parse(case, fake_loc)

    def test_parse_error(self):
        value_err_cases = ["", "boop", "10-1-3", "1911-12-b"]
        for case in value_err_cases:
            msg = "Expected '{}' not to parse as date".format(case)
            with self.assertRaises(field.FieldParsingError, msg=msg):
                self.fld.parse(case, fake_loc)


class TestNumberField(BaseFieldTest):

    fld_class = field.NumberField

    def test_parse_success(self):
        ok_cases = ["1", "-2", "3.14", "-2.2", "1.3e12"]
        for case in ok_cases:
            parsed = self.fld.parse(case, None)
            matches = type(parsed) is int or type(parsed) is float
            msg = "Expected '{}' to parse as a number".format(case)
            self.assertTrue(matches, msg)

    def test_parse_error(self):
        err_cases = ["a", "1.b", "2e1.2", ""]
        for case in err_cases:
            msg = "Expected '{}' to not parse as a number".format(case)
            with self.assertRaises(field.FieldParsingError, msg=msg):
                self.fld.parse(case, fake_loc)


class TestStringField(BaseFieldTest):

    fld_class = field.StringField

    def test_parse_success(self):
        ok_cases = ["asdf", "jkl", "semicolon"]
        for case in ok_cases:
            parsed = self.fld.parse(case, loc=None)
            self.assertEqual(parsed, case)

    def test_parse_no_blanks(self):
        fld = field.StringField(name="unrequired")
        self.assertEqual(fld.parse("", loc=None), None)


class TestEnumField(BaseFieldTest):
    def setUp(self):
        # override because EnumFields have additional constructor options
        pass

    def test_parse_success(self):
        options = ("a", "b", "c")
        fld = field.EnumField(
            name="test field", required=True, options=options
        )
        ok_cases = ["a", "B", " C", " A "]
        for case in ok_cases:
            fld.parse(case, fake_loc)

    def test_parse_failured(self):
        options = ("a", "b", "c")
        fld = field.EnumField(
            name="test field", required=True, options=options
        )
        fail_cases = ["d", 3, None, [], {1: 2}, {1, 2, 3}]
        for case in fail_cases:
            msg = "Expected '{}' to not parse as enum".format(case)
            with self.assertRaises(field.FieldParsingError, msg=msg):
                fld.parse(case, fake_loc)


class TestFieldEquality(unittest.TestCase):
    def test_equal_fields_are_equal(self):
        fld1 = field.NumberField(name="fld", required=True)
        fld2 = field.NumberField(name="fld", required=True)
        self.assertFalse(fld1 is fld2)
        self.assertEqual(fld1, fld2)
        self.assertFalse(fld1 != fld2)

    def test_inequal_field_aren_not_equal(self):
        fld1 = field.NumberField(name="fld", required=True)
        fld2 = field.NumberField(name="other fld", required=True)
        self.assertNotEqual(fld1, fld2)


class TestForeignKeyField(unittest.TestCase):
    def test_equal_fields_are_equal(self):
        fld1 = field.ForeignKeyField(
            name="a", required=True, target="a_target"
        )
        fld2 = field.ForeignKeyField(
            name="a", required=True, target="a_target"
        )
        self.assertEqual(fld1, fld2)

    def test_nonequal_fields_are_not_equal(self):
        fld1 = field.ForeignKeyField(
            name="a", required=True, target="a_target"
        )
        fld2 = field.ForeignKeyField(
            name="b", required=True, target="b_target"
        )
        self.assertNotEqual(fld1, fld2)


class TestLoadedField(unittest.TestCase):
    def test_parse(self):
        fld = shrl.field.LoadedField(
            src="1.0",
            fld=shrl.field.NumberField("test_field", required=True),
            loc=fake_loc,
        )
        self.assertEqual(fld._parse(), 1.0)

    def test_parse_invalid(self):
        fld = shrl.field.LoadedField(
            src="Kangaroo",
            fld=shrl.field.NumberField("test_field", required=True),
            loc=fake_loc,
        )
        self.assertRaises(shrl.field.FieldParsingError, fld._parse)

    def test_parse_or(self):
        fld = shrl.field.LoadedField(
            src="Kangaroo",
            fld=shrl.field.NumberField("test_field", required=True),
            loc=fake_loc,
        )
        self.assertEqual(fld._parse_or(0.0), 0.0)
