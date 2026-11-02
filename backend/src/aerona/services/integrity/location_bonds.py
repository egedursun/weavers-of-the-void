from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import BondKind, BondRole, BondState
from aerona.domain.enums.entity import EntityStatus

PLACED_STATUSES = (EntityStatus.CANON, EntityStatus.FULFILLED)


async def _inside_bonds(session: AsyncSession) -> dict[int, list[BondRow]]:
    statement = select(BondRow).where(BondRow.kind == BondKind.INSIDE, BondRow.state == BondState.ACTIVE).order_by(BondRow.id)
    found: dict[int, list[BondRow]] = {}
    for bond in await session.scalars(statement):
        found.setdefault(bond.source_node_id, []).append(bond)
    return found


async def add_missing_inside_bonds(session: AsyncSession, epoch: int) -> int:
    bonds = await _inside_bonds(session)
    repository = BondRepository(session)
    statuses = {entity_id: status for entity_id, status in await session.execute(select(EntityRow.id, EntityRow.status))}
    added = 0
    for entity in await session.scalars(select(EntityRow).where(EntityRow.status.in_(PLACED_STATUSES), EntityRow.location_id.is_not(None))):
        location = entity.location_id
        if location is None or statuses.get(location) not in PLACED_STATUSES:
            continue
        if any(bond.target_node_id == location for bond in bonds.get(entity.id, [])):
            continue
        await repository.connect(BondDraft(entity.id, location, BondKind.INSIDE, epoch))
        added += 1
    return added


async def close_stale_inside_bonds(session: AsyncSession, epoch: int) -> int:
    bonds = await _inside_bonds(session)
    locations = {entity_id: location for entity_id, location in await session.execute(select(EntityRow.id, EntityRow.location_id))}
    repository = BondRepository(session)
    closed = 0
    for source, own in bonds.items():
        current = locations.get(source)
        if current is None or not any(bond.target_node_id == current for bond in own):
            continue
        for bond in own:
            if bond.target_node_id != current and bond.role is not BondRole.SPIRIT_BINDING:
                await repository.deactivate(bond, epoch)
                closed += 1
    return closed
