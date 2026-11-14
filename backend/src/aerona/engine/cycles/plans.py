from dataclasses import dataclass

from sqlalchemy import select

from aerona.db.tables.cycles import LongPlanRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.genetics import AllelePoolRow
from aerona.db.tables.polity import HouseProfileRow, PolityProfileRow
from aerona.db.tables.regime import BreedingPlanRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.cycles import LongPlanKind, LongPlanStatus
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.polity import HouseTrait
from aerona.domain.enums.structure import StructureKind
from aerona.engine.collective.book import ruler_id, shift
from aerona.engine.context import TickContext
from aerona.engine.divine.gods import divine_of
from aerona.engine.economy.purse import take_coin
from aerona.engine.genetics.pools import shifted_gift
from aerona.engine.notes import note
from aerona.engine.polity.seats import faction_leader
from aerona.engine.primitives.faith import living_patron
from aerona.engine.primitives.folk import homes_of
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.queries import connect, living_entity
from aerona.engine.sacred.forecasts import steer_forecast
from aerona.engine.services.community_relations import change_relation
from aerona.engine.structures.construction import Commission, begin

BRED_TRAITS = (HouseTrait.FERTILE, HouseTrait.LONG_LIVED, HouseTrait.GIANT_BLOODED, HouseTrait.SEER_GIFT)
PERCENT_SPAN = 100


@dataclass
class PlanTally:
    advanced: int = 0
    completed: int = 0
    exposed: int = 0
    carried: int = 0
    disrupted: int = 0
    abandoned: int = 0


async def active_plans(ctx: TickContext) -> list[LongPlanRow]:
    return list(await ctx.session.scalars(select(LongPlanRow).where(LongPlanRow.status == LongPlanStatus.ACTIVE).order_by(LongPlanRow.id)))


async def heir_carrier(ctx: TickContext, holder: EntityRow) -> int | None:
    if holder.entity_type is EntityType.POLITY:
        return await ruler_id(ctx, holder.id)
    if holder.entity_type in {EntityType.FACTION, EntityType.CULT}:
        return await faction_leader(ctx, holder.id)
    return None


async def carrier_alive(ctx: TickContext, carrier_id: int | None) -> bool:
    if carrier_id is None:
        return False
    if await living_entity(ctx.session, carrier_id) is not None:
        return True
    return await divine_of(ctx.session, carrier_id) is not None


async def pass_on(ctx: TickContext, plan: LongPlanRow, holder: EntityRow | None, tally: PlanTally) -> None:
    if "carrier_node_id" in plan.locked or await carrier_alive(ctx, plan.carrier_node_id) or holder is None:
        return
    heir = await heir_carrier(ctx, holder)
    if heir is None or heir == plan.carrier_node_id:
        return
    plan.carrier_node_id = heir
    tally.carried += 1
    heir_row = await ctx.session.get(EntityRow, heir)
    await note(ctx, f"{heir_row.name if heir_row else 'A new hand'} took up {plan.name} for {holder.name}.", key="plans.carried", ids=[holder.id, heir])


async def holder_pays(ctx: TickContext, plan: LongPlanRow, holder: EntityRow | None) -> bool:
    if holder is None:
        return await divine_of(ctx.session, plan.holder_node_id) is not None
    return await take_coin(ctx.session, ctx.rules, holder, plan.step_cost)


async def owner_of_target(ctx: TickContext, plan: LongPlanRow) -> EntityRow | None:
    if plan.target_node_id is None:
        return None
    target = await living_entity(ctx.session, plan.target_node_id)
    if target is None:
        return None
    if target.entity_type in {EntityType.SETTLEMENT, EntityType.PEOPLE, EntityType.POLITY}:
        return target
    return None


async def expose(ctx: TickContext, plan: LongPlanRow, holder: EntityRow | None, tally: PlanTally) -> None:
    table = ctx.rules.long_plans
    if plan.exposed or "exposed" in plan.locked:
        return
    chance = table.expose_pct * (PERCENT_SPAN - plan.secrecy) / PERCENT_SPAN
    if not ctx.rng(f"plan.expose.{plan.id}.{ctx.epoch}").chance(chance):
        return
    plan.exposed = True
    tally.exposed += 1
    owner = await owner_of_target(ctx, plan)
    if owner is not None and holder is not None and owner.id != holder.id:
        await change_relation(ctx, owner.id, holder.id, -table.exposed_relation, MemoryKind.BETRAYED_ME, note=plan.name)
    await note(ctx, f"The long design called {plan.name} came to light.", key="plans.exposed", ids=[plan.holder_node_id, *([owner.id] if owner else [])])


async def disrupt(ctx: TickContext, plan: LongPlanRow, tally: PlanTally) -> bool:
    table = ctx.rules.long_plans
    if not plan.exposed or "progress" in plan.locked or not ctx.rng(f"plan.disrupt.{plan.id}.{ctx.epoch}").chance(table.disrupt_pct):
        return False
    plan.progress = max(0, plan.progress - table.disrupt_steps)
    tally.disrupted += 1
    await note(ctx, f"Rivals set back {plan.name} by {table.disrupt_steps} steps.", key="plans.disrupted", ids=[plan.holder_node_id])
    return True


async def plan_god(ctx: TickContext, holder: EntityRow | None, holder_id: int) -> int | None:
    if holder is None:
        return holder_id if await divine_of(ctx.session, holder_id) is not None else None
    if holder.entity_type is EntityType.POLITY:
        profile = await ctx.session.get(PolityProfileRow, holder.id)
        capital = await living_entity(ctx.session, profile.capital_entity_id) if profile is not None and profile.capital_entity_id else None
        patron = await living_patron(ctx.session, capital or holder)
    else:
        patron = await living_patron(ctx.session, holder)
    return patron.id if patron is not None else None


async def target_towns(ctx: TickContext, target_id: int | None) -> list[EntityRow]:
    if target_id is None:
        return []
    target = await living_entity(ctx.session, target_id)
    if target is None:
        rows = await ctx.session.scalars(
            select(EntityRow)
            .where(EntityRow.world_id == target_id, EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON)
            .order_by(EntityRow.id)
        )
        return list(rows)
    if target.entity_type is EntityType.SETTLEMENT:
        return [target]
    found = []
    for home_id in sorted(await homes_of(ctx.session, target)):
        home = await living_entity(ctx.session, home_id)
        if home is not None and home.entity_type is EntityType.SETTLEMENT:
            found.append(home)
    return found


async def transform_land(ctx: TickContext, plan: LongPlanRow) -> int:
    table = ctx.rules.long_plans
    if plan.target_node_id is None:
        return 0
    region = await ctx.session.get(RegionEnvironmentRow, plan.target_node_id)
    regions = (
        [region]
        if region is not None
        else list(
            await ctx.session.scalars(
                select(RegionEnvironmentRow).where(RegionEnvironmentRow.world_id == plan.target_node_id).order_by(RegionEnvironmentRow.entity_id)
            )
        )
    )
    for row in regions:
        if held(row.entity_id):
            continue
        shift(row, "moisture", table.eco_moisture)
        shift(row, "soil_fertility", table.eco_fertility)
    return len(regions)


async def breed_people(ctx: TickContext, plan: LongPlanRow) -> bool:
    pool = await ctx.session.get(AllelePoolRow, plan.target_node_id) if plan.target_node_id is not None else None
    if pool is None or "frequencies" in pool.locked or held(pool.people_node_id):
        return False
    pool.frequencies = shifted_gift(pool.frequencies, ctx.rules.long_plans.bloodline_gift_pct)
    return True


async def breed(ctx: TickContext, plan: LongPlanRow) -> HouseTrait | None:
    house = await ctx.session.get(HouseProfileRow, plan.target_node_id) if plan.target_node_id is not None else None
    if house is None or "traits" in house.locked or held(house.house_entity_id):
        return None
    missing = [trait for trait in BRED_TRAITS if trait.value not in house.traits]
    if not missing:
        return None
    trait = ctx.rng(f"plan.breed.{plan.id}").pick(missing)
    house.traits = [*house.traits, trait.value]
    return trait


async def convert(ctx: TickContext, plan: LongPlanRow, holder: EntityRow | None) -> int:
    god = await plan_god(ctx, holder, plan.holder_node_id)
    if god is None:
        return 0
    converted = 0
    for town in await target_towns(ctx, plan.target_node_id):
        if held(town.id):
            continue
        if await connect(ctx.session, town.id, god, BondKind.WORSHIPS, ctx.epoch, description=plan.name) is not None:
            converted += 1
    return converted


async def raise_wonder(ctx: TickContext, plan: LongPlanRow) -> EntityRow | None:
    towns = await target_towns(ctx, plan.target_node_id)
    site = next((town for town in towns if not held(town.id)), None)
    if site is None:
        return None
    work, construction = await begin(ctx, Commission(site=site, kind=StructureKind.WONDER, name=plan.name))
    construction.funds += plan.steps * plan.step_cost * ctx.rules.long_plans.wonder_funds_pct // PERCENT_SPAN
    return work


async def complete(ctx: TickContext, plan: LongPlanRow, holder: EntityRow | None, tally: PlanTally) -> None:
    plan.status = LongPlanStatus.COMPLETED
    plan.finished_epoch = ctx.epoch
    tally.completed += 1
    ids = [plan.holder_node_id, *([plan.target_node_id] if plan.target_node_id is not None else [])]
    if plan.kind is LongPlanKind.ECOLOGICAL_TRANSFORMATION:
        changed = await transform_land(ctx, plan)
        await note(ctx, f"{plan.name} was fulfilled: {changed} lands were remade.", key="plans.completed", ids=ids)
    elif plan.kind is LongPlanKind.BLOODLINE:
        trait = await breed(ctx, plan)
        found = trait.value.replace("_", " ") if trait is not None else "richer in the gift" if await breed_people(ctx, plan) else "nothing new"
        await note(ctx, f"{plan.name} was fulfilled: the line was bred to be {found}.", key="plans.completed", ids=ids)
    elif plan.kind is LongPlanKind.CONVERSION:
        converted = await convert(ctx, plan, holder)
        await note(ctx, f"{plan.name} was fulfilled: {converted} towns turned to a new worship.", key="plans.completed", ids=ids)
    elif plan.kind is LongPlanKind.FORECAST:
        lifted = await steer_forecast(ctx, plan.id)
        await note(ctx, f"{plan.name} was fulfilled: the realm's stress eased by {lifted}.", key="plans.completed", ids=ids)
    else:
        work = await raise_wonder(ctx, plan)
        await note(ctx, f"{plan.name} was fulfilled: {work.name if work else 'no site'} rose from its saving.", key="plans.completed", ids=ids)


async def advance_plans(ctx: TickContext, tally: PlanTally) -> None:
    table = ctx.rules.long_plans
    for plan in await active_plans(ctx):
        if held(plan.holder_node_id) or "status" in plan.locked:
            continue
        holder = await living_entity(ctx.session, plan.holder_node_id)
        if holder is None and await divine_of(ctx.session, plan.holder_node_id) is None:
            plan.status = LongPlanStatus.ABANDONED
            plan.finished_epoch = ctx.epoch
            tally.abandoned += 1
            await note(ctx, f"{plan.name} was abandoned; none was left to carry it.", key="plans.abandoned", ids=[plan.holder_node_id])
            continue
        await pass_on(ctx, plan, holder, tally)
        await expose(ctx, plan, holder, tally)
        if await disrupt(ctx, plan, tally):
            continue
        if "progress" in plan.locked or await ctx.session.get(BreedingPlanRow, plan.id) is not None or not await holder_pays(ctx, plan, holder):
            continue
        plan.progress = min(plan.steps, plan.progress + max(1, round_half_up(table.steps_per_epoch)))
        tally.advanced += 1
        if plan.progress >= plan.steps:
            await complete(ctx, plan, holder, tally)
    await ctx.session.flush()
