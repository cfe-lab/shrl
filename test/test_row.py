import io
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


raw_source = '''ID,COUNTRY,SEX,YEAR_OF_BIRTH,LTFU,LTFU_YEAR,DIED,COD,SEX_ORI,IDU,IDU_RECENT,NDU,NDU_RECENT,PRISON,HIV,HBV,OST,CHIR,CTP,MELD,BIL,HEMO,ALB,IL28B,BL_SEQ_FILE,BL_GENOTYP,BL_SUBGENOTYPE,BL_CUTOFF,FIRST_TREATMENT,DURATION_SCH,DURATION_ACT,REGIMEN,PREV_REGIMEN,RESPONSE,NOTES
0,Canada,female,1971,n,,,,heterosexual,n,n,y,n,n,n,y,y,y,6,40,2.57,12.2,6.1,tc,baseline_1.fasta,1,a,5,yes,84,84,HARVONI,SOVALDI & PEGASYS,nr,
1,Canada,male,1988,n,,,,heterosexual,n,n,n,n,n,n,n,n,y,8,48,0.44,10.3,5.8,tc,baseline_2.fasta,1,a,5,no,84,72,SOVALDI & PEGASYS,,svr,
2,Canada,female,1967,y,2009,y,cir,homosexual,y,n,y,y,n,y,y,n,n,12,13,1.73,15.7,4.7,tt,baseline_3.fasta,1,b,5,yes,84,84,SOVALDI & PEGASYS,,svr,
3,Canada,other,1971,n,,,,heterosexual,n,n,n,n,n,n,y,y,y,13,53,2.34,16.9,6.4,cc,baseline_4.fasta,1,a,5,yes,84,79,SOVALDI & OLYSIO,SOVALDI & PEGASYS,svr,
4,Canada,male,1989,y,2011,n,,homosexual,n,n,n,n,y,y,n,n,y,8,22,2.65,14.1,7.8,tc,baseline_5.fasta,1,a,5,no,84,80,SOVALDI & PEGASYS,,rl,'''  # noqa


class TestParseRows(unittest.TestCase):
    def test_parsing_source_rows(self):
        source = io.StringIO(raw_source)
        open_source = shrl.io.CsvSource.from_file(source, filename="fake.csv")
        parsed = list(row.parse_rows(open_source))
        self.assertEqual(len(parsed), 5)
        self.assertTrue(all(type(r) is dict for r in parsed))
