from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass

from sqlalchemy import select

from aerona.core.total import total
from aerona.db.tables.cycles import LongPlanRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.genetics import AllelePoolRow
from aerona.db.tables.polity import HouseProfileRow, PolityProfileRow
from aerona.db.tables.regime import BreedingPlanRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.cycles import LongPlanKind, LongPlanStatus, PlanOutcome
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import HouseTrait
from aerona.domain.enums.structure import StructureKind
from aerona.engine.collective.book import ruler_id, shift
from aerona.engine.context import TickContext
from aerona.engine.cycles.plan_works import (
    Fulfilled,
    fulfil_exploration,
    fulfil_line,
    fulfil_megastructure,
    fulfil_network,
    fulfil_programme,
    fulfil_realm,
    fulfil_reform,
    fulfil_restoration,
)
from aerona.engine.divine.gods import divine_of
from aerona.engine.economy.purse import take_coin
from aerona.engine.genetics.pools import shifted_gift
from aerona.engine.polity.seats import faction_leader
from aerona.engine.primitives.faith import living_patron
from aerona.engine.primitives.folk import homes_of
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.queries import connect, living_entity
from aerona.engine.recording.record import record
from aerona.engine.recording.terms import explaining
from aerona.engine.sacred.forecasts import steer_forecast
from aerona.engine.services.community_relations import change_relation
from aerona.engine.structures.construction import Commission, begin

BRED_TRAITS = (
    HouseTrait.FERTILE,
    HouseTrait.LONG_LIVED,
    HouseTrait.GIANT_BLOODED,
    HouseTrait.SEER_GIFT,
    HouseTrait.STRONG_BLOODED,
    HouseTrait.SWIFT,
    HouseTrait.QUICK_HEALING,
    HouseTrait.SHARP_SENSED,
    HouseTrait.STEADY,
    HouseTrait.QUICK_MINDED,
)
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
    await record(
        ctx,
        "plans.carried",
        roles={IncidentRole.SUCCESSOR: heir, IncidentRole.OWNER: holder.id},
        facts={"plan": plan.name, "plan_kind": plan.kind, "progress": plan.progress, "steps": plan.steps},
        place=holder.location_id,
    )


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
    await record(
        ctx,
        "plans.exposed",
        roles={IncidentRole.OWNER: plan.holder_node_id, IncidentRole.TARGET: owner.id if owner is not None else None},
        facts={"plan": plan.name, "plan_kind": plan.kind, "secrecy": plan.secrecy, "chance": chance},
        place=holder.location_id if holder is not None else None,
    )


async def disrupt(ctx: TickContext, plan: LongPlanRow, tally: PlanTally) -> bool:
    table = ctx.rules.long_plans
    if not plan.exposed or "progress" in plan.locked or not ctx.rng(f"plan.disrupt.{plan.id}.{ctx.epoch}").chance(table.disrupt_pct):
        return False
    before = plan.progress
    plan.progress = max(0, plan.progress - table.disrupt_steps)
    tally.disrupted += 1
    await record(
        ctx,
        "plans.disrupted",
        roles={IncidentRole.OWNER: plan.holder_node_id},
        facts={"plan": plan.name, "plan_kind": plan.kind, "lost": before - plan.progress, "progress": plan.progress, "chance": table.disrupt_pct},
    )
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


async def fulfil_ecology(ctx: TickContext, plan: LongPlanRow, _holder: EntityRow | None) -> Fulfilled:
    return PlanOutcome.LANDS_REMADE, {"count": await transform_land(ctx, plan)}


async def fulfil_bloodline(ctx: TickContext, plan: LongPlanRow, _holder: EntityRow | None) -> Fulfilled:
    design = await ctx.session.get(BreedingPlanRow, plan.id)
    if design is not None and design.claim_polity_id is not None:
        return PlanOutcome.BRED_NOTHING, {}
    trait = await breed(ctx, plan)
    if trait is not None:
        return PlanOutcome.LINE_BRED, {"trait": trait}
    return (PlanOutcome.GIFT_ENRICHED, {}) if await breed_people(ctx, plan) else (PlanOutcome.BRED_NOTHING, {})


async def fulfil_conversion(ctx: TickContext, plan: LongPlanRow, holder: EntityRow | None) -> Fulfilled:
    return PlanOutcome.TOWNS_CONVERTED, {"count": await convert(ctx, plan, holder)}


async def fulfil_wonder(ctx: TickContext, plan: LongPlanRow, _holder: EntityRow | None) -> Fulfilled:
    work = await raise_wonder(ctx, plan)
    return (PlanOutcome.WONDER_RAISED, {"made": work.id}) if work is not None else (PlanOutcome.NO_WONDER_SITE, {})


async def fulfil_forecast(ctx: TickContext, plan: LongPlanRow, _holder: EntityRow | None) -> Fulfilled:
    return PlanOutcome.STRESS_EASED, {"amount": await steer_forecast(ctx, plan.id)}


Fulfil = Callable[[TickContext, LongPlanRow, EntityRow | None], Awaitable[Fulfilled]]
FULFIL: Mapping[LongPlanKind, Fulfil] = total(
    LongPlanKind,
    {
        LongPlanKind.ECOLOGICAL_TRANSFORMATION: fulfil_ecology,
        LongPlanKind.BLOODLINE: fulfil_bloodline,
        LongPlanKind.CONVERSION: fulfil_conversion,
        LongPlanKind.WONDER: fulfil_wonder,
        LongPlanKind.FORECAST: fulfil_forecast,
        LongPlanKind.NETWORK: fulfil_network,
        LongPlanKind.MEGASTRUCTURE: fulfil_megastructure,
        LongPlanKind.PROGRAMME: fulfil_programme,
        LongPlanKind.REALM: fulfil_realm,
        LongPlanKind.LINE: fulfil_line,
        LongPlanKind.REFORM: fulfil_reform,
        LongPlanKind.EXPLORATION: fulfil_exploration,
        LongPlanKind.RESTORATION: fulfil_restoration,
    },
)


async def complete(ctx: TickContext, plan: LongPlanRow, holder: EntityRow | None, tally: PlanTally) -> None:
    plan.status = LongPlanStatus.COMPLETED
    plan.finished_epoch = ctx.epoch
    tally.completed += 1
    with explaining():
        outcome: PlanOutcome
        outcome, facts = await FULFIL[plan.kind](ctx, plan, holder)
        await record(
            ctx,
            f"plans.completed_{outcome.value}",
            roles={IncidentRole.OWNER: plan.holder_node_id, IncidentRole.TARGET: plan.target_node_id},
            facts={"plan": plan.name, "plan_kind": plan.kind, "epochs": ctx.epoch - plan.started_epoch, **facts},
            place=holder.location_id if holder is not None else None,
        )


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
            await record(
                ctx,
                "plans.abandoned",
                roles={IncidentRole.OWNER: plan.holder_node_id},
                facts={"plan": plan.name, "plan_kind": plan.kind, "progress": plan.progress, "steps": plan.steps},
            )
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
