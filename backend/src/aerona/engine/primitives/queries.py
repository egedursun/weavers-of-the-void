from collections import defaultdict, deque
from collections.abc import Iterable, Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.engine import LOCATION_CHAIN_MAX_HOPS, SUBTREE_STEP_LIMIT
from aerona.db.bond_index import bond_lookup
from aerona.db.read_memo import memoized
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.repositories.nodes import NodeRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityFlagRow, EntityRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.node import NodeKind
from aerona.domain.enums.son import SonStatus

ACTIVE_ONLY = (BondState.ACTIVE,)


async def canon(session: AsyncSession, types: Iterable[EntityType] | None = None, world_id: int | None = None) -> list[EntityRow]:
    statement = select(EntityRow).where(EntityRow.status == EntityStatus.CANON)
    wanted = list(types) if types is not None else None
    if wanted is not None:
        statement = statement.where(EntityRow.entity_type.in_(wanted))
    if world_id is not None:
        statement = statement.where(EntityRow.world_id == world_id)
    return list(await session.scalars(statement.order_by(EntityRow.id)))


async def entity(session: AsyncSession, entity_id: int | None) -> EntityRow | None:
    if entity_id is None:
        return None
    return await session.get(EntityRow, entity_id)


async def living_entity(session: AsyncSession, entity_id: int | None) -> EntityRow | None:
    found = await entity(session, entity_id)
    return found if found is not None and found.status is EntityStatus.CANON else None


async def count_canon(session: AsyncSession, entity_type: EntityType | None = None) -> int:
    statement = select(func.count()).select_from(EntityRow).where(EntityRow.status == EntityStatus.CANON)
    if entity_type is not None:
        statement = statement.where(EntityRow.entity_type == entity_type)
    return int(await session.scalar(statement) or 0)


async def count_communities(session: AsyncSession, world_id: int | None = None) -> int:
    statement = select(func.count()).select_from(EntityRow).where(EntityRow.status == EntityStatus.CANON, EntityRow.entity_type.in_(list(COMMUNITY_TYPES)))
    if world_id is not None:
        statement = statement.where(EntityRow.world_id == world_id)
    return int(await session.scalar(statement) or 0)


async def flags_by_entity(session: AsyncSession, flag: EntityFlag) -> set[int]:
    return set(await session.scalars(select(EntityFlagRow.entity_id).where(EntityFlagRow.flag == flag)))


async def has_flag(session: AsyncSession, entity_id: int, flag: EntityFlag) -> bool:
    return await EntityRepository(session).has_flag(entity_id, flag)


async def add_flag(session: AsyncSession, entity_id: int, flag: EntityFlag, epoch: int) -> bool:
    return await EntityRepository(session).add_flag(entity_id, flag, epoch)


async def remove_flag(session: AsyncSession, entity_id: int, flag: EntityFlag) -> bool:
    return await EntityRepository(session).remove_flag(entity_id, flag)


async def active_bonds(
    session: AsyncSession,
    kinds: Iterable[BondKind],
    sources: Sequence[int] | None = None,
    targets: Sequence[int] | None = None,
) -> list[BondRow]:
    wanted = tuple(kinds)
    lookup = await bond_lookup(session)
    if lookup is not None:
        return lookup.select(wanted, ACTIVE_ONLY, sources, targets)
    statement = select(BondRow).where(BondRow.state == BondState.ACTIVE, BondRow.kind.in_(list(wanted)))
    if sources is not None:
        statement = statement.where(BondRow.source_node_id.in_(list(sources)))
    if targets is not None:
        statement = statement.where(BondRow.target_node_id.in_(list(targets)))
    return list(await session.scalars(statement.order_by(BondRow.id)))


async def connect(session: AsyncSession, source: int, target: int, kind: BondKind, epoch: int, *, description: str | None = None) -> BondRow | None:
    if source == target:
        return None
    return await BondRepository(session).connect(BondDraft(source, target, kind, epoch, description))


async def bond_exists(session: AsyncSession, first: int, second: int, kind: BondKind) -> bool:
    return await BondRepository(session).exists_between(first, second, kind)


async def directed_bond(session: AsyncSession, source: int, target: int, kind: BondKind) -> BondRow | None:
    statement = select(BondRow).where(
        BondRow.source_node_id == source, BondRow.target_node_id == target, BondRow.kind == kind, BondRow.state == BondState.ACTIVE
    )
    found: BondRow | None = await session.scalar(statement.order_by(BondRow.id).limit(1))
    return found


async def close(session: AsyncSession, bond: BondRow, epoch: int, reason: str | None = None) -> None:
    await BondRepository(session).deactivate(bond, epoch, reason)


class BondIndex:
    def __init__(self, bonds: Iterable[BondRow]) -> None:
        self.bonds = list(bonds)
        self._outgoing: dict[tuple[int, BondKind], list[BondRow]] = defaultdict(list)
        self._incoming: dict[tuple[int, BondKind], list[BondRow]] = defaultdict(list)
        for bond in self.bonds:
            self._outgoing[(bond.source_node_id, bond.kind)].append(bond)
            self._incoming[(bond.target_node_id, bond.kind)].append(bond)

    @classmethod
    async def load(cls, session: AsyncSession, kinds: Iterable[BondKind]) -> "BondIndex":
        return cls(await active_bonds(session, kinds))

    def outgoing(self, node_id: int, kind: BondKind) -> list[BondRow]:
        return [bond for bond in self._outgoing.get((node_id, kind), ()) if bond.state is BondState.ACTIVE]

    def incoming(self, node_id: int, kind: BondKind) -> list[BondRow]:
        return [bond for bond in self._incoming.get((node_id, kind), ()) if bond.state is BondState.ACTIVE]

    def touching(self, node_id: int, kind: BondKind) -> list[BondRow]:
        return self.outgoing(node_id, kind) + self.incoming(node_id, kind)

    def between(self, first: int, second: int, kind: BondKind) -> bool:
        return any(bond.target_node_id == second for bond in self.outgoing(first, kind)) or any(
            bond.target_node_id == first for bond in self.outgoing(second, kind)
        )

    def add(self, bond: BondRow | None) -> None:
        if bond is None or bond in self.bonds:
            return
        self.bonds.append(bond)
        self._outgoing[(bond.source_node_id, bond.kind)].append(bond)
        self._incoming[(bond.target_node_id, bond.kind)].append(bond)


@memoized(BondRow, EntityRow)
async def spoken_language(session: AsyncSession, speaker_id: int) -> EntityRow | None:
    statement = (
        select(EntityRow)
        .join(BondRow, BondRow.target_node_id == EntityRow.id)
        .where(
            BondRow.source_node_id == speaker_id,
            BondRow.kind == BondKind.SPEAKS,
            BondRow.state == BondState.ACTIVE,
            EntityRow.entity_type == EntityType.LANGUAGE,
            EntityRow.status.in_([EntityStatus.CANON, EntityStatus.DEAD]),
        )
        .order_by(BondRow.id.desc())
        .limit(1)
    )
    found: EntityRow | None = await session.scalar(statement)
    return found


async def son(session: AsyncSession, son_id: int | None) -> SonRow | None:
    if son_id is None:
        return None
    return await session.get(SonRow, son_id)


async def living_son(session: AsyncSession, son_id: int | None) -> SonRow | None:
    found = await son(session, son_id)
    return found if found is not None and found.status is not SonStatus.DEAD else None


async def living_sons(session: AsyncSession) -> list[SonRow]:
    return list(await session.scalars(select(SonRow).where(SonRow.status != SonStatus.DEAD).order_by(SonRow.id)))


async def node_kind(session: AsyncSession, node_id: int) -> NodeKind | None:
    return await NodeRepository(session).kind_of(node_id)


async def descendants(session: AsyncSession, ancestor_id: int, types: Iterable[EntityType]) -> list[EntityRow]:
    statement = (
        select(EntityRow)
        .join(BondRow, BondRow.source_node_id == EntityRow.id)
        .where(
            BondRow.target_node_id == ancestor_id,
            BondRow.kind == BondKind.DESCENDS_FROM,
            BondRow.state == BondState.ACTIVE,
            EntityRow.status == EntityStatus.CANON,
            EntityRow.entity_type.in_(list(types)),
        )
        .order_by(BondRow.id.desc())
    )
    return list((await session.scalars(statement)).unique())


async def subtree(session: AsyncSession, root_id: int, statuses: tuple[EntityStatus, ...] = (EntityStatus.CANON,)) -> list[EntityRow]:
    collected: list[EntityRow] = []
    queue = deque([root_id])
    seen = {root_id}
    while queue and len(collected) < SUBTREE_STEP_LIMIT:
        current = queue.popleft()
        statement = select(EntityRow).where(EntityRow.location_id == current, EntityRow.status.in_(list(statuses))).order_by(EntityRow.id)
        for child in await session.scalars(statement):
            if child.id in seen:
                continue
            seen.add(child.id)
            collected.append(child)
            queue.append(child.id)
    return collected


async def top_region(session: AsyncSession, entity: EntityRow | None) -> EntityRow | None:
    current = entity
    found: EntityRow | None = None
    seen: set[int] = set()
    while current is not None and current.id not in seen and len(seen) <= LOCATION_CHAIN_MAX_HOPS:
        seen.add(current.id)
        if current.entity_type is EntityType.REGION:
            found = current
        current = await session.get(EntityRow, current.location_id) if current.location_id is not None else None
    return found
