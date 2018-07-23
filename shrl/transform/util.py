import logging
import typing as ty
import uuid

import Bio.SeqIO as seqio
import Bio.SeqRecord as seqrecord
import sqlalchemy.sql as sql

import shared_schema.dao as dao
import shared_schema.regimens as ss_regimens

log = logging.getLogger(__name__)


class RegimenRegistry(object):
    def __init__(self) -> None:
        self._storage: ty.Dict[
            int, ty.Tuple[uuid.UUID, ss_regimens.Regimen]
        ] = dict()

    def __contains__(self, regimen: ss_regimens.Regimen) -> bool:
        return hash(regimen) in self._storage

    def add(
        self,
        regimen: ss_regimens.Regimen,
        reg_id: ty.Optional[uuid.UUID] = None,
    ) -> ty.Tuple[uuid.UUID, ss_regimens.Regimen]:
        reg_hash = hash(regimen)
        if reg_id is None:
            reg_id = uuid.uuid4()
        self._storage[reg_hash] = (reg_id, regimen)
        return reg_id, regimen

    def get(
        self, regimen: ss_regimens
    ) -> ty.Tuple[uuid.UUID, ss_regimens.Regimen]:
        return self._storage[hash(regimen)]

    def values(self) -> ty.Iterable[ty.Tuple[uuid.UUID, ss_regimens.Regimen]]:
        return self._storage.values()

    @classmethod
    def init_from_dao(cls, dao: dao.DAO) -> "RegimenRegistry":
        log.info("Loading regimens from DAO")
        registry = cls()
        reg_qry = dao.regimen.select()
        regs = dao.execute(reg_qry).fetchall()
        for reg in regs:
            uid = reg.id
            regimen = ss_regimens.cannonical.from_dao(dao, uid)
            registry.add(regimen, reg_id=uid)
        return registry

    def get_or_create_id(self, regimen: ss_regimens.Regimen) -> uuid.UUID:
        """Finds or creates a regimen in the registry"""
        if regimen in self:
            reg_id, _ = self.get(regimen)
            return reg_id
        else:
            reg_id, _ = self.add(regimen)
            return reg_id

    def sync_to_dao(self, dao: dao.DAO) -> None:
        """Save new regimens to the DAO

        Given a shared_schema.dao.DAO, check that each regimen in the
        registry exists in the database. If it doesn't, create it.
        """
        log.info("Syncing regimens to the database")
        for reg_id, regimen in self.values():
            db_regimen = dao.get_regimen(reg_id=reg_id)
            if db_regimen is None:
                log.info("Creating new regimen: {reg}".format(reg=regimen))
                create_stm = dao.regimen.insert().values(id=reg_id, name=None)
                dao.execute(create_stm)
                incl_values = list(
                    {"regimen_id": reg_id, **incl._asdict()}
                    for incl in ss_regimens.cannonical.drug_inclusions(regimen)
                )
                incl_keys = incl_values[0].keys()
                incl_stm = dao.regimendruginclusion.insert().values(
                    **{nm: sql.bindparam(nm) for nm in incl_keys}
                )
                dao.execute(incl_stm, incl_values)


T = ty.TypeVar("T", bound="SequenceRegistry")


class SequenceRegistry(object):

    SEQ_FILE_FORMAT = "fasta"

    def __init__(self) -> None:
        """Manages access to genetic sequences

        Takes an iterable of biopython SeqRecords, extracts an ID from
        each one, and stores them for random access.
        """
        self._seq_store: ty.Dict[str, seqrecord.SeqRecord] = dict()
        self._hash_store: ty.Set[int] = set()

    def __contains__(self, seq_id: str) -> bool:
        return seq_id in self._seq_store

    def get(self, seq_id: str) -> seqrecord.SeqRecord:
        if seq_id not in self:
            msg = "Missing sequence with id '{}'".format(seq_id)
            raise KeyError(msg)
        else:
            return self._seq_store[seq_id]

    @staticmethod
    def id_function(seq: seqrecord.SeqRecord) -> str:
        """Get a sequence's ID from its BioPython sequence object

        When loading sequences from FASTA files, this function is
        applied to each sequence. It should return a unique ID.

        The base SequenceManager uses the sequence's ID unchanged;
        subclasses may use other conventions (e.g. to pull a field out
        of a character-delimited list in the title).
        """
        return str(seq.id)

    @staticmethod
    def hash_key(bio_seq: seqrecord.SeqRecord) -> ty.Tuple[str, str]:
        """Returns a tuple of the fields on an input fasta sequence object
        that should be considered for the sequence's hash
        value. Default is name and sequence."""
        name: str = bio_seq.name
        seq: str = str(bio_seq.seq)
        return (name, seq)

    @classmethod
    def sequence_hash(cls, seq: seqrecord.SeqRecord) -> int:
        key = cls.hash_key(seq)
        return hash(key)

    def check_in_sequence(self, sequence: seqrecord.SeqRecord) -> None:
        """Get a sequence's hash value and add it to the repository's hash
        store, checking that we're not adding duplicates"""
        hash_value = self.sequence_hash(sequence)
        if hash_value in self._hash_store:
            msg = "Duplicate sequence: name='{}'".format(sequence.name)
            raise ValueError(msg)
        self._hash_store.add(hash_value)

    def add_seqs(self, sequences: ty.Iterable[seqrecord.SeqRecord]) -> None:
        "Add a sequence of BioPython seq objects"
        for seq in sequences:
            self.check_in_sequence(seq)
            seq_id = self.id_function(seq)
            self._seq_store[seq_id] = seq

    def add_file(self, filename: str) -> None:
        seqs = self.file_seqs(filename)
        self.add_seqs(seqs)

    @classmethod
    def file_seqs(
        cls: ty.Type[T], filename: str
    ) -> ty.Iterable[seqrecord.SeqRecord]:
        "Load sequences from a file"
        with open(filename) as inf:
            seqs = list(seqio.parse(inf, cls.SEQ_FILE_FORMAT))
        return seqs

    @classmethod
    def from_seqs(
        cls: ty.Type[T], seqs: ty.Iterable[seqrecord.SeqRecord]
    ) -> T:
        repository = cls()
        repository.add_seqs(seqs)
        return repository

    @classmethod
    def from_files(cls: ty.Type[T], filenames: ty.Iterable[str]) -> T:
        repository = cls()
        for filename in filenames:
            repository.add_file(filename)
        return repository
