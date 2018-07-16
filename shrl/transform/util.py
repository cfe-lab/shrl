import logging
import typing as ty
import uuid

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
