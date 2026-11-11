from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.divine import GodGoalRow
from aerona.db.tables.dominion import GodDesignRow, ThroneRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import RelicRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.mythic import MantlingRow
from aerona.db.tables.polity import HouseMemberRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.warfare import WarRow
from aerona.db.write_guard import held
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.divine import GoalSource, GoalState, GodGoalKind
from aerona.domain.enums.entity import HERO_ROLES, EntityType
from aerona.domain.enums.foreign_god import ForeignGodStatus
from aerona.domain.enums.mind import ValueAxis, ValueHolder
from aerona.domain.enums.mythic import MantlingState
from aerona.domain.enums.son import SonStatus
from aerona.domain.enums.war import WarStatus
from aerona.engine.context import TickContext
from aerona.engine.divine.gods import God, alive, domains_of, faithful_communities, god_of, living_gods
from aerona.engine.divine.hooks import foes_of
from aerona.engine.dominion.sites import thrones_held
from aerona.engine.gods.progress import grant_progress, xp_for_next_level
from aerona.engine.mind.book import stored_values
from aerona.engine.notes import note
from aerona.engine.primitives.faith import worshipper_count
from aerona.engine.primitives.numbers import clamp_int

K = GodGoalKind
SON_ONLY = frozenset({K.FOUND_REALM, K.AWAKEN_GOD, K.DEFEAT_FOREIGN_GOD, K.RECONCILE, K.REBEL})
GOAL_LABELS = {
    K.BE_WORSHIPPED: "Be worshipped",
    K.FOUND_REALM: "Found a holy world",
    K.DESTROY_RIVAL: "Destroy a rival",
    K.SPREAD_DOMAIN: "Spread a domain",
    K.WIN_WAR: "Win a war",
    K.ACQUIRE_RELIC: "Acquire a relic",
    K.RAISE_HERO: "Raise a hero",
    K.AWAKEN_GOD: "Awaken a god",
    K.DEFEAT_FOREIGN_GOD: "Defeat a foreign god",
    K.RECONCILE: "Reconcile with the Creator",
    K.REBEL: "Rebel against the Creator",
    K.HOLD_THRONES: "Hold the thrones of power and ascend",
    K.PREVENT_MANTLING: "Keep a mortal from taking a god's place",
    K.SPONSOR_MANTLING: "Raise a chosen mortal to godhood",
}


@dataclass(frozen=True)
class Reading:
    progress: int
    state: GoalState = GoalState.ACTIVE


Check = Callable[[TickContext, God, GodGoalRow], Awaitable[Reading]]


def done_at(progress: float) -> Reading:
    value = clamp_int(progress, 0, PERCENT)
    return Reading(value, GoalState.DONE if value >= PERCENT else GoalState.ACTIVE)


async def worshipped(ctx: TickContext, god: God, goal: GodGoalRow) -> Reading:
    return done_at(await worshipper_count(ctx.session, god.id) * PERCENT / max(1, goal.amount))


async def realm(ctx: TickContext, god: God, goal: GodGoalRow) -> Reading:
    world = await ctx.session.get(WorldRow, goal.world_id) if goal.world_id is not None else None
    if world is None:
        return Reading(goal.progress, GoalState.FAILED)
    if world.patron_son_id == god.id:
        return Reading(PERCENT, GoalState.DONE)
    here = [community for community in await faithful_communities(ctx.session, god.id) if community.world_id == world.id]
    return done_at(len(here) * PERCENT / max(1, ctx.rules.pantheon.auto_holy_world_worshippers))


async def rival(ctx: TickContext, god: God, goal: GodGoalRow) -> Reading:
    target = await god_of(ctx.session, goal.target_node_id)
    if target is None or not alive(target):
        return Reading(PERCENT, GoalState.DONE)
    strength = target.existence if isinstance(target, SonRow) else target.power
    return Reading(clamp_int(PERCENT - strength, 0, PERCENT - 1))


async def spread(ctx: TickContext, god: God, goal: GodGoalRow) -> Reading:
    if goal.domain is None:
        return Reading(goal.progress, GoalState.FAILED)
    book = await ctx.divine()
    reached = 0
    for worshipper, gods in book.patrons.items():
        _, _, world_id = await book.place_of(ctx.session, worshipper)
        if goal.world_id is not None and world_id != goal.world_id:
            continue
        if any(goal.domain in book.gods[god_id].living_domains for god_id in gods if god_id in book.gods):
            reached += 1
    return done_at(reached * PERCENT / max(1, goal.amount))


async def war(ctx: TickContext, god: God, goal: GodGoalRow) -> Reading:
    ended = await ctx.session.scalars(
        select(WarRow).where(WarRow.status == WarStatus.ENDED, WarRow.ended_epoch >= goal.since_epoch, WarRow.loser_entity_id == goal.target_node_id)
    )
    faithful = {community.id for community in await faithful_communities(ctx.session, god.id)}
    if any(row.victor_entity_id in faithful for row in ended):
        return Reading(PERCENT, GoalState.DONE)
    lost = await ctx.session.scalar(
        select(WarRow.id).where(WarRow.status == WarStatus.ENDED, WarRow.ended_epoch >= goal.since_epoch, WarRow.victor_entity_id == goal.target_node_id)
    )
    return Reading(goal.progress, GoalState.FAILED if lost is not None else GoalState.ACTIVE)


async def relic(ctx: TickContext, god: God, goal: GodGoalRow) -> Reading:
    cults = [community.id for community in await faithful_communities(ctx.session, god.id)]
    found = await ctx.session.scalar(select(RelicRow.item_entity_id).where(RelicRow.cult_entity_id.in_(cults)).limit(1)) if cults else None
    return Reading(PERCENT, GoalState.DONE) if found is not None else Reading(goal.progress)


async def hero(ctx: TickContext, god: God, goal: GodGoalRow) -> Reading:
    members = select(HouseMemberRow.mortal_entity_id).where(HouseMemberRow.house_entity_id == goal.target_node_id)
    heroes = await ctx.session.scalars(select(EntityRow).where(EntityRow.id.in_(members), EntityRow.mortal_role.in_(list(HERO_ROLES))))
    book = await ctx.divine()
    for mortal in heroes:
        gods, _ = await book.faithful_of(ctx.session, mortal.id)
        if god.id in gods:
            return Reading(PERCENT, GoalState.DONE)
    return Reading(goal.progress)


async def awaken(ctx: TickContext, god: God, goal: GodGoalRow) -> Reading:
    target = await ctx.session.get(ForeignGodRow, goal.target_node_id) if goal.target_node_id is not None else None
    if target is None or target.status is ForeignGodStatus.DEAD:
        return Reading(goal.progress, GoalState.FAILED)
    if target.status is ForeignGodStatus.AWAKE:
        return Reading(PERCENT, GoalState.DONE)
    return Reading(clamp_int(target.awakening_pressure, 0, PERCENT - 1))


async def defeat(ctx: TickContext, god: God, goal: GodGoalRow) -> Reading:
    target = await ctx.session.get(ForeignGodRow, goal.target_node_id) if goal.target_node_id is not None else None
    if target is None or target.status in {ForeignGodStatus.DEFEATED, ForeignGodStatus.DEAD}:
        return Reading(PERCENT, GoalState.DONE)
    return Reading(clamp_int(PERCENT - target.power, 0, PERCENT - 1))


async def reconcile(ctx: TickContext, god: God, goal: GodGoalRow) -> Reading:
    if not isinstance(god, SonRow):
        return Reading(goal.progress, GoalState.FAILED)
    if not god.rebel and god.loyalty >= ctx.rules.son_goals.reconcile_loyalty:
        return Reading(PERCENT, GoalState.DONE)
    return Reading(clamp_int(god.loyalty * PERCENT / max(1, ctx.rules.son_goals.reconcile_loyalty), 0, PERCENT - 1))


async def rebel(ctx: TickContext, god: God, goal: GodGoalRow) -> Reading:
    if not isinstance(god, SonRow):
        return Reading(goal.progress, GoalState.FAILED)
    return Reading(PERCENT, GoalState.DONE) if god.rebel else Reading(clamp_int(PERCENT - god.loyalty, 0, PERCENT - 1))


async def thrones(ctx: TickContext, god: God, goal: GodGoalRow) -> Reading:
    held_worlds, wanted = await thrones_held(ctx, god.id)
    if held_worlds >= wanted:
        return Reading(PERCENT, GoalState.DONE)
    return Reading(clamp_int(held_worlds * PERCENT / wanted, 0, PERCENT - 1))


async def mantled(ctx: TickContext, goal: GodGoalRow) -> MantlingRow | None:
    return await ctx.session.get(MantlingRow, goal.target_node_id) if goal.target_node_id is not None else None


async def prevent(ctx: TickContext, god: God, goal: GodGoalRow) -> Reading:
    row = await mantled(ctx, goal)
    if row is None or row.state in {MantlingState.BLOCKED, MantlingState.FAILED}:
        return Reading(PERCENT, GoalState.DONE)
    if row.state in {MantlingState.ASCENDED, MantlingState.REPLACED}:
        return Reading(0, GoalState.FAILED)
    return Reading(clamp_int(PERCENT - row.progress, 0, PERCENT - 1))


async def sponsor(ctx: TickContext, god: God, goal: GodGoalRow) -> Reading:
    row = await mantled(ctx, goal)
    if row is not None and row.state in {MantlingState.ASCENDED, MantlingState.REPLACED}:
        return Reading(PERCENT, GoalState.DONE)
    if row is None or row.state in {MantlingState.BLOCKED, MantlingState.FAILED}:
        return Reading(0, GoalState.FAILED)
    return Reading(clamp_int(row.progress, 0, PERCENT - 1))


CHECKS: dict[GodGoalKind, Check] = {
    K.BE_WORSHIPPED: worshipped,
    K.FOUND_REALM: realm,
    K.DESTROY_RIVAL: rival,
    K.SPREAD_DOMAIN: spread,
    K.WIN_WAR: war,
    K.ACQUIRE_RELIC: relic,
    K.RAISE_HERO: hero,
    K.AWAKEN_GOD: awaken,
    K.DEFEAT_FOREIGN_GOD: defeat,
    K.RECONCILE: reconcile,
    K.REBEL: rebel,
    K.HOLD_THRONES: thrones,
    K.PREVENT_MANTLING: prevent,
    K.SPONSOR_MANTLING: sponsor,
}


async def active_goals(ctx: TickContext, god_id: int) -> list[GodGoalRow]:
    statement = select(GodGoalRow).where(GodGoalRow.god_node_id == god_id, GodGoalRow.state == GoalState.ACTIVE).order_by(GodGoalRow.id)
    return list(await ctx.session.scalars(statement))


def goal_text(god: God, goal: GodGoalRow, target: str | None) -> str:
    tail = f" ({target})" if target else ""
    return f"{god.name}: {GOAL_LABELS[goal.kind].lower()}{tail}"


async def target_name(ctx: TickContext, goal: GodGoalRow) -> str | None:
    if goal.target_node_id is not None:
        god = await god_of(ctx.session, goal.target_node_id)
        if god is not None:
            return god.name
        thing = await ctx.session.get(EntityRow, goal.target_node_id)
        if thing is not None:
            return thing.name
    if goal.world_id is not None:
        world = await ctx.session.get(WorldRow, goal.world_id)
        return world.name if world is not None else None
    return goal.domain.value if goal.domain is not None else None


async def close(ctx: TickContext, god: God, goal: GodGoalRow, state: GoalState) -> None:
    table = ctx.rules.son_goals
    goal.state, goal.closed_epoch = state, ctx.epoch
    if state is GoalState.DONE:
        goal.progress = PERCENT
        if goal.kind is K.HOLD_THRONES:
            await ascend(ctx, god)
        if isinstance(god, SonRow):
            await grant_progress(ctx, god, xp=table.done_xp, fame=table.done_fame)
            if goal.kind is K.REBEL:
                god.rebel = True
            if goal.kind is K.RECONCILE:
                god.rebel = False
        else:
            god.power = min(PERCENT, god.power + table.foreign_power)
    verb = "reached" if state is GoalState.DONE else "gave up"
    text = f"{goal_text(god, goal, await target_name(ctx, goal))} — {verb}."
    await note(ctx, text, key=f"divine.goal_{state.value}", son_id=god.id if isinstance(god, SonRow) else None, kind=ChronicleKind.ASCENSION)


async def ascend(ctx: TickContext, god: God) -> None:
    design = await ctx.session.get(GodDesignRow, god.id)
    if design is None or "rank" in design.locked:
        return
    design.rank += 1
    if isinstance(god, SonRow) and not held(god.id):
        need = sum(xp_for_next_level(ctx.rules, god.level + step) for step in range(ctx.rules.god_design.rank_levels)) - god.xp
        await grant_progress(ctx, god, xp=max(0, need), fame=0)
    await note(ctx, f"{god.name} ascended to a higher divine rank by the thrones it holds.", key="divine.ascended", ids=[god.id], kind=ChronicleKind.ASCENSION)


async def measure(ctx: TickContext, god: God, goal: GodGoalRow) -> None:
    reading = await CHECKS[goal.kind](ctx, god, goal)
    if "progress" not in goal.locked:
        goal.progress = reading.progress
    expired = ctx.epoch - goal.since_epoch >= ctx.rules.son_goals.max_epochs and goal.source is GoalSource.ENGINE
    if reading.state is not GoalState.ACTIVE and "state" not in goal.locked:
        await close(ctx, god, goal, reading.state)
    elif expired and "state" not in goal.locked:
        await close(ctx, god, goal, GoalState.FAILED)


async def rivals_of(ctx: TickContext, god: God) -> list[God]:
    mine = set(domains_of(god))
    return [other for other in await living_gods(ctx.session) if other.id != god.id and mine & set(domains_of(other))]


async def ascension_options(ctx: TickContext, god: God, ambition: float) -> list[tuple[GodGoalRow, float]]:
    weight = ctx.rules.son_goals.base_weight * (1 + ambition / PERCENT)
    found: list[tuple[GodGoalRow, float]] = []
    if await ctx.session.scalar(select(ThroneRow.id).limit(1)) is not None:
        found.append((GodGoalRow(kind=K.HOLD_THRONES), weight))
    design = await ctx.session.get(GodDesignRow, god.id)
    if isinstance(god, SonRow) and not god.rebel and design is not None and design.rank > 0:
        found.append((GodGoalRow(kind=K.REBEL), weight))
    for row in await ctx.session.scalars(select(MantlingRow).where(MantlingRow.state == MantlingState.WALKING).order_by(MantlingRow.mortal_entity_id)):
        kind = K.PREVENT_MANTLING if row.god_node_id == god.id else K.SPONSOR_MANTLING
        found.append((GodGoalRow(kind=kind, target_node_id=row.mortal_entity_id), weight * row.progress / PERCENT))
    return found


async def choose(ctx: TickContext, god: God) -> GodGoalRow | None:
    table = ctx.rules.son_goals
    rng = ctx.rng(f"goal.{god.id}")
    values = await stored_values(ctx.session, ValueHolder.DIVINE, god.id)
    ambition = god.ambition if isinstance(god, SonRow) else table.foreign_ambition
    mercy = god.mercy if isinstance(god, SonRow) else values.get(ValueAxis.MERCY, 0) + PERCENT // 2
    martial = max(0, values.get(ValueAxis.MARTIAL, 0))
    options: list[tuple[GodGoalRow, float]] = []
    count = await worshipper_count(ctx.session, god.id)
    options.append((GodGoalRow(kind=K.BE_WORSHIPPED, amount=count + table.worship_gain), float(table.base_weight)))
    for domain in domains_of(god):
        world_id = god.current_world_id if isinstance(god, SonRow) else god.world_id
        options.append(
            (GodGoalRow(kind=K.SPREAD_DOMAIN, domain=domain, world_id=world_id, amount=table.spread_amount), table.base_weight * (1 + ambition / PERCENT))
        )
    for other in await rivals_of(ctx, god):
        options.append((GodGoalRow(kind=K.DESTROY_RIVAL, target_node_id=other.id), max(0.0, ambition - mercy) * table.rival_weight_pct / PERCENT))
    for community in (await faithful_communities(ctx.session, god.id))[: table.scan_limit]:
        for foe in sorted(await foes_of(ctx, community.id))[:1]:
            options.append((GodGoalRow(kind=K.WIN_WAR, target_node_id=foe), table.base_weight * (1 + martial / PERCENT)))
    houses = select(HouseMemberRow.house_entity_id).join(EntityRow, EntityRow.id == HouseMemberRow.mortal_entity_id)
    house = await ctx.session.scalar(houses.where(EntityRow.world_id == (god.current_world_id if isinstance(god, SonRow) else god.world_id)).limit(1))
    if house is not None:
        options.append((GodGoalRow(kind=K.RAISE_HERO, target_node_id=house), table.base_weight * (1 + max(0, mercy) / PERCENT)))
    options.append((GodGoalRow(kind=K.ACQUIRE_RELIC), table.base_weight / 2))
    options.extend(await ascension_options(ctx, god, ambition))
    if isinstance(god, SonRow):
        world = await ctx.session.get(WorldRow, god.current_world_id) if god.current_world_id is not None else None
        if world is not None and world.patron_son_id != god.id:
            options.append((GodGoalRow(kind=K.FOUND_REALM, world_id=world.id), table.base_weight * (1 + ambition / PERCENT)))
        for foreign in await ctx.session.scalars(select(ForeignGodRow).where(ForeignGodRow.status == ForeignGodStatus.ASLEEP).limit(1)):
            options.append((GodGoalRow(kind=K.AWAKEN_GOD, target_node_id=foreign.id), table.base_weight / 2))
        for foreign in await ctx.session.scalars(
            select(ForeignGodRow).where(ForeignGodRow.status == ForeignGodStatus.AWAKE, ForeignGodRow.stance < 0).limit(1)
        ):
            options.append((GodGoalRow(kind=K.DEFEAT_FOREIGN_GOD, target_node_id=foreign.id), table.base_weight * (1 + martial / PERCENT)))
        if god.rebel or god.loyalty < table.reconcile_loyalty:
            options.append((GodGoalRow(kind=K.RECONCILE), table.base_weight * (1 + max(0, mercy) / PERCENT)))
        if not god.rebel and god.loyalty < table.rebel_loyalty:
            options.append((GodGoalRow(kind=K.REBEL), max(0.0, ambition - god.loyalty) * table.rival_weight_pct / PERCENT))
    weighted = [(row, weight) for row, weight in options if weight > 0]
    if not weighted:
        return None
    chosen = rng.weighted([row for row, _ in weighted], [weight for _, weight in weighted])
    chosen.god_node_id, chosen.since_epoch, chosen.source, chosen.locked = god.id, ctx.epoch, GoalSource.ENGINE, []
    return chosen


async def attend(ctx: TickContext, son: SonRow, goal: GodGoalRow) -> bool:
    table = ctx.rules.son_goals
    if goal.world_id is None or son.current_world_id == goal.world_id or son.status is not SonStatus.ACTIVE:
        return False
    if son.manually_assigned_epoch is not None and ctx.epoch - son.manually_assigned_epoch < table.manual_attention_epochs:
        return False
    if not ctx.rng(f"attend.{son.id}").chance(table.attention_drift_chance):
        return False
    son.current_world_id = goal.world_id
    return True


async def pursue_goals(ctx: TickContext) -> int:
    table = ctx.rules.son_goals
    moved = 0
    for god in await living_gods(ctx.session):
        if held(god.id):
            continue
        goals = await active_goals(ctx, god.id)
        for goal in goals:
            await measure(ctx, god, goal)
        current = [goal for goal in goals if goal.state is GoalState.ACTIVE]
        if not current and ctx.rng(f"goal_new.{god.id}").chance(table.choose_chance):
            chosen = await choose(ctx, god)
            if chosen is not None:
                ctx.session.add(chosen)
                current.append(chosen)
                await note(
                    ctx,
                    f"{goal_text(god, chosen, await target_name(ctx, chosen))} — a new aim.",
                    key="divine.goal_set",
                    son_id=god.id if isinstance(god, SonRow) else None,
                    kind=ChronicleKind.ASCENSION,
                )
        if isinstance(god, SonRow):
            for goal in current:
                moved += 1 if await attend(ctx, god, goal) else 0
    await ctx.session.flush()
    return moved


TARGET_TYPES = {K.WIN_WAR: (EntityType.PEOPLE, EntityType.SETTLEMENT, EntityType.POLITY), K.RAISE_HERO: (EntityType.HOUSE,)}
