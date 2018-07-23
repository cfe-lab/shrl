import unittest
import uuid

import sqlalchemy.sql as sql

import shared_schema.dao
from shrl import metadata

EX_REFERENCE = metadata.Reference(
    id=uuid.uuid4(),
    author="Prior Worker",
    title="Dr. Prior Work",
    journal="Prestigious Journal",
    pubmed_id=str(uuid.uuid4()),
    publication_dt=None,
    url=None,
)
EX_SOURCESTUDY = metadata.SourceStudy(
    name="Prior Source Study",
    start_year=2000,
    end_year=2002,
    notes="Notes on the study.",
)
EX_COLLABORATOR = metadata.Collaborator(
    id=uuid.uuid4(), name="Just Prior Worker to their friends"
)
EX_STUDYDATA = metadata.StudyData(
    source_study=EX_SOURCESTUDY,
    collaborators=[EX_COLLABORATOR],
    references=[EX_REFERENCE],
)


class TestConsistencyWithExistingEntities(unittest.TestCase):
    def setUp(self):
        self.dao = shared_schema.dao.DAO("sqlite:///:memory:")
        self.dao.init_db()
        self.dao.insert("reference", EX_REFERENCE._asdict())
        self.dao.insert("sourcestudy", EX_SOURCESTUDY._asdict())
        self.dao.insert("collaborator", EX_COLLABORATOR._asdict())

    def test_matching_sourcedata_validates(self):
        handle = metadata.StudyDataDatabaseHandle(EX_STUDYDATA, self.dao)
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
            changed_sourcestudy = EX_STUDYDATA._replace(
                source_study=EX_SOURCESTUDY._replace(start_year=0)
            )
            metadata.StudyDataDatabaseHandle(
                changed_sourcestudy, self.dao
            ).check_existing()
        with self.assertRaises(metadata.DatabaseMismatchError):
            changed_reference = EX_STUDYDATA._replace(
                references=[
                    EX_REFERENCE._replace(
                        author="Updated Author", title="New Title"
                    )
                ]
            )
            metadata.StudyDataDatabaseHandle(
                changed_reference, self.dao
            ).check_existing()
        with self.assertRaises(metadata.DatabaseMismatchError):
            changed_collaborator = EX_STUDYDATA._replace(
                collaborators=[
                    EX_COLLABORATOR._replace(name="Updated Collaborator Name")
                ]
            )
            metadata.StudyDataDatabaseHandle(
                changed_collaborator, self.dao
            ).check_existing()


class TestCreatingNewEntities(unittest.TestCase):
    def setUp(self):
        self.dao = shared_schema.dao.DAO("sqlite:///:memory:")
        self.dao.init_db()

    def assert_created_and_flds_equal(self, item, table, match_pred, flds):
        retrieved = self.dao.execute(
            table.select().where(match_pred)
        ).fetchone()
        self.assertIsNotNone(retrieved, "Missing value from database")
        for fld in flds:
            self.assertEqual(getattr(item, fld), retrieved[fld])

    def test_adding_new_entities_one_at_a_time(self):
        "A StudyData with one new entity of each kind syncs correctly"
        hndl = metadata.StudyDataDatabaseHandle(EX_STUDYDATA, self.dao)
        hndl.check_existing()
        hndl.create_new()

        self.assert_created_and_flds_equal(
            EX_REFERENCE,
            self.dao.reference,
            self.dao.reference.c.id == EX_REFERENCE.id,
            [
                "author",
                "title",
                "journal",
                "pubmed_id",
                "publication_dt",
                "url",
            ],
        )
        self.assert_created_and_flds_equal(
            EX_COLLABORATOR,
            self.dao.collaborator,
            self.dao.collaborator.c.id == EX_COLLABORATOR.id,
            ["id", "name"],
        )
        self.assert_created_and_flds_equal(
            EX_SOURCESTUDY,
            self.dao.sourcestudy,
            self.dao.sourcestudy.c.name == EX_SOURCESTUDY.name,
            ["name", "start_year", "end_year", "notes"],
        )

    def test_associations_are_created(self):
        "Many-to-many associations are created when syncing"
        hndl = metadata.StudyDataDatabaseHandle(EX_STUDYDATA, self.dao)

        hndl.check_existing()
        hndl.create_new()

        def assert_item_created(tbl_name, **properties):
            tbl = getattr(self.dao, tbl_name)
            preds = [
                tbl.columns[fld] == val for fld, val in properties.items()
            ]
            pred = sql.and_(*preds)
            query = tbl.select().where(pred)
            result = self.dao.execute(query).fetchone()
            prop_msgs = (f"{key}={val}" for key, val in properties.items())
            self.assertIsNotNone(
                result,
                f"Expected a '{tbl_name}'' where {', '.join(prop_msgs)}",
            )

        assert_item_created(
            "sourcestudyreference",
            sourcestudy_id=EX_SOURCESTUDY.name,
            reference_id=EX_REFERENCE.id,
        )
        assert_item_created(
            "sourcestudycollaborator",
            study_name=EX_SOURCESTUDY.name,
            collaborator_id=EX_COLLABORATOR.id,
        )

    def test_adding_multiple_entities_at_a_time(self):
        "A StudyData with multiple new entities is correctly synced"
        new_collaborator = metadata.Collaborator(
            id=uuid.uuid4(), name="An additional Collaborator"
        )
        new_collaborators = [new_collaborator, EX_COLLABORATOR]
        new_study_data = EX_STUDYDATA._replace(collaborators=new_collaborators)
        hndl = metadata.StudyDataDatabaseHandle(new_study_data, self.dao)
        hndl.check_existing()
        hndl.create_new()

        for collab in new_collaborators:
            self.assert_created_and_flds_equal(
                collab,
                self.dao.collaborator,
                self.dao.collaborator.c.id == collab.id,
                ["name", "id"],
            )


class TestSyncingToDatabase(unittest.TestCase):
    def setUp(self):
        self.dao = shared_schema.dao.DAO("sqlite:///:memory:")
        self.dao.init_db()

    def assert_created_and_flds_equal(self, item, table, match_pred):
        flds = item._fields
        retrieved = self.dao.execute(
            table.select().where(match_pred)
        ).fetchone()
        self.assertIsNotNone(retrieved, "Missing value from database")
        for fld in flds:
            self.assertEqual(getattr(item, fld), retrieved[fld])

    def test_syncing_to_clean_database(self):
        hndl = metadata.StudyDataDatabaseHandle(EX_STUDYDATA, self.dao)
        hndl.check_existing()
        hndl.create_new()
        self.assert_created_and_flds_equal(
            EX_COLLABORATOR,
            self.dao.collaborator,
            self.dao.collaborator.c.id == EX_COLLABORATOR.id,
        )
        self.assert_created_and_flds_equal(
            EX_SOURCESTUDY,
            self.dao.sourcestudy,
            self.dao.sourcestudy.c.name == EX_SOURCESTUDY.name,
        )
        self.assert_created_and_flds_equal(
            EX_REFERENCE,
            self.dao.reference,
            self.dao.reference.c.id == EX_REFERENCE.id,
        )

    def test_syncing_to_database_with_existing_data(self):
        # Collaborator already exists in database
        self.dao.insert("collaborator", EX_COLLABORATOR._asdict())
        self.assert_created_and_flds_equal(
            EX_COLLABORATOR,
            self.dao.collaborator,
            self.dao.collaborator.c.id == EX_COLLABORATOR.id,
        )
        # When syncing, no error is thrown.
        hndl = metadata.StudyDataDatabaseHandle(EX_STUDYDATA, self.dao)
        hndl.check_existing()
        hndl.create_new()
        self.assert_created_and_flds_equal(
            EX_COLLABORATOR,
            self.dao.collaborator,
            self.dao.collaborator.c.id == EX_COLLABORATOR.id,
        )
        self.assert_created_and_flds_equal(
            EX_SOURCESTUDY,
            self.dao.sourcestudy,
            self.dao.sourcestudy.c.name == EX_SOURCESTUDY.name,
        )
        self.assert_created_and_flds_equal(
            EX_REFERENCE,
            self.dao.reference,
            self.dao.reference.c.id == EX_REFERENCE.id,
        )

    def test_syncing_to_database_with_conflicting_data(self):
        # Collaborator already exists in database, with different name
        altered_collaborator = EX_COLLABORATOR._replace(name="Different Name")
        self.dao.insert("collaborator", altered_collaborator._asdict())
        self.assert_created_and_flds_equal(
            altered_collaborator,
            self.dao.collaborator,
            self.dao.collaborator.c.id == EX_COLLABORATOR.id,
        )
        with self.assertRaises(metadata.DatabaseMismatchError):
            hndl = metadata.StudyDataDatabaseHandle(EX_STUDYDATA, self.dao)
            hndl.check_existing()
            hndl.create_new()
