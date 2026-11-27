from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.fixups import fixup_due
from aerona.db.tables.body import BodyRow, InjuryRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.records import IncidentFactRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import Capacity, DamageType, HarmCause, InjuryState
from aerona.domain.enums.entity import EntityType
from aerona.engine.body.book import recorded_plan, species_traits
from aerona.engine.body.capacities import perception_factor
from aerona.engine.body.digits import replan
from aerona.rules.registry import Rules

PLANS_FIXUP = "body.w52_plans"
PLAN_LOCK = "plan"


async def backfill_plans(session: AsyncSession) -> int:
    if not await fixup_due(session, PLANS_FIXUP):
        return 0
    moved = 0
    found = await session.execute(
        select(BodyRow, EntityRow).join(EntityRow, EntityRow.id == BodyRow.node_id).where(EntityRow.entity_type == EntityType.SPECIES).order_by(BodyRow.node_id)
    )
    for body, species in found:
        if held(body.node_id) or PLAN_LOCK in body.locked:
            continue
        plan = await recorded_plan(session, species, await species_traits(session, species.id))
        if plan is not body.plan:
            replan(body, plan)
            moved += 1
    session.add(AppliedFixupRow(key=PLANS_FIXUP, result={"bodies": moved}))
    await session.flush()
    return moved


DROWNED_FIXUP = "damage.w52"


async def backfill_drowned(session: AsyncSession) -> int:
    if not await fixup_due(session, DROWNED_FIXUP):
        return 0
    drowned = select(IncidentFactRow.incident_id).where(IncidentFactRow.name.ilike("%drown%"))
    rows = await session.scalars(select(InjuryRow).where(InjuryRow.state == InjuryState.LETHAL, InjuryRow.incident_id.in_(drowned)).order_by(InjuryRow.id))
    moved = 0
    for row in rows:
        if held(row.bearer_node_id) or row.damage_type is DamageType.ASPHYXIA:
            continue
        row.damage_type = DamageType.ASPHYXIA
        moved += 1
    session.add(AppliedFixupRow(key=DROWNED_FIXUP, result={"injuries": moved}))
    await session.flush()
    return moved


BIRTH_FIXUP = "harm.w52"


async def backfill_birth_harm(session: AsyncSession) -> int:
    if not await fixup_due(session, BIRTH_FIXUP):
        return 0
    births = select(IncidentFactRow.incident_id).where(IncidentFactRow.name.ilike("%childbirth%"))
    rows = await session.scalars(select(InjuryRow).where(InjuryRow.incident_id.in_(births)).order_by(InjuryRow.id))
    moved = 0
    for row in rows:
        if held(row.bearer_node_id) or row.cause_kind is HarmCause.CHILDBIRTH:
            continue
        row.cause_kind = HarmCause.CHILDBIRTH
        moved += 1
    session.add(AppliedFixupRow(key=BIRTH_FIXUP, result={"injuries": moved}))
    await session.flush()
    return moved


CAPACITIES_FIXUP = "capacities.w52"


async def backfill_capacities(session: AsyncSession, rules: Rules) -> int:
    if not await fixup_due(session, CAPACITIES_FIXUP):
        return 0
    filled = 0
    for body in await session.scalars(select(BodyRow).order_by(BodyRow.node_id)):
        if held(body.node_id):
            continue
        if Capacity.ENDURANCE.value not in body.locked:
            body.endurance = body.mobility
        if Capacity.PERCEPTION.value not in body.locked:
            body.perception = round(PERCENT * perception_factor(rules.capacities, body.hearing, body.sight))
        filled += 1
    session.add(AppliedFixupRow(key=CAPACITIES_FIXUP, result={"bodies": filled}))
    await session.flush()
    return filled
