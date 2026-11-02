from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.bonds import BondRepository
from aerona.db.tables.bonds import BondRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.engine.services.war import ever_fought
from aerona.rules.registry import Rules

NEVER_FOUGHT = "never fought"


async def close_unfought_truces(session: AsyncSession, rules: Rules, epoch: int) -> int:
    if rules.diplomacy.truce_without_war:
        return 0
    repository = BondRepository(session)
    closed = 0
    for bond in list(await session.scalars(select(BondRow).where(BondRow.kind == BondKind.TRUCE, BondRow.state == BondState.ACTIVE).order_by(BondRow.id))):
        if not await ever_fought(session, bond.source_node_id, bond.target_node_id):
            await repository.deactivate(bond, epoch, NEVER_FOUGHT)
            closed += 1
    return closed
