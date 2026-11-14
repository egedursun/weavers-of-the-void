from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.customs import TimeBudgetRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import ValueAxis, ValueHolder
from aerona.domain.enums.society import SocialClass
from aerona.engine.context import TickContext
from aerona.engine.mind.book import stored_values
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import shift_stat

TEN = 10


@dataclass
class TimeTally:
    seeded: int = 0
    towns: int = 0


def shares_for(values: dict[ValueAxis, int]) -> dict[str, int]:
    leisure = clamp_int(10 + values.get(ValueAxis.LEISURE, 0) // 10, 0, 40)
    worship = clamp_int(10 + values.get(ValueAxis.PIETY, 0) // 10, 0, 40)
    service = clamp_int(2 + values.get(ValueAxis.MARTIAL, 0) // 20, 0, 20)
    rest, travel = 20, 3
    return {
        "work": max(0, PERCENT - leisure - worship - service - rest - travel),
        "rest": rest,
        "worship": worship,
        "leisure": leisure,
        "travel": travel,
        "service": service,
    }


async def budgets_of(ctx: TickContext, people_id: int) -> dict[SocialClass, TimeBudgetRow]:
    rows = await ctx.session.scalars(select(TimeBudgetRow).where(TimeBudgetRow.people_entity_id == people_id))
    return {row.social_class: row for row in rows}


async def seed_budgets(ctx: TickContext, people: EntityRow, tally: TimeTally) -> dict[SocialClass, TimeBudgetRow]:
    found = await budgets_of(ctx, people.id)
    if found or held(people.id):
        return found
    shares = shares_for(await stored_values(ctx.session, ValueHolder.CULTURE, people.id))
    for social_class in SocialClass:
        found[social_class] = TimeBudgetRow(people_entity_id=people.id, social_class=social_class, **shares, locked=[])
        ctx.session.add(found[social_class])
    tally.seeded += 1
    return found


async def live_by(ctx: TickContext, town: EntityRow, budgets: dict[SocialClass, TimeBudgetRow], tally: TimeTally) -> None:
    table = ctx.rules.time_budgets
    society = await ctx.session.get(CommunitySocietyRow, town.id)
    if society is None:
        return
    work = worship = rest = travel = service = 0.0
    for social_class, row in budgets.items():
        share = float(getattr(society, f"share_{social_class.value}", 0.0)) / PERCENT
        work += row.work * share
        worship += row.worship * share
        rest += row.rest * share
        travel += row.travel * share
        service += row.service * share
        key = f"satisfaction_{social_class.value}"
        lift = round_half_up((row.leisure - table.usual_leisure) / TEN * table.leisure_satisfaction / TEN)
        if lift:
            setattr(society, key, clamp_int(int(getattr(society, key)) + lift, 0, PERCENT))
    shift_stat(town, "prosperity", (work - table.usual_work) * table.output_pct / PERCENT / TEN, low=0, high=PERCENT)
    shift_stat(town, "piety", worship / TEN * table.worship_piety / TEN, low=0, high=PERCENT)
    shift_stat(town, "prosperity", travel / TEN * table.travel_trade / TEN, low=0, high=PERCENT)
    shift_stat(town, "defense", service / TEN * table.service_defense / TEN, low=0, high=PERCENT)
    profile = await ctx.session.get(SettlementProfileRow, town.id)
    if profile is not None and "unrest" not in profile.locked:
        profile.unrest = clamp_int(profile.unrest - round_half_up((rest - table.usual_rest) / TEN * table.rest_calm), 0, PERCENT)
    tally.towns += 1


async def keep_time_budgets(ctx: TickContext, tally: TimeTally) -> None:
    for people in list(
        await ctx.session.scalars(
            select(EntityRow).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
        )
    ):
        budgets = await seed_budgets(ctx, people, tally)
        if not budgets:
            continue
        for town in list(
            await ctx.session.scalars(
                select(EntityRow)
                .where(EntityRow.affiliated_entity_id == people.id, EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON)
                .order_by(EntityRow.id)
            )
        ):
            if not held(town.id):
                await live_by(ctx, town, budgets, tally)
    await ctx.session.flush()
