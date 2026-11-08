from collections import defaultdict
from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityFlagRow, EntityRow
from aerona.db.tables.warfare import TributeRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.war import TributeStatus
from aerona.engine.primitives.knowledge import KnowledgeMap, LawBook
from aerona.engine.primitives.queries import BondIndex
from aerona.engine.primitives.stats import stat

COMMUNITY_BOND_KINDS = (
    BondKind.ENEMY,
    BondKind.TRADES_WITH,
    BondKind.PAYS_TRIBUTE,
    BondKind.RULES,
    BondKind.OWNS,
    BondKind.SPEAKS,
    BondKind.ALLY,
)


class CommunityBook:
    def __init__(
        self,
        *,
        bonds: BondIndex,
        knowledge: KnowledgeMap,
        laws: LawBook,
        flags: dict[EntityFlag, set[int]],
        tributaries: set[int],
        justice: dict[int, list[int]],
    ) -> None:
        self.bonds = bonds
        self.knowledge = knowledge
        self.laws = laws
        self._flags = flags
        self._tributaries = tributaries
        self._justice = justice

    @classmethod
    async def load(cls, session: AsyncSession, kinds: Iterable[BondKind] = COMMUNITY_BOND_KINDS) -> "CommunityBook":
        flags: dict[EntityFlag, set[int]] = defaultdict(set)
        for entity_id, flag in await session.execute(select(EntityFlagRow.entity_id, EntityFlagRow.flag)):
            flags[flag].add(entity_id)
        tributaries = set(await session.scalars(select(TributeRow.payer_entity_id).where(TributeRow.status == TributeStatus.ACTIVE)))
        justice: dict[int, list[int]] = defaultdict(list)
        laws = await session.scalars(
            select(EntityRow).where(EntityRow.entity_type == EntityType.LAW, EntityRow.status == EntityStatus.CANON, EntityRow.location_id.is_not(None))
        )
        for law in laws:
            value = stat(law, "justice")
            if law.location_id is not None and value is not None:
                justice[law.location_id].append(value)
        return cls(
            bonds=await BondIndex.load(session, kinds),
            knowledge=await KnowledgeMap.load(session),
            laws=await LawBook.load(session),
            flags=flags,
            tributaries=tributaries,
            justice=justice,
        )

    def at_war(self, entity_id: int) -> bool:
        return bool(self.bonds.touching(entity_id, BondKind.ENEMY))

    def routes(self, entity_id: int) -> int:
        return len(self.bonds.touching(entity_id, BondKind.TRADES_WITH))

    def pays_tribute(self, entity_id: int) -> bool:
        return entity_id in self._tributaries or bool(self.bonds.outgoing(entity_id, BondKind.PAYS_TRIBUTE))

    def flagged(self, entity_id: int, flag: EntityFlag) -> bool:
        return entity_id in self._flags.get(flag, set())

    def mean_justice(self, location_id: int) -> float | None:
        values = self._justice.get(location_id)
        return sum(values) / len(values) if values else None

    def justice_values(self, location_id: int) -> list[int]:
        return list(self._justice.get(location_id, []))
