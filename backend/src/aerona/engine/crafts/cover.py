from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.crafts import InsurancePolicyRow, InsurerRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.households import HouseholdMemberRow, HouseholdRow
from aerona.db.write_guard import held
from aerona.domain.enums.crafts import InsuranceCover
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import shift_points
from aerona.engine.recording.record import record


async def cargo_holders(session: AsyncSession) -> frozenset[int]:
    rows = await session.scalars(
        select(InsurancePolicyRow.holder_node_id)
        .join(InsurerRow, InsurerRow.insurer_entity_id == InsurancePolicyRow.insurer_entity_id)
        .where(InsurancePolicyRow.cover == InsuranceCover.CARGO, InsurancePolicyRow.active.is_(True), InsurerRow.ruined.is_(False))
    )
    return frozenset(rows)


async def pay_household(session: AsyncSession, member_id: int, amount: int) -> bool:
    member = await session.get(HouseholdMemberRow, member_id)
    household = await session.get(HouseholdRow, member.household_id) if member is not None else None
    if household is None or "wealth" in household.locked:
        return False
    household.wealth += amount
    return True


async def claim(session: AsyncSession, holder_id: int, cover: InsuranceCover, loss: int) -> int:
    if loss <= 0 or held(holder_id):
        return 0
    policy = await session.scalar(
        select(InsurancePolicyRow)
        .join(InsurerRow, InsurerRow.insurer_entity_id == InsurancePolicyRow.insurer_entity_id)
        .where(
            InsurancePolicyRow.holder_node_id == holder_id, InsurancePolicyRow.cover == cover, InsurancePolicyRow.active.is_(True), InsurerRow.ruined.is_(False)
        )
        .order_by(InsurancePolicyRow.id)
        .limit(1)
    )
    if policy is None:
        return 0
    insurer = await session.get(InsurerRow, policy.insurer_entity_id)
    if insurer is None or held(insurer.insurer_entity_id):
        return 0
    paid = min(loss, policy.sum_insured)
    if cover is InsuranceCover.LIFE:
        if not await pay_household(session, holder_id, paid):
            return 0
    else:
        holder = await session.get(EntityRow, holder_id)
        if holder is None:
            return 0
        await shift_points(session, holder, paid)
    if "pool" not in insurer.locked:
        insurer.pool -= paid
    if "claims" not in policy.locked:
        policy.claims += 1
    return paid


async def insured_loss(ctx: TickContext, holder_id: int | None, cover: InsuranceCover, loss: int) -> int:
    if holder_id is None:
        return 0
    paid = await claim(ctx.session, holder_id, cover, loss)
    if paid > 0:
        await record(ctx, "insurance.paid", roles={IncidentRole.BENEFICIARY: holder_id}, facts={"cover": cover, "paid": paid})
    return paid
