from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.bonds import BondRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import BondKind, BondRole, BondState
from aerona.domain.enums.entity import EngineKind, EntityType

CONTAINER_TYPES = frozenset({EntityType.REGION, EntityType.PLACE, EntityType.SETTLEMENT, EntityType.PEOPLE, EntityType.FACTION, EntityType.CULT})
MARKET_REASON = "market trade across worlds"


async def close_mismatched_inside(session: AsyncSession, epoch: int) -> int:
    rows = await session.execute(select(EntityRow.id, EntityRow.location_id, EntityRow.entity_type))
    locations: dict[int, int | None] = {}
    types: dict[int, EntityType] = {}
    for entity_id, location_id, entity_type in rows:
        locations[entity_id] = location_id
        types[entity_id] = entity_type
    repository = BondRepository(session)
    closed = 0
    statement = select(BondRow).where(BondRow.kind == BondKind.INSIDE, BondRow.state == BondState.ACTIVE).order_by(BondRow.id)
    for bond in list(await session.scalars(statement)):
        if bond.role is BondRole.SPIRIT_BINDING or bond.source_node_id not in locations:
            continue
        if types.get(bond.target_node_id) in CONTAINER_TYPES and locations[bond.source_node_id] != bond.target_node_id:
            await repository.deactivate(bond, epoch)
            closed += 1
    return closed


async def close_market_trade(session: AsyncSession, epoch: int) -> int:
    markets = {
        entity_id: world_id
        for entity_id, world_id in await session.execute(select(EntityRow.id, EntityRow.world_id).where(EntityRow.engine_kind == EngineKind.WANDERING_MARKET))
    }
    if not markets:
        return 0
    worlds = {entity_id: world_id for entity_id, world_id in await session.execute(select(EntityRow.id, EntityRow.world_id))}
    repository = BondRepository(session)
    closed = 0
    statement = select(BondRow).where(BondRow.kind == BondKind.TRADES_WITH, BondRow.state == BondState.ACTIVE).order_by(BondRow.id)
    for bond in list(await session.scalars(statement)):
        for market, partner in ((bond.source_node_id, bond.target_node_id), (bond.target_node_id, bond.source_node_id)):
            if market in markets and worlds.get(partner) is not None and worlds[partner] != markets[market]:
                await repository.deactivate(bond, epoch, MARKET_REASON)
                closed += 1
                break
    return closed
