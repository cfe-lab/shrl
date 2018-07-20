import configparser
import textwrap
import unittest
import uuid

import shared_schema.dao
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
                "publication_dt": "2016-01-01",
                "pubmed_id": "0",
            },
            {
                "author": "X",
                "title": "Y",
                "journal": "Z",
                "url": "https://journalclub.website/X/Y/Z",
                "publication_dt": "1996-10-24",
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


class TestFindingExistingOrSimilarReferences(unittest.TestCase):
    def setUp(self):
        self.dao = shared_schema.dao.DAO("sqlite:///:memory:")
        self.dao.init_db()
        self.existing_reference = metadata.Reference(
            id=uuid.uuid4(),
            author="Prior Worker",
            title="Dr. Prior Work",
            journal="Prestigious Journal",
            pubmed_id=str(uuid.uuid4()),
            publication_dt=None,
            url=None,
        )
        self.dao.insert("reference", self.existing_reference._asdict())
        self.existing_sourcestudy = metadata.SourceStudy(
            name="Prior Source Study",
            start_year=2000,
            end_year=2002,
            notes="Notes on the study.",
        )
        self.dao.insert("sourcestudy", self.existing_sourcestudy._asdict())
        self.existing_collaborator = metadata.Collaborator(
            id=uuid.uuid4(), name="Just Prior Worker to their friends"
        )
        self.dao.insert("collaborator", self.existing_collaborator._asdict())
        self.existing_study_data = metadata.StudyData(
            source_study=self.existing_sourcestudy,
            collaborators=[self.existing_collaborator],
            references=[self.existing_reference],
        )

    def test_matching_sourcedata_validates(self):
        handle = metadata.StudyDataDatabaseHandle(
            self.existing_study_data, self.dao
        )
        handle.check_existing()

    def test_nonexistant_sourcedata_validates(self):
        study_data = metadata.StudyData(
            source_study=metadata.SourceStudy(
                name="New Study", start_year=2022, end_year=None, notes=None
            ),
            collaborators=[
                metadata.Collaborator(id=uuid.uuid4(), name="New Collaborator")
            ],
            references=[
                metadata.Reference(
                    id=uuid.uuid4(),
                    author="New Author",
                    title="New Reference",
                    journal="New Journal",
                    url=None,
                    publication_dt="2022-08-11",
                    pubmed_id=None,
                )
            ],
        )
        handle = metadata.StudyDataDatabaseHandle(study_data, self.dao)
        handle.check_existing()

    def test_mismatching_sourcedata_does_not_validate(self):
        with self.assertRaises(metadata.DatabaseMismatchError):
            changed_sourcestudy = self.existing_study_data._replace(
                source_study=self.existing_sourcestudy._replace(start_year=0)
            )
            metadata.StudyDataDatabaseHandle(
                changed_sourcestudy, self.dao
            ).check_existing()
        with self.assertRaises(metadata.DatabaseMismatchError):
            changed_reference = self.existing_study_data._replace(
                references=[
                    self.existing_reference._replace(
                        author="Updated Author", title="New Title"
                    )
                ]
            )
            metadata.StudyDataDatabaseHandle(
                changed_reference, self.dao
            ).check_existing()
        with self.assertRaises(metadata.DatabaseMismatchError):
            changed_collaborator = self.existing_study_data._replace(
                collaborators=[
                    self.existing_collaborator._replace(
                        name="Updated Collaborator Name"
                    )
                ]
            )
            metadata.StudyDataDatabaseHandle(
                changed_collaborator, self.dao
            ).check_existing()
