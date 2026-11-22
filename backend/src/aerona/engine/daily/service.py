from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.daily_life import DomesticServiceRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.households import HouseholdMemberRow, HouseholdRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.daily_life import ServiceEnd, ServiceTerms
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.genetics import HouseholdRole
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.households.formation import join_household
from aerona.engine.mortal.life import adult
from aerona.engine.primitives.folk import present_among
from aerona.engine.recording.record import record


async def willing_servant(session: AsyncSession, household: HouseholdRow, hirer_id: int | None) -> EntityRow | None:
    if household.settlement_node_id is None:
        return None
    serving = select(DomesticServiceRow.servant_node_id)
    heads = select(HouseholdRow.head_node_id).where(HouseholdRow.head_node_id.is_not(None))
    richer = (
        select(HouseholdMemberRow.member_node_id)
        .join(HouseholdRow, HouseholdRow.id == HouseholdMemberRow.household_id)
        .where(HouseholdRow.wealth >= household.wealth)
    )
    rows = await session.execute(
        select(EntityRow, MortalProfileRow)
        .join(MortalProfileRow, MortalProfileRow.entity_id == EntityRow.id)
        .where(
            EntityRow.entity_type == EntityType.MORTAL,
            EntityRow.status == EntityStatus.CANON,
            await present_among(session, [household.settlement_node_id]),
            EntityRow.id.not_in(serving),
            EntityRow.id.not_in(heads),
            EntityRow.id.not_in(richer),
            EntityRow.id != (hirer_id or 0),
        )
        .order_by(MortalProfileRow.wealth, EntityRow.id)
    )
    return next((mortal for mortal, profile in rows if adult(profile.life_stage) and not held(mortal.id)), None)


async def engage_servant(ctx: TickContext, household: HouseholdRow, terms: ServiceTerms, wage: int) -> EntityRow | None:
    servant = await willing_servant(ctx.session, household, household.head_node_id)
    if servant is None:
        return None
    ctx.session.add(DomesticServiceRow(servant_node_id=servant.id, household_id=household.id, terms=terms, wage=wage, since_epoch=ctx.epoch, locked=[]))
    await join_household(ctx, household, servant, HouseholdRole.SERVANT)
    await record(
        ctx,
        "daily.servant_hired",
        roles={IncidentRole.ACTOR: household.head_node_id, IncidentRole.SUBJECT: servant.id},
        facts={"terms": terms, "wage": wage},
        place=household.settlement_node_id,
    )
    return servant


async def release_servant(ctx: TickContext, household: HouseholdRow) -> bool:
    query = select(DomesticServiceRow).where(DomesticServiceRow.household_id == household.id).order_by(DomesticServiceRow.since_epoch.desc())
    for service in await ctx.session.scalars(query):
        if held(service.servant_node_id) or service.locked:
            continue
        await ctx.session.delete(service)
        await record(
            ctx,
            "daily.servant_left",
            roles={IncidentRole.ACTOR: household.head_node_id, IncidentRole.SUBJECT: service.servant_node_id},
            facts={"reason": ServiceEnd.DISMISSED},
        )
        return True
    return False
