from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import BondKind, BondRole, BondState
from aerona.domain.enums.entity import EntityStatus, EntityType

RULED_COMMUNITIES = frozenset({EntityType.SETTLEMENT, EntityType.PEOPLE, EntityType.FACTION, EntityType.CULT})
DUPLICATE_RULE = "duplicate rule"


async def homeland_to_lives_in(session: AsyncSession, epoch: int) -> int:
    repository = BondRepository(session)
    statement = select(BondRow).where(BondRow.kind == BondKind.RULES, BondRow.role == BondRole.HOMELAND, BondRow.state == BondState.ACTIVE).order_by(BondRow.id)
    converted = 0
    for bond in list(await session.scalars(statement)):
        await repository.deactivate(bond, epoch)
        if not await repository.active_between(bond.source_node_id, bond.target_node_id, [BondKind.LIVES_IN]):
            await repository.connect(BondDraft(bond.source_node_id, bond.target_node_id, BondKind.LIVES_IN, epoch, description=bond.description))
        converted += 1
    return converted


async def single_rule(session: AsyncSession, epoch: int) -> int:
    targets = {
        entity_id
        for entity_id in await session.scalars(
            select(EntityRow.id).where(EntityRow.entity_type.in_(list(RULED_COMMUNITIES)), EntityRow.status == EntityStatus.CANON)
        )
    }
    living = set(await session.scalars(select(EntityRow.id).where(EntityRow.status == EntityStatus.CANON)))
    statement = select(BondRow).where(BondRow.kind == BondKind.RULES, BondRow.state == BondState.ACTIVE).order_by(BondRow.id)
    by_target: dict[int, list[BondRow]] = {}
    for bond in await session.scalars(statement):
        if bond.target_node_id in targets and bond.source_node_id in living:
            by_target.setdefault(bond.target_node_id, []).append(bond)
    repository = BondRepository(session)
    closed = 0
    for bonds in by_target.values():
        if len(bonds) < 2:
            continue
        keeper = max((bond for bond in bonds if bond.role is not BondRole.HOMELAND), key=lambda bond: bond.id, default=bonds[-1])
        for bond in bonds:
            if bond.id != keeper.id:
                await repository.deactivate(bond, epoch, DUPLICATE_RULE)
                closed += 1
    return closed
