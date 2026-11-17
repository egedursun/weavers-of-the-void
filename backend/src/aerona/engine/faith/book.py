from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.read_memo import memoized
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import CultDoctrineRow, CultTenetRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus, EntityType
from aerona.domain.enums.faith import TenetKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.primitives.faith import FaithIndex
from aerona.engine.recording.record import FactInput


@dataclass(frozen=True)
class FaithLine:
    key: str
    roles: Mapping[IncidentRole, int | tuple[int, ...]]
    facts: Mapping[str, FactInput] = field(default_factory=dict)

    @property
    def ids(self) -> tuple[int, ...]:
        return tuple(node for value in self.roles.values() for node in (value if isinstance(value, tuple) else (value,)))


@dataclass
class Church:
    cult: EntityRow
    doctrine: CultDoctrineRow | None
    tenets: dict[TenetKind, CultTenetRow] = field(default_factory=dict)
    god: SonRow | None = None
    members: list[EntityRow] = field(default_factory=list)

    def holds(self, tenet: TenetKind) -> bool:
        return tenet in self.tenets


@dataclass
class FaithBook:
    faith: FaithIndex
    churches: dict[int, Church]
    by_god: dict[int, list[Church]]
    communities: dict[int, EntityRow]

    @classmethod
    async def load(cls, session: AsyncSession) -> "FaithBook":
        faith = await FaithIndex.load(session)
        cults = list(
            await session.scalars(
                select(EntityRow).where(EntityRow.entity_type == EntityType.CULT, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
            )
        )
        doctrines = {row.cult_entity_id: row for row in await session.scalars(select(CultDoctrineRow))}
        tenets: dict[int, dict[TenetKind, CultTenetRow]] = defaultdict(dict)
        for row in await session.scalars(select(CultTenetRow)):
            tenets[row.cult_entity_id][row.tenet] = row
        communities = {
            row.id: row
            for row in await session.scalars(
                select(EntityRow).where(EntityRow.entity_type.in_(list(COMMUNITY_TYPES)), EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
            )
        }
        churches: dict[int, Church] = {}
        by_god: dict[int, list[Church]] = defaultdict(list)
        for cult in cults:
            god = faith.living_patron_son(cult.id)
            church = Church(cult, doctrines.get(cult.id), tenets.get(cult.id, {}), god)
            churches[cult.id] = church
            if god is not None:
                by_god[god.id].append(church)
        for community in communities.values():
            god_id = faith.patron(community.id)
            for church in by_god.get(god_id or -1, []):
                if church.cult.world_id == community.world_id:
                    church.members.append(community)
        return cls(faith, churches, by_god, communities)

    def church_of(self, community_id: int) -> Church | None:
        god_id = self.faith.patron(community_id)
        churches = self.by_god.get(god_id or -1, [])
        if not churches:
            return None
        community = self.communities.get(community_id)
        local = [church for church in churches if community is None or church.cult.world_id == community.world_id] or churches
        return max(local, key=lambda church: (len(church.members), -church.cult.id))

    def holds(self, community_id: int, tenet: TenetKind) -> bool:
        church = self.church_of(community_id)
        return church is not None and church.holds(tenet)


@memoized(BondRow)
async def patron_node(session: AsyncSession, entity_id: int) -> int | None:
    statement = select(BondRow.target_node_id).where(BondRow.source_node_id == entity_id, BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE)
    return await session.scalar(statement.order_by(BondRow.id).limit(1))


async def faith_tenets(session: AsyncSession, community_id: int) -> set[TenetKind]:
    god_id = await patron_node(session, community_id)
    if god_id is None:
        return set()
    worshippers = select(BondRow.source_node_id).where(BondRow.target_node_id == god_id, BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE)
    cults = select(EntityRow.id).where(EntityRow.id.in_(worshippers), EntityRow.entity_type == EntityType.CULT, EntityRow.status == EntityStatus.CANON)
    return set(await session.scalars(select(CultTenetRow.tenet).where(CultTenetRow.cult_entity_id.in_(cults))))


@memoized(BondRow, CultTenetRow)
async def dietary_gods(session: AsyncSession) -> frozenset[int]:
    cults = select(CultTenetRow.cult_entity_id).where(CultTenetRow.tenet == TenetKind.DIETARY_LAW, CultTenetRow.target.is_not(None), CultTenetRow.target != "")
    statement = select(BondRow.target_node_id).where(BondRow.source_node_id.in_(cults), BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE)
    return frozenset(await session.scalars(statement.distinct()))


async def forbidden_foods(session: AsyncSession, community_id: int) -> set[str]:
    god_id = await patron_node(session, community_id)
    if god_id is None or god_id not in await dietary_gods(session):
        return set()
    worshippers = select(BondRow.source_node_id).where(BondRow.target_node_id == god_id, BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE)
    rows = await session.scalars(select(CultTenetRow.target).where(CultTenetRow.cult_entity_id.in_(worshippers), CultTenetRow.tenet == TenetKind.DIETARY_LAW))
    return {row for row in rows if row}
