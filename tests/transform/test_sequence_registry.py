import random
import string
import unittest

from shrl.transform import util


def random_seq(length=20, alphabet="gatc"):
    return "".join(random.choice(alphabet) for _ in range(length))


def random_name(length=9, alphabet=string.ascii_lowercase):
    return "".join(random.choice(alphabet) for _ in range(length))


class FakeSeqRecord:
    def __init__(self, id):
        self.id = id
        self.name = random_name()
        self.seq = random_seq()


class TestSequenceRegistry(unittest.TestCase):
    def setUp(self):
        self.seq_records = list(map(FakeSeqRecord, range(20)))
        self.registry = util.SequenceRegistry()
        self.registry.add_seqs(self.seq_records)

    def test_presence_checking(self):
        for seq in self.seq_records:
            self.assertIn(str(seq.id), self.registry)
        for fake_id in range(100, 120):
            self.assertNotIn(str(fake_id), self.registry)

    def test_retrieval(self):
        for seq in self.seq_records:
            seq_id = self.registry.id_function(seq)
            self.assertEqual(
                seq,
                self.registry.get(seq_id),
                "Retrieved seq doesn't match original",
            )


class StringIdRegistry(util.SequenceRegistry):
    @staticmethod
    def id_function(seq):
        return str(seq.id)


class TestSequenceRegistryWithCustomIdFunction(unittest.TestCase):

    reg_class = StringIdRegistry

    def setUp(self):
        self.seq_records = list(map(FakeSeqRecord, range(20)))
        self.registry = self.reg_class()
        self.registry.add_seqs(self.seq_records)

    def test_presence_checking(self):
        for seq in self.seq_records:
            new_id = self.reg_class.id_function(seq)
            self.assertIn(new_id, self.registry)
        for fake_id in map(str, range(100, 120)):
            self.assertNotIn(fake_id, self.registry)

    def test_retrieval(self):
        for seq in self.seq_records:
            self.assertNotIn(seq.id, self.registry)
            new_id = self.reg_class.id_function(seq)
            self.assertEqual(
                seq,
                self.registry.get(new_id),
                "Retrieved seq doesn't match original",
            )
