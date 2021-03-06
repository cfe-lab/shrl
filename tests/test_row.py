import io
import unittest

import shrl.exceptions
from shrl import field, row

# ---------------------------------------------------------------------
# Test Fixtures

id_field = field.NumberField(name="id", required=True)
flag_field = field.BoolField(name="flag", required=False)
notes_field = field.StringField(name="notes", required=False)
example_fields = (id_field, flag_field, notes_field)
example_rowspec = row.RowSpec(fields=example_fields)

# ---------------------------------------------------------------------
# Tests
fake_location = shrl.exceptions.SourceLocation(
    filename="fake_filename", line=0
)


def parse_loaded(loaded):
    return {nm: val._parse() for nm, val in loaded.items()}


class TestRowSpec(unittest.TestCase):
    def test_parse_success(self):
        source = {"id": "3", "flag": "true", "notes": ""}
        loaded = example_rowspec.load(source, fake_location)
        expected = {"id": 3, "flag": True, "notes": None}
        self.assertEqual(parse_loaded(loaded), expected)

    def test_parse_blank_unrequired(self):
        source = {"id": "3", "flag": "", "notes": ""}
        loaded = example_rowspec.load(source, fake_location)
        expected = {"id": 3, "flag": None, "notes": None}
        self.assertEqual(parse_loaded(loaded), expected)

    def test_parse_blank_required(self):
        source = {"id": "7f8c83ed9df2d", "flag": "", "notes": ""}
        loaded = example_rowspec.load(source, fake_location)
        self.assertRaises(shrl.field.FieldParsingError, parse_loaded, loaded)

    def test_parse_missing_required(self):
        source = {"flag": "True", "notes": ""}
        loaded = example_rowspec.load(source, fake_location)
        self.assertRaises(shrl.field.FieldParsingError, parse_loaded, loaded)

    def test_table_equality(self):
        flds = (
            field.NumberField(name="id", required=True),
            field.BoolField(name="flag", required=False),
            field.StringField(name="notes", required=False),
        )
        other_example_rowspec = row.RowSpec(fields=flds)

        self.assertEqual(example_rowspec, example_rowspec)
        self.assertNotEqual(example_rowspec, other_example_rowspec)


raw_source = """ID,COUNTRY,SEX,YEAR_OF_BIRTH,LTFU,LTFU_YEAR,DIED,COD,SEX_ORI,IDU,IDU_RECENT,NDU,NDU_RECENT,PRISON,KIND,HIV,HBV,OST,CIRR,CTP,MELD,BIL,HEMO,ALB,IL28B,SEQ_ID,SEQ_METHOD,SEQ_KIND,GENE,GENOTYPE,SUBGENOTYPE,CUTOFF,FIRST_TREATMENT,DURATION_ACT,REGIMEN,PREV_REGIMEN,RESPONSE
1,Canada,female,1971,n,,,,heterosexual,n,n,y,n,n,BL,n,y,y,y,6,40,2.57,12.2,6.1,tt,vnyvkde1,sanger,BL,NS5A,1,a,5,yes,84,HARVONI,"SOVALDI , PEGASYS",nr
1,,,,,,,,,,,,,,,,,,,,,,,,,j7yx8083,sanger,FW24,NS5A,1,a,5,,,HARVONI,,
2,Canada,male,1988,n,,,,heterosexual,n,n,n,n,n,BL,n,n,n,y,8,48,0.44,10.3,5.8,ct,hjxm0f1e,sanger,,NS3,1,a,5,no,72,"SOVALDI , PEGASYS",,svr
2,,,,,,,,,,,,,,,,,,,,,,,,,z66sbhwp,sanger,FW12,NS5B,1,a,5,,,"SOVALDI , PEGASYS",,
3,Canada,female,1967,y,2009,y,cir,homosexual,y,n,y,y,n,BL,y,y,n,n,12,13,1.73,15.7,4.7,tt,dtwcjt13,sanger,,NS3,1,b,5,yes,84,"SOVALDI , PEGASYS",,svr
4,Canada,other,1971,n,,,,heterosexual,n,n,n,n,n,BL,n,y,y,y,13,53,2.34,16.9,6.4,cc,ibofdt3h,sanger,,NS5B,1,a,5,yes,79,"SOVALDI , OLYSIO","SOVALDI , PEGASYS",svr
5,Canada,male,1989,y,2011,n,,homosexual,n,n,n,n,y,BL,y,n,n,y,8,22,2.65,14.1,7.8,ct,0zg4olpt,sanger,,NS5B,1,a,5,no,80,"SOVALDI , PEGASYS",,rl
5,,,,,,,,,,,,,,,,,,,,,,,,,8phxbqku,sanger,FW24,NS5B,1,a,5,,,"SOVALDI , PEGASYS",,"""  # noqa


def fake_source():
    source = io.StringIO(raw_source)
    source_file = shrl.io.CsvSource.from_file(source, filename="fake.csv")
    return source_file


class TestLoadRows(unittest.TestCase):
    def test_loading_source_rows(self):
        source_data = fake_source()
        loaded = list(row.load_rows(source_data))
        self.assertEqual(len(loaded), 8)
        self.assertTrue(all(type(r) is dict for r in loaded))
