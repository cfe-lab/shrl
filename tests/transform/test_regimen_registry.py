"""Test that the object for tracking, retrieving, and syncing cannonical
treatment regimens to the database while loading new records works as expected.
"""
import unittest
import uuid

import sqlalchemy.sql as sql

import shared_schema.dao as ss_dao
import shared_schema.regimens as ss_reg
from shrl.transform import util


class TestRegimenRegistry(unittest.TestCase):
    def setUp(self):
        self.registry = util.RegimenRegistry()

    def test_added_regimen_is_in_registry(self):
        fake_regimen = frozenset([1])
        self.registry.add(fake_regimen)
        self.assertIn(fake_regimen, self.registry)

    def test_added_regimen_can_have_id(self):
        fake_regimen = frozenset([1])
        fake_uid = uuid.uuid4()
        self.registry.add(fake_regimen, reg_id=fake_uid)
        retrieved_uid, retrieved_regimen = self.registry.get(fake_regimen)
        self.assertEqual(fake_regimen, retrieved_regimen)
        self.assertEqual(fake_uid, retrieved_uid)

    def test_id_can_be_retrieved(self):
        fake_regimen = frozenset([1])
        retrieved_uid = self.registry.get_or_create_id(fake_regimen)
        self.assertIsInstance(retrieved_uid, uuid.UUID)


class TestRegimenInitialization(unittest.TestCase):
    def test_initialize_from_dao(self):
        dao = ss_dao.DAO("sqlite:///:memory:")
        dao.init_db()
        reg_id = uuid.uuid4()
        reg_expr = dao.regimen.insert().values(id=reg_id, name="Test Regimen")
        dao.execute(reg_expr)
        reg_incl_expr = dao.regimendruginclusion.insert().values(
            regimen_id=reg_id,
            medication_id="BOC",
            dose=100,
            frequency="QD",
            duration=7,
        )
        dao.execute(reg_incl_expr)

        registry = util.RegimenRegistry.init_from_dao(dao)

        regimen_src = "100mg BOC QD 1 week"
        regimen_data = ss_reg.cannonical.from_string(regimen_src)
        self.assertEqual(reg_id, registry.get_or_create_id(regimen_data))


class TestRegmimenRegistrySyncing(unittest.TestCase):
    def setUp(self):
        self.registry = util.RegimenRegistry()
        self.dao = ss_dao.DAO("sqlite:///:memory:")
        self.dao.init_db()

    def test_basic_sync(self):
        reg_src = "250mg SOF QD 6 weeks"
        regimen = ss_reg.cannonical.from_string(reg_src)
        reg_id = self.registry.get_or_create_id(regimen)

        self.registry.sync_to_dao(self.dao)

        reg_record = self.dao.get_regimen(reg_id=reg_id)
        self.assertIsNotNone(reg_record)

        reg_qry = sql.select(
            [self.dao.regimen, self.dao.regimendruginclusion]
        ).where(
            self.dao.regimen.c.id == self.dao.regimendruginclusion.c.regimen_id
        )
        rows = self.dao.execute(reg_qry).fetchall()
        self.assertEqual(len(rows), 1, "Expected one drug inclusion record")
        row = next(iter(rows))
        cases = [
            (row.id, reg_id),
            (row.medication_id, "SOF"),
            (row.dose, 250),
            (row.frequency, "QD"),
            (row.duration, 42),
        ]
        for got, expected in cases:
            self.assertEqual(got, expected)
