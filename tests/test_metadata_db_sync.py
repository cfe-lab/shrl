import unittest
import uuid

import shared_schema.dao
from shrl import metadata


class TestConsistencyWithExistingEntities(unittest.TestCase):
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


class TestCreatingNewEntities(unittest.TestCase):
    def setUp(self):
        self.dao = shared_schema.dao.DAO("sqlite:///:memory:")
        self.dao.init_db()

    @unittest.skip("TODO")
    def test_adding_new_entities(self):
        pass


class TestSyncingToDatabase(unittest.TestCase):
    @unittest.skip("TODO")
    def test_syncing_to_clean_database(self):
        pass

    @unittest.skip("TODO")
    def test_syncing_to_database_with_existing_data(self):
        pass
