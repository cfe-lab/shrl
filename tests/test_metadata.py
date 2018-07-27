import configparser
import datetime
import textwrap
import unittest
import uuid

from shrl import metadata


def parse_config_str(src):
    parser = metadata.get_parser()
    parser.read_string(src)
    return parser


class TestParseCollaborator(unittest.TestCase):
    def test_load_collaborator(self):
        src = textwrap.dedent(
            """\
            [collaborator]
            id=af8e1177-a043-4d10-963d-5eb76af13566
            name=asdf
            """
        )
        parsed = parse_config_str(src)
        extracted = metadata.collaborators(parsed)
        expected_collab = metadata.Collaborator(
            id=uuid.UUID("af8e1177-a043-4d10-963d-5eb76af13566"), name="asdf"
        )
        self.assertEqual(extracted, [expected_collab])

    def test_load_multiple_collaborators(self):
        src = textwrap.dedent(
            """\
            [collaborator.1]
            id=af8e1177-a043-4d10-963d-5eb76af13566
            name=asdf

            [collaborator.2]
            id=af8e1177-a043-4d10-963d-5eb76af13567
            name = jkl
            """
        )
        parsed = parse_config_str(src)
        extracted = metadata.collaborators(parsed)
        expected = [
            metadata.Collaborator(
                id=uuid.UUID("af8e1177-a043-4d10-963d-5eb76af13566"),
                name="asdf",
            ),
            metadata.Collaborator(
                id=uuid.UUID("af8e1177-a043-4d10-963d-5eb76af13567"),
                name="jkl",
            ),
        ]
        self.assertEqual(extracted, expected)

    def test_missing_collaborator_raises_error(self):
        src = ""
        parsed = parse_config_str(src)
        with self.assertRaises(metadata.MetadataError):
            metadata.collaborators(parsed)


class TestParseSourceStudy(unittest.TestCase):
    def test_source_study(self):
        src = textwrap.dedent(
            """\
            [collaborator]
            id=fb1cd0e9-e181-4902-82bf-ee314ebe0227
            name=asdf

            [sourcestudy]
            name=jkl
            start_year = 1988
            end_year = 1996
            notes =
              This was a study.
            """
        )
        parsed = parse_config_str(src)
        source_study = metadata.source_study(parsed)
        expected = metadata.SourceStudy(
            name="jkl",
            start_year=1988,
            end_year=1996,
            notes="This was a study.",
        )
        self.assertEqual(source_study, expected)

    def test_duplicate_source_studies_raises_error(self):
        src = textwrap.dedent(
            """\
            [collaborator]
            id=fb1cd0e9-e181-4902-82bf-ee314ebe0227
            name=asdf

            [sourcestudy]
            name=jkl
            start_year = 1988
            end_year = 1996
            notes =
            This was a study.

            [sourcestudy]
            name=asdf
            start_year = 2002
            end_year = 2008
            notes =
            This was a different study.
            """
        )
        with self.assertRaises(configparser.DuplicateSectionError):
            parse_config_str(src)


class TestParseReferences(unittest.TestCase):
    def test_references(self):
        src = textwrap.dedent(
            """\
            [collaborator]
            id=fb1cd0e9-e181-4902-82bf-ee314ebe0227
            name=asdf

            [reference.1]
            author=A
            title=B
            journal=C
            publication_dt=2016-01-01
            pubmed_id=0

            [reference.2]
            author=X
            title=Y
            journal=Z
            url=https://journalclub.website/X/Y/Z
            publication_dt=1996-10-24
            """
        )
        parsed = parse_config_str(src)
        extracted = metadata.references(parsed)
        expected_fields = [
            {
                "author": "A",
                "title": "B",
                "journal": "C",
                "publication_dt": datetime.date(2016, 1, 1),
                "pubmed_id": "0",
            },
            {
                "author": "X",
                "title": "Y",
                "journal": "Z",
                "url": "https://journalclub.website/X/Y/Z",
                "publication_dt": datetime.date(1996, 10, 24),
            },
        ]
        self.assertEqual(
            len(expected_fields),
            len(extracted),
            "Expected two references to be parsed",
        )
        for entity, expected_flds in zip(extracted, expected_fields):
            for name, val in expected_flds.items():
                self.assertEqual(getattr(entity, name), val)
            self.assertIsInstance(entity.id, uuid.UUID)
