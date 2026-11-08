from collections.abc import Iterable

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.bonds import BondRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.cosmos import CosmosRow, CreatorRow
from aerona.db.tables.entities import EntityFlagRow, EntityRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.son import SonStatus

THINKING_TYPES = frozenset(COMMUNITY_TYPES | {EntityType.MORTAL})


async def cosmos_row(session: AsyncSession) -> CosmosRow | None:
    row: CosmosRow | None = await session.scalar(select(CosmosRow))
    return row


async def creator_row(session: AsyncSession) -> CreatorRow | None:
    row: CreatorRow | None = await session.scalar(select(CreatorRow))
    return row


async def canon_count(session: AsyncSession, types: Iterable[EntityType] | None = None) -> int:
    statement = select(func.count(EntityRow.id)).where(EntityRow.status == EntityStatus.CANON)
    if types is not None:
        statement = statement.where(EntityRow.entity_type.in_(list(types)))
    return int(await session.scalar(statement) or 0)


async def flagged_ids(session: AsyncSession, flag: EntityFlag) -> set[int]:
    return set(await session.scalars(select(EntityFlagRow.entity_id).where(EntityFlagRow.flag == flag)))


async def sons(session: AsyncSession, statuses: Iterable[SonStatus] | None = None) -> list[SonRow]:
    statement = select(SonRow)
    if statuses is not None:
        statement = statement.where(SonRow.status.in_(list(statuses)))
    return list(await session.scalars(statement.order_by(SonRow.id)))


async def active_sons(session: AsyncSession) -> list[SonRow]:
    return await sons(session, [SonStatus.ACTIVE])


async def world_count(session: AsyncSession) -> int:
    return int(await session.scalar(select(func.count(WorldRow.id))) or 0)


async def worship_targets(session: AsyncSession, entity_id: int) -> list[int]:
    statement = select(BondRow.target_node_id).where(BondRow.source_node_id == entity_id, BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE)
    return list(await session.scalars(statement.order_by(BondRow.id)))


async def worshippers_of(session: AsyncSession, god_node_id: int, active_only: bool = True) -> list[EntityRow]:
    bonds = await BondRepository(session).incoming(god_node_id, BondKind.WORSHIPS, active_only)
    ids = list(dict.fromkeys(bond.source_node_id for bond in bonds))
    if not ids:
        return []
    statement = select(EntityRow).where(EntityRow.id.in_(ids), EntityRow.status == EntityStatus.CANON)
    found = {entity.id: entity for entity in await session.scalars(statement)}
    return [found[entity_id] for entity_id in ids if entity_id in found]


async def place_of(session: AsyncSession, entity: EntityRow) -> EntityRow | None:
    if entity.entity_type in (EntityType.REGION, EntityType.PLACE, EntityType.SETTLEMENT):
        return entity
    return await session.get(EntityRow, entity.location_id) if entity.location_id is not None else None


async def community_of(session: AsyncSession, mortal: EntityRow) -> EntityRow | None:
    if mortal.location_id is not None:
        location = await session.get(EntityRow, mortal.location_id)
        if location is not None and location.entity_type in COMMUNITY_TYPES and location.status is EntityStatus.CANON:
            return location
    repository = BondRepository(session)
    bonds = [*await repository.outgoing(mortal.id, BondKind.LIVES_IN), *await repository.outgoing(mortal.id, BondKind.MEMBER_OF)]
    for bond in sorted(bonds, key=lambda row: row.id):
        target = await session.get(EntityRow, bond.target_node_id)
        if target is not None and target.entity_type in COMMUNITY_TYPES and target.status is EntityStatus.CANON:
            return target
    return None


async def active_bond_exists(session: AsyncSession, source: int, target: int, kind: BondKind) -> bool:
    statement = select(BondRow.id).where(
        BondRow.source_node_id == source, BondRow.target_node_id == target, BondRow.kind == kind, BondRow.state == BondState.ACTIVE
    )
    return await session.scalar(statement.limit(1)) is not None


async def owners_of(session: AsyncSession, resource_id: int) -> list[EntityRow]:
    bonds = await BondRepository(session).incoming(resource_id, BondKind.OWNS)
    owners: list[EntityRow] = []
    for bond in bonds:
        owner = await session.get(EntityRow, bond.source_node_id)
        if owner is not None and owner.status is EntityStatus.CANON and owner not in owners:
            owners.append(owner)
    return owners
