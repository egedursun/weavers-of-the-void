from collections.abc import Awaitable, Callable, Mapping

from sqlalchemy import select

from aerona.catalog.life.divine import HUNGER_TECHNIQUE
from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.cosmography import RiftRow
from aerona.db.tables.divine import BreachPointRow, NaturalLawProfileRow, OuterBeingProfileRow
from aerona.db.tables.entities import EntityFlagRow, EntityRow
from aerona.db.tables.outer_agency import OuterHeraldRow, OuterIncursionRow, OuterPactRow, OuterPlanRow, OuterRelationRow, OuterSealRow
from aerona.db.tables.powers import PowerRow
from aerona.db.tables.sons import SonRow
from aerona.db.write_guard import held
from aerona.domain.enums.arcana import SpellForm
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.cosmography import OPEN_RIFT_STATES, RiftState
from aerona.domain.enums.divine import OuterHunger
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.outer import IncursionStage, OuterFate, OuterGoal, OuterPlanState, OuterPrice, OuterRelation, OuterSealKind
from aerona.domain.enums.powers import PowerOrigin, PowerState
from aerona.domain.enums.son import SonStatus
from aerona.engine.context import TickContext
from aerona.engine.cosmos.sanity import shift_sanity
from aerona.engine.divine.outer import found_outer_cult, outer_profile
from aerona.engine.primitives.numbers import clamp_percent
from aerona.engine.primitives.queries import connect
from aerona.engine.primitives.stats import shift_stat, stat_or
from aerona.engine.primitives.transfers import move_amount
from aerona.engine.recording.record import FactInput, record

GOAL_TEXT: Mapping[OuterGoal, str] = total(
    OuterGoal,
    {
        OuterGoal.FEED: "to feed",
        OuterGoal.ENTER: "to enter the cosmos",
        OuterGoal.BE_WORSHIPPED: "to be worshipped",
        OuterGoal.UNMAKE_LAW: "to unmake a law",
        OuterGoal.GAIN_NAME: "to gain a name",
        OuterGoal.OPEN_RIFT: "to open a rift",
    },
)
STAGE_ORDER = (IncursionStage.PROBING, IncursionStage.BREACH, IncursionStage.MANIFESTATION)


async def tell(ctx: TickContext, being: EntityRow, key: str, facts: Mapping[str, FactInput] | None = None) -> None:
    await record(ctx, key, roles={IncidentRole.SUBJECT: being.id}, facts=facts, kind=ChronicleKind.OUTER_BEING, world_id=being.world_id)


async def living_beings(ctx: TickContext) -> list[EntityRow]:
    query = select(EntityRow).where(EntityRow.entity_type == EntityType.OUTER_BEING, EntityRow.status == EntityStatus.CANON)
    return list(await ctx.session.scalars(query.order_by(EntityRow.id)))


async def cults_of(ctx: TickContext, being_id: int) -> list[int]:
    flagged = select(EntityFlagRow.entity_id).where(EntityFlagRow.flag == EntityFlag.OUTER_CULT)
    found = select(BondRow.source_node_id).where(
        BondRow.target_node_id == being_id, BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE, BondRow.source_node_id.in_(flagged)
    )
    return sorted(set(await ctx.session.scalars(found)))


async def worshippers_of(ctx: TickContext, being_id: int) -> int:
    found = select(BondRow.id).where(BondRow.target_node_id == being_id, BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE)
    return len(list(await ctx.session.scalars(found)))


async def active_plan(ctx: TickContext, being_id: int) -> OuterPlanRow | None:
    query = select(OuterPlanRow).where(OuterPlanRow.outer_entity_id == being_id, OuterPlanRow.state == OuterPlanState.ACTIVE)
    return await ctx.session.scalar(query.order_by(OuterPlanRow.id).limit(1))


async def choose_goal(ctx: TickContext, being: EntityRow, profile: OuterBeingProfileRow) -> tuple[OuterGoal, int | None]:
    if profile.fed < ctx.rules.outer_beings.feed_gain:
        return OuterGoal.FEED, None
    rifts = await ctx.session.scalar(select(RiftRow.id).where(RiftRow.world_id == being.world_id, RiftRow.state.in_(list(OPEN_RIFT_STATES))).limit(1))
    if rifts is None and await breach_of(ctx, being) is None:
        return OuterGoal.OPEN_RIFT, being.world_id
    if not await cults_of(ctx, being.id):
        return OuterGoal.BE_WORSHIPPED, being.world_id
    law = await ctx.session.scalar(
        select(NaturalLawProfileRow.law_entity_id)
        .where(NaturalLawProfileRow.world_id == being.world_id, NaturalLawProfileRow.strength > 0)
        .order_by(NaturalLawProfileRow.strength.desc())
        .limit(1)
    )
    if law is not None and stat_or(being, "influence", 0) >= PERCENT // 2:
        return OuterGoal.UNMAKE_LAW, law
    if stat_or(being, "influence", 0) < PERCENT // 4:
        return OuterGoal.GAIN_NAME, None
    return OuterGoal.ENTER, rifts


async def plan_push(ctx: TickContext, being: EntityRow) -> int:
    table = ctx.rules.outer_beings
    heralds = list(await ctx.session.scalars(select(OuterHeraldRow).where(OuterHeraldRow.outer_entity_id == being.id)))
    push = table.plan_pace + sum(table.herald_push * herald.zeal // PERCENT for herald in heralds)
    return push + table.cult_push * len(await cults_of(ctx, being.id))


async def show_sign(ctx: TickContext, being: EntityRow, plan: OuterPlanRow) -> None:
    world = await ctx.session.get(WorldRow, being.world_id)
    if world is not None and not held(world.id):
        world.leakage = clamp_percent(world.leakage + ctx.rules.outer_beings.sign_leak)
    plan.sign_epoch = ctx.epoch
    await tell(ctx, being, "outer.sign", {"goal": plan.goal, "aim": GOAL_TEXT[plan.goal], "stage": plan.stage})


Fulfil = Callable[[TickContext, EntityRow, OuterPlanRow], Awaitable[None]]


async def fulfil_feed(ctx: TickContext, being: EntityRow, _plan: OuterPlanRow) -> None:
    profile = await outer_profile(ctx, being)
    if "fed" not in profile.locked:
        profile.fed += ctx.rules.outer_beings.feed_gain


async def breach_of(ctx: TickContext, being: EntityRow) -> BreachPointRow | None:
    query = select(BreachPointRow).where(BreachPointRow.outer_entity_id == being.id).order_by(BreachPointRow.id)
    found: BreachPointRow | None = await ctx.session.scalar(query.limit(1))
    return found


async def fulfil_enter(ctx: TickContext, being: EntityRow, plan: OuterPlanRow) -> None:
    rift = await ctx.session.get(RiftRow, plan.target_node_id) if plan.target_node_id is not None else None
    if rift is None:
        rift = await ctx.session.scalar(select(RiftRow).where(RiftRow.world_id == being.world_id, RiftRow.state.in_(list(OPEN_RIFT_STATES))).limit(1))
    if rift is not None:
        await open_incursion(ctx, being, rift.id, rift.region_entity_id)
        return
    breach = await breach_of(ctx, being)
    await open_incursion(ctx, being, None, breach.region_entity_id if breach is not None else None)


async def fulfil_worship(ctx: TickContext, being: EntityRow, _plan: OuterPlanRow) -> None:
    community = await ctx.session.scalar(
        select(EntityRow)
        .where(EntityRow.world_id == being.world_id, EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
        .limit(1)
    )
    if community is None or held(community.id):
        return
    await connect(ctx.session, community.id, being.id, BondKind.WORSHIPS, ctx.epoch, description="drawn to an outer being")
    born = select(BondRow.source_node_id).where(
        BondRow.target_node_id == community.id, BondRow.kind == BondKind.DESCENDS_FROM, BondRow.state == BondState.ACTIVE
    )
    flagged = select(EntityFlagRow.entity_id).where(EntityFlagRow.flag == EntityFlag.OUTER_CULT, EntityFlagRow.entity_id.in_(born))
    cult_id = await ctx.session.scalar(flagged.order_by(EntityFlagRow.entity_id).limit(1))
    cult = await ctx.session.get(EntityRow, cult_id) if cult_id is not None else await found_outer_cult(ctx, community)
    if cult is not None and not held(cult.id):
        await connect(ctx.session, cult.id, being.id, BondKind.WORSHIPS, ctx.epoch, description="serves an outer being")


async def fulfil_unmake(ctx: TickContext, being: EntityRow, plan: OuterPlanRow) -> None:
    row = await ctx.session.get(NaturalLawProfileRow, plan.target_node_id) if plan.target_node_id is not None else None
    if row is not None and "strength" not in row.locked and not held(row.law_entity_id):
        row.strength = clamp_percent(row.strength - ctx.rules.outer_beings.unmake_bite)


async def fulfil_name(ctx: TickContext, being: EntityRow, _plan: OuterPlanRow) -> None:
    shift_stat(being, "influence", ctx.rules.outer_beings.name_influence, 0)


async def fulfil_rift(ctx: TickContext, being: EntityRow, _plan: OuterPlanRow) -> None:
    rift = await ctx.session.scalar(
        select(RiftRow).where(RiftRow.world_id == being.world_id, RiftRow.state.in_([RiftState.CLOSING, RiftState.SEALED])).limit(1)
    )
    if rift is not None and "state" not in rift.locked:
        rift.state, rift.sealed_epoch = RiftState.OPENING, None
        return
    region = await ctx.session.scalar(
        select(EntityRow.id)
        .where(EntityRow.world_id == being.world_id, EntityRow.entity_type == EntityType.REGION, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
        .limit(1)
    )
    if region is not None:
        ctx.session.add(
            BreachPointRow(
                outer_entity_id=being.id,
                world_id=being.world_id,
                region_entity_id=region,
                strength=ctx.rules.outer_beings.breach_strength,
                opened_epoch=ctx.epoch,
            )
        )


FULFIL: Mapping[OuterGoal, Fulfil] = total(
    OuterGoal,
    {
        OuterGoal.FEED: fulfil_feed,
        OuterGoal.ENTER: fulfil_enter,
        OuterGoal.BE_WORSHIPPED: fulfil_worship,
        OuterGoal.UNMAKE_LAW: fulfil_unmake,
        OuterGoal.GAIN_NAME: fulfil_name,
        OuterGoal.OPEN_RIFT: fulfil_rift,
    },
)


async def advance_plan(ctx: TickContext, being: EntityRow, profile: OuterBeingProfileRow) -> bool:
    plan = await active_plan(ctx, being.id)
    if profile.fate is not OuterFate.ACTIVE:
        if plan is not None and "state" not in plan.locked:
            plan.state = OuterPlanState.THWARTED
        return False
    if plan is None:
        goal, target = await choose_goal(ctx, being, profile)
        plan = OuterPlanRow(outer_entity_id=being.id, goal=goal, target_node_id=target, started_epoch=ctx.epoch, locked=[])
        ctx.session.add(plan)
        await ctx.session.flush()
    stages = max(1, ctx.rules.outer_beings.plan_stages)
    if "progress" not in plan.locked:
        plan.progress = clamp_percent(plan.progress + await plan_push(ctx, being))
    reached = min(stages, plan.progress * stages // PERCENT)
    if reached > plan.stage and "stage" not in plan.locked:
        plan.stage = reached
        await show_sign(ctx, being, plan)
    if plan.progress >= PERCENT and "state" not in plan.locked:
        await FULFIL[plan.goal](ctx, being, plan)
        plan.state = OuterPlanState.ACHIEVED
        await tell(ctx, being, "outer.plan_achieved", {"goal": plan.goal, "aim": GOAL_TEXT[plan.goal]})
        return True
    return False


async def open_incursion(ctx: TickContext, being: EntityRow, rift_id: int | None, region_id: int | None) -> OuterIncursionRow:
    row = OuterIncursionRow(
        outer_entity_id=being.id,
        rift_id=rift_id,
        region_entity_id=region_id,
        strength=ctx.rules.outer_beings.breach_strength,
        started_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    await record(ctx, "outer.incursion", roles={IncidentRole.SUBJECT: being.id}, kind=ChronicleKind.OUTER_BEING, world_id=being.world_id)
    return row


def stage_for(ctx: TickContext, strength: int) -> IncursionStage:
    table = ctx.rules.outer_beings
    if strength <= 0:
        return IncursionStage.RECEDING
    if strength >= table.manifest_at:
        return IncursionStage.MANIFESTATION
    return IncursionStage.BREACH if strength >= table.breach_at else IncursionStage.PROBING


async def ward_off(ctx: TickContext, row: OuterIncursionRow, world_id: int) -> int:
    table = ctx.rules.outer_beings
    pushed = 0
    sons = select(SonRow).where(SonRow.status == SonStatus.ACTIVE, SonRow.current_world_id == world_id, SonRow.rebel.is_(False)).order_by(SonRow.id)
    for son in list(await ctx.session.scalars(sons)):
        if held(son.id) or son.essence < table.ward_essence:
            continue
        son.essence -= table.ward_essence
        pushed += table.ward_push
    return pushed


async def press_incursions(ctx: TickContext) -> int:
    table = ctx.rules.outer_beings
    live = 0
    for row in list(await ctx.session.scalars(select(OuterIncursionRow).where(OuterIncursionRow.ended_epoch.is_(None)).order_by(OuterIncursionRow.id))):
        being = await ctx.session.get(EntityRow, row.outer_entity_id)
        if being is None or held(being.id):
            continue
        profile = await outer_profile(ctx, being)
        rift = await ctx.session.get(RiftRow, row.rift_id) if row.rift_id is not None else None
        growth = table.incursion_growth if profile.fate is OuterFate.ACTIVE and (rift is None or rift.state in OPEN_RIFT_STATES) else -table.incursion_growth
        growth += table.cult_push * len(await cults_of(ctx, being.id))
        if row.stage is IncursionStage.MANIFESTATION:
            growth -= await ward_off(ctx, row, being.world_id)
        if "strength" not in row.locked:
            row.strength = clamp_percent(row.strength + growth)
        if "stage" not in row.locked:
            row.stage = stage_for(ctx, row.strength)
        if row.stage is IncursionStage.RECEDING:
            row.ended_epoch = ctx.epoch
            await tell(ctx, being, "outer.incursion_ended")
            continue
        depth = STAGE_ORDER.index(row.stage) + 1 if row.stage in STAGE_ORDER else len(STAGE_ORDER)
        land = await ctx.session.get(EntityRow, row.region_entity_id) if row.region_entity_id is not None else None
        if land is not None and not held(land.id):
            shift_sanity(ctx.rules, land, -table.incursion_sanity * depth)
        world = await ctx.session.get(WorldRow, being.world_id)
        if world is not None and not held(world.id):
            world.leakage = clamp_percent(world.leakage + table.incursion_leak * depth)
        live += 1
    return live


async def pay_mortal_price(ctx: TickContext, being: EntityRow, holder: EntityRow, price: OuterPrice) -> None:
    await PRICES[price](ctx, being, holder)


async def price_sanity(ctx: TickContext, _being: EntityRow, holder: EntityRow) -> None:
    shift_sanity(ctx.rules, holder, -ctx.rules.outer_beings.mortal_price_sanity)


async def price_years(ctx: TickContext, _being: EntityRow, holder: EntityRow) -> None:
    shift_stat(holder, "endurance", -ctx.rules.outer_beings.price_years, 0)


async def price_memory(ctx: TickContext, _being: EntityRow, holder: EntityRow) -> None:
    shift_stat(holder, "willpower", -ctx.rules.outer_beings.price_memory, 0)


async def price_name(ctx: TickContext, being: EntityRow, _holder: EntityRow) -> None:
    shift_stat(being, "influence", ctx.rules.outer_beings.name_influence // 2, 0)


async def price_service(ctx: TickContext, being: EntityRow, holder: EntityRow) -> None:
    if await ctx.session.get(OuterHeraldRow, holder.id) is None:
        ctx.session.add(OuterHeraldRow(herald_node_id=holder.id, outer_entity_id=being.id, bound_epoch=ctx.epoch, locked=[]))


async def price_offering(ctx: TickContext, being: EntityRow, _holder: EntityRow) -> None:
    profile = await outer_profile(ctx, being)
    if "fed" not in profile.locked:
        profile.fed += ctx.rules.outer_beings.offering_feed


PRICES: Mapping[OuterPrice, Callable[[TickContext, EntityRow, EntityRow], Awaitable[None]]] = total(
    OuterPrice,
    {
        OuterPrice.SANITY: price_sanity,
        OuterPrice.YEARS: price_years,
        OuterPrice.MEMORY: price_memory,
        OuterPrice.NAME: price_name,
        OuterPrice.SERVICE: price_service,
        OuterPrice.OFFERING: price_offering,
    },
)


async def strike_bargain(ctx: TickContext, being: EntityRow, holder: EntityRow, price: OuterPrice) -> OuterPactRow:
    profile = await outer_profile(ctx, being)
    power = PowerRow(
        holder_node_id=holder.id,
        technique=HUNGER_TECHNIQUE[profile.hunger],
        form=SpellForm.VOID,
        strength=ctx.rules.outer_beings.bargain_strength,
        origin=PowerOrigin.BONDED,
        state=PowerState.ACTIVE,
        granted_by_node_id=being.id,
        gained_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(power)
    await ctx.session.flush()
    row = OuterPactRow(outer_entity_id=being.id, holder_node_id=holder.id, price=price, paid=True, power_id=power.id, struck_epoch=ctx.epoch, locked=[])
    ctx.session.add(row)
    await pay_mortal_price(ctx, being, holder, price)
    await ctx.session.flush()
    return row


async def tempt(ctx: TickContext, being: EntityRow) -> int:
    struck = 0
    for cult in await cults_of(ctx, being.id):
        members = select(BondRow.source_node_id).where(BondRow.target_node_id == cult, BondRow.kind == BondKind.MEMBER_OF, BondRow.state == BondState.ACTIVE)
        for member_id in sorted(set(await ctx.session.scalars(members))):
            member = await ctx.session.get(EntityRow, member_id)
            if member is None or member.entity_type is not EntityType.MORTAL or member.status is not EntityStatus.CANON or held(member.id):
                continue
            known = await ctx.session.scalar(select(OuterPactRow.id).where(OuterPactRow.holder_node_id == member.id, OuterPactRow.outer_entity_id == being.id))
            rng = ctx.rng(f"outer.bargain.{being.id}.{member.id}.{ctx.epoch}")
            if known is not None or not rng.chance(ctx.rules.outer_beings.bargain_pct):
                continue
            await strike_bargain(ctx, being, member, rng.pick(list(OuterPrice)))
            struck += 1
    return struck


def relation_between(first: EntityRow, second: EntityRow, hungers: Mapping[int, OuterHunger]) -> OuterRelation:
    if stat_or(first, "size", 0) >= 2 * max(1, stat_or(second, "size", 0)):
        return OuterRelation.FEEDS_ON
    return OuterRelation.RIVAL if hungers.get(first.id) is hungers.get(second.id) else OuterRelation.IGNORE


async def relate(ctx: TickContext, beings: list[EntityRow]) -> int:
    table = ctx.rules.outer_beings
    hungers = {being.id: (await outer_profile(ctx, being)).hunger for being in beings}
    acted = 0
    for first in beings:
        for second in beings:
            if first.id == second.id or held(first.id, second.id):
                continue
            row = await ctx.session.get(OuterRelationRow, (first.id, second.id))
            if row is None:
                row = OuterRelationRow(outer_entity_id=first.id, other_entity_id=second.id, since_epoch=ctx.epoch, locked=[])
                ctx.session.add(row)
            if "relation" not in row.locked:
                row.relation = relation_between(first, second, hungers)
            acted += await RELATIONS[row.relation](ctx, first, second, table.devour_pct if row.relation is OuterRelation.FEEDS_ON else table.rival_setback)
    return acted


async def devour(ctx: TickContext, first: EntityRow, second: EntityRow, share: int) -> int:
    hunter, prey = await outer_profile(ctx, first), await outer_profile(ctx, second)
    taken = prey.fed * share // PERCENT
    if taken <= 0 or "fed" in prey.locked or "fed" in hunter.locked:
        return 0
    return int(move_amount(prey, hunter, "fed", taken))


async def thwart(ctx: TickContext, first: EntityRow, second: EntityRow, setback: int) -> int:
    mine, theirs = await active_plan(ctx, first.id), await active_plan(ctx, second.id)
    if mine is None or theirs is None or mine.goal is not theirs.goal or "progress" in theirs.locked:
        return 0
    theirs.progress = max(0, theirs.progress - setback)
    return 1


async def ignore(_ctx: TickContext, _first: EntityRow, _second: EntityRow, _amount: int) -> int:
    return 0


RELATIONS: Mapping[OuterRelation, Callable[[TickContext, EntityRow, EntityRow, int], Awaitable[int]]] = total(
    OuterRelation, {OuterRelation.FEEDS_ON: devour, OuterRelation.RIVAL: thwart, OuterRelation.IGNORE: ignore}
)


async def press_seals(ctx: TickContext, being: EntityRow, profile: OuterBeingProfileRow) -> None:
    table = ctx.rules.outer_beings
    seals = list(await ctx.session.scalars(select(OuterSealRow).where(OuterSealRow.outer_entity_id == being.id, OuterSealRow.broken_epoch.is_(None))))
    pressure = stat_or(being, "size", 0) // 2 + stat_or(being, "influence", 0) // 2
    standing: OuterSealRow | None = None
    for seal in seals:
        if "strength" not in seal.locked:
            seal.strength = max(0, seal.strength - table.seal_decay)
        if seal.strength < pressure and "strength" not in seal.locked:
            seal.broken_epoch = ctx.epoch
            await tell(ctx, being, "outer.seal_broken")
            continue
        standing = seal if standing is None or seal.kind is OuterSealKind.BANISH else standing
    if "fate" in profile.locked or profile.fate in {OuterFate.STARVED, OuterFate.DESTROYED}:
        return
    profile.fate = OuterFate.ACTIVE if standing is None else OuterFate.BANISHED if standing.kind is OuterSealKind.BANISH else OuterFate.SEALED
    if standing is not None and standing.kind is OuterSealKind.BANISH and "reach" not in profile.locked:
        profile.reach = 0


async def starve(ctx: TickContext, being: EntityRow, profile: OuterBeingProfileRow) -> bool:
    if profile.fate is not OuterFate.ACTIVE or profile.unfed_epochs < ctx.rules.outer_beings.starve_epochs or "fate" in profile.locked:
        return False
    if await worshippers_of(ctx, being.id) or await cults_of(ctx, being.id):
        return False
    await end_being(ctx, being, profile, OuterFate.STARVED)
    return True


async def end_being(ctx: TickContext, being: EntityRow, profile: OuterBeingProfileRow, fate: OuterFate) -> None:
    profile.fate = fate
    being.status, being.end_epoch = EntityStatus.DESTROYED, ctx.epoch
    for breach in list(await ctx.session.scalars(select(BreachPointRow).where(BreachPointRow.outer_entity_id == being.id))):
        await ctx.session.delete(breach)
    for incursion in list(
        await ctx.session.scalars(select(OuterIncursionRow).where(OuterIncursionRow.outer_entity_id == being.id, OuterIncursionRow.ended_epoch.is_(None)))
    ):
        incursion.stage, incursion.ended_epoch = IncursionStage.RECEDING, ctx.epoch
    await tell(ctx, being, "outer.ended", {"fate": fate, "told": "starved, unfed and forgotten" if fate is OuterFate.STARVED else "was destroyed"})


async def outer_agency(ctx: TickContext) -> int:
    beings = [being for being in await living_beings(ctx) if not held(being.id)]
    achieved = 0
    for being in beings:
        profile = await outer_profile(ctx, being)
        await press_seals(ctx, being, profile)
        if await starve(ctx, being, profile):
            continue
        achieved += await advance_plan(ctx, being, profile)
        if profile.fate is OuterFate.ACTIVE:
            ctx.count("outer_pacts", await tempt(ctx, being))
    ctx.count("incursions", await press_incursions(ctx))
    ctx.count("outer_relations", await relate(ctx, [being for being in beings if being.status is EntityStatus.CANON]))
    await ctx.session.flush()
    return achieved


async def seal_being(ctx: TickContext, being: EntityRow, sealer: int | None, kind: OuterSealKind, strength: int) -> OuterSealRow:
    row = OuterSealRow(outer_entity_id=being.id, sealer_node_id=sealer, kind=kind, strength=strength, sealed_epoch=ctx.epoch, locked=[])
    ctx.session.add(row)
    profile = await outer_profile(ctx, being)
    if "fate" not in profile.locked:
        profile.fate = OuterFate.BANISHED if kind is OuterSealKind.BANISH else OuterFate.SEALED
    if kind is OuterSealKind.BANISH:
        for breach in list(await ctx.session.scalars(select(BreachPointRow).where(BreachPointRow.outer_entity_id == being.id))):
            await ctx.session.delete(breach)
    await ctx.session.flush()
    return row
