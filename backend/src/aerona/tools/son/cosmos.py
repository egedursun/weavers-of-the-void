from enum import StrEnum
from typing import Annotated, Any

from pydantic import Field
from sqlalchemy import select

from aerona.catalog.gates import Gate
from aerona.catalog.weather import WEATHER
from aerona.constants.tool_inputs import (
    INSPIRATION_MAX,
    INSPIRATION_MIN,
    NAME_MAX,
    NAME_MIN,
    REASON_MAX,
    REASON_MIN,
    SHORT_DESCRIPTION_MAX,
    SHORT_DESCRIPTION_MIN,
)
from aerona.db.repositories.names import NameRepository
from aerona.db.repositories.worlds import WorldRepository
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import LeyLineRow
from aerona.db.tables.routes import RouteRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind, PendingJobKind, TurnCounter
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.environment import WeatherKind
from aerona.domain.enums.foreign_god import ForeignGodPowerEffect, ForeignGodStatus
from aerona.domain.enums.limits import RELATION_MAX, RELATION_MIN
from aerona.domain.enums.son import SonStatus, Stat
from aerona.domain.enums.world import EXTINGUISHED_STAR_TYPES, Discovery, StarType, WorldType
from aerona.engine.cosmos.actions import bargain_with_outer, seal_gate
from aerona.engine.cosmos.foreign_gods import powers_of, stat_effect
from aerona.engine.cosmos.stars import extinguish_star, hang_star, rekindle_star
from aerona.engine.cosmos.worlds import declare_holy_world
from aerona.engine.environment.control import force_weather, reorder_seasons, sever_ley, world_seasons
from aerona.engine.phases.afterlife import soul_bind
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import CommonResult, SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.ports import BornWorld, WorldBirth, WorldBirthOrder
from aerona.tools.framework.spec import LongJob, ToolMeta, ToolOutcome, ToolSpec, gate, no_cost, son_standard_action
from aerona.tools.framework.validation import fail, state_reason
from aerona.tools.son import lines
from aerona.tools.son.support import ensure_in_reach, grant, require_essence, share, shift_relation
from aerona.tools.son.war import known_god

PERCENT = 100
SEASON_DOMAINS = frozenset({Domain.SKY, Domain.STORM, Domain.TIME, Domain.SUN, Domain.MOON, Domain.HARVEST, Domain.ICE, Domain.PLANTS})
INHABITANTS = (EntityType.PEOPLE, EntityType.SETTLEMENT)
BINDABLE = frozenset({EntityType.ITEM, EntityType.VESSEL, EntityType.STRUCTURE})


class TalkIntent(StrEnum):
    ALLIANCE = "alliance"
    THREAT = "threat"
    BARGAIN = "bargain"


class SeverLeyInput(ToolInput):
    line_id: int
    reason: Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class ReorderSeasonsInput(ToolInput):
    world_id: int
    order: list[int] = Field(min_length=1)


class ShapeWeatherInput(ToolInput):
    region_id: int
    weather: WeatherKind
    epochs: int = Field(default=1, ge=1)
    reason: Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class WorldInput(ToolInput):
    world_id: int


class SealInput(ToolInput):
    route_id: int
    reason: Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class StarInput(ToolInput):
    star_id: int


class BindSpiritInput(ToolInput):
    spirit_id: int
    target_id: int


class HangStarInput(ToolInput):
    name: Annotated[str, Field(min_length=NAME_MIN, max_length=NAME_MAX)]
    type: StarType | None = None
    description: Annotated[str, Field(min_length=SHORT_DESCRIPTION_MIN, max_length=SHORT_DESCRIPTION_MAX)]


class ExtinguishInput(ToolInput):
    star_id: int
    reason: Annotated[str, Field(min_length=REASON_MIN + 5, max_length=REASON_MAX)]


class TalkInput(ToolInput):
    god_id: int
    intent: TalkIntent
    words: Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class LeakSealInput(ToolInput):
    how: Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class OuterBargainInput(ToolInput):
    outsider_id: int
    request: Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


class BirthWorldInput(ToolInput):
    inspiration: Annotated[str, Field(min_length=INSPIRATION_MIN, max_length=INSPIRATION_MAX)]
    type: WorldType | None = None
    star_id: int | None = None
    parent_world_id: int | None = None
    new_star: bool = False


async def _world(call: SonCall, world_id: int) -> WorldRow:
    world = await call.session.get(WorldRow, world_id)
    if world is None:
        fail(SonResult.NO_SUCH_WORLD)
    return world


async def move_to_world(call: SonCall, args: WorldInput) -> str:
    target = await _world(call, args.world_id)
    if target.discovery is Discovery.UNKNOWN:
        fail(SonResult.WORLD_UNKNOWN, name=target.name)
    if target.discovery is Discovery.FORGOTTEN:
        fail(SonResult.WORLD_FORGOTTEN, name=target.name)
    if target.id == call.world_id:
        fail(SonResult.ALREADY_THERE, name=target.name)
    current = await call.session.get(WorldRow, call.world_id) if call.world_id is not None else None
    if current is not None:
        others = await call.session.scalar(
            select(SonRow.id).where(SonRow.current_world_id == current.id, SonRow.status == SonStatus.ACTIVE, SonRow.id != call.son.id).limit(1)
        )
        inhabited = await call.session.scalar(
            select(EntityRow.id)
            .where(EntityRow.world_id == current.id, EntityRow.status == EntityStatus.CANON, EntityRow.entity_type.in_(INHABITANTS))
            .limit(1)
        )
        if others is None and inhabited is not None:
            fail(SonResult.SOLE_GOD, name=current.name)
    call.son.current_world_id = target.id
    call.target(target.id)
    await call.chronicle(ChronicleKind.COSMIC, lines.MOVE, world_id=target.id, son=call.son.name, old=current.name if current else "", new=target.name)
    return result(SonResult.MOVED, name=target.name)


async def sever_ley_line(call: SonCall, args: SeverLeyInput) -> str:
    line = await call.session.get(LeyLineRow, args.line_id)
    if line is None:
        fail(SonResult.NO_SUCH_LEY, id=args.line_id)
    if call.world_id != line.world_id and not await call.reachable_world(line.world_id):
        fail(SonResult.LEY_OUT_OF_REACH)
    cost = call.rules.son_tools.sever_ley_essence
    require_essence(call, cost)
    first, second = await call.session.get(EntityRow, line.region_a_id), await call.session.get(EntityRow, line.region_b_id)
    epochs = call.rules.environment.sever_ley_epochs
    call.target(line.region_a_id)
    await sever_ley(call.session, line.id, until_epoch=call.tick.epoch + epochs - 1, son_id=call.son.id)
    call.spend_essence(cost)
    names = (first.name if first is not None else "", second.name if second is not None else "")
    ids = [line.region_a_id, line.region_b_id]
    await call.chronicle(
        ChronicleKind.COSMIC, lines.SEVER_LEY, entity_ids=ids, world_id=line.world_id, son=call.son.name, first=names[0], second=names[1], reason=args.reason
    )
    return result(SonResult.LEY_SEVERED, first=names[0], second=names[1], epochs=epochs)


async def reorder_world_seasons(call: SonCall, args: ReorderSeasonsInput) -> str:
    tools = call.rules.son_tools
    if not {call.son.domain_primary, call.son.domain_secondary} & SEASON_DOMAINS:
        fail(SonResult.SEASONS_NOT_YOURS)
    await call.within_limit(TurnCounter.SEASON_ORDER, tools.reorder_seasons_per_epoch, "son_tools.reorder_seasons_per_epoch", SonResult.SEASONS_LIMIT)
    world = await _world(call, args.world_id)
    if call.world_id != world.id and not await call.reachable_world(world.id):
        fail(SonResult.SEASONS_OUT_OF_REACH, name=world.name)
    require_essence(call, tools.reorder_seasons_essence)
    current = await world_seasons(call.session, world.id)
    if sorted(args.order) != [season.position for season in current]:
        fail(SonResult.SEASONS_INVALID, name=world.name, seasons=", ".join(f"{season.position}: {season.name}" for season in current))
    call.target(world.id)
    seasons = await reorder_seasons(call.session, world.id, args.order)
    order = ", ".join(season.name for season in seasons)
    call.spend_essence(tools.reorder_seasons_essence)
    await call.bump(TurnCounter.SEASON_ORDER)
    await call.chronicle(ChronicleKind.COSMIC, lines.REORDER_SEASONS, world_id=world.id, son=call.son.name, world=world.name, order=order)
    return result(SonResult.SEASONS_REORDERED, name=world.name, order=order)


async def shape_weather(call: SonCall, args: ShapeWeatherInput) -> str:
    tools = call.rules.son_tools
    if not {call.son.domain_primary, call.son.domain_secondary} & SEASON_DOMAINS:
        fail(SonResult.SEASONS_NOT_YOURS)
    await call.within_limit(TurnCounter.WEATHER_SHAPING, tools.shape_weather_per_epoch, "son_tools.shape_weather_per_epoch", SonResult.WEATHER_LIMIT)
    region = await call.session.get(EntityRow, args.region_id)
    if region is None or region.entity_type is not EntityType.REGION:
        fail(SonResult.WEATHER_NOT_REGION, name=region.name if region is not None else str(args.region_id))
    if call.world_id != region.world_id and not await call.reachable_world(region.world_id):
        fail(SonResult.SEASONS_OUT_OF_REACH, name=region.name)
    epochs = min(args.epochs, tools.shape_weather_max_epochs)
    cost = tools.shape_weather_essence * epochs
    require_essence(call, cost)
    call.target(region.id)
    await force_weather(call.session, region, args.weather, from_epoch=call.tick.epoch, epochs=epochs, season_position=None, son_id=call.son.id)
    call.spend_essence(cost)
    await call.bump(TurnCounter.WEATHER_SHAPING)
    label = WEATHER[args.weather].label
    await call.chronicle(
        ChronicleKind.COSMIC,
        lines.SHAPE_WEATHER,
        entity_ids=[region.id],
        world_id=region.world_id,
        son=call.son.name,
        weather=label.lower(),
        region=region.name,
        epochs=epochs,
        reason=args.reason,
    )
    return result(SonResult.WEATHER_SHAPED, weather=label, name=region.name, epochs=epochs)


async def declare_holy(call: SonCall, args: WorldInput) -> str:
    tools = call.rules.son_tools
    await call.within_limit(TurnCounter.HOLY_WORLD, tools.holy_world_per_epoch, "son_tools.holy_world_per_epoch", SonResult.HOLY_LIMIT)
    world = await _world(call, args.world_id)
    if world.discovery is Discovery.UNKNOWN:
        fail(SonResult.HOLY_UNKNOWN, name=world.name)
    if world.discovery is Discovery.FORGOTTEN:
        fail(SonResult.HOLY_FORGOTTEN, name=world.name)
    call.target(world.id)
    await declare_holy_world(call.tick, call.son, world)
    await call.bump(TurnCounter.HOLY_WORLD)
    return result(SonResult.HOLY_DECLARED)


async def seal(call: SonCall, args: SealInput) -> str:
    cost = share(call.rules.cosmic_costs.seal_gate, call.rules.son_tools.cosmic_seal_pct)
    require_essence(call, cost)
    route = await call.session.get(RouteRow, args.route_id)
    if route is not None and not (await call.reachable_world(route.world_a_id) or await call.reachable_world(route.world_b_id)):
        fail(SonResult.ROUTE_OUT_OF_REACH, id=route.id)
    await seal_gate(call.tick, args.route_id, call.son.name)
    call.spend_essence(cost)
    return result(SonResult.GATE_SEALED, reason=args.reason)


async def rekindle(call: SonCall, args: StarInput) -> str:
    cost = share(call.rules.cosmic_costs.rekindle_dead_star, call.rules.son_tools.cosmic_rekindle_pct)
    require_essence(call, cost)
    await _star(call, args.star_id)
    await rekindle_star(call.tick, args.star_id, call.son.name)
    call.spend_essence(cost)
    call.son.fame += call.rules.son_tools.rekindle_star_renown
    call.target(args.star_id)
    return result(SonResult.STAR_REKINDLED)


async def _free_spirit(call: SonCall, spirit_id: int) -> EntityRow:
    spirit = await call.session.get(EntityRow, spirit_id)
    if spirit is not None and spirit.entity_type is EntityType.SPIRIT and spirit.status is not EntityStatus.CANON:
        fail(SonResult.SPIRIT_NOT_FREE, id=spirit.id, name=spirit.name)
    if spirit is None or spirit.entity_type is not EntityType.SPIRIT:
        fail(SonResult.NO_FREE_SPIRIT)
    return spirit


async def bind_spirit(call: SonCall, args: BindSpiritInput) -> str:
    cost = share(call.rules.cosmic_costs.spirit_cloak, call.rules.son_tools.cosmic_spirit_cloak_pct)
    require_essence(call, cost)
    spirit = await _free_spirit(call, args.spirit_id)
    target = await call.session.get(EntityRow, args.target_id)
    if target is None:
        fail(CommonResult.NO_SUCH_ENTITY, id=args.target_id)
    if target.status is not EntityStatus.CANON:
        fail(SonResult.SPIRIT_TARGET_STATE, reason=state_reason(target, target.id))
    await ensure_in_reach(call, spirit)
    await ensure_in_reach(call, target)
    bound = await soul_bind(call.tick, spirit.id, target.id, call.son.name, call.son.id)
    call.spend_essence(cost)
    call.target(target.id)
    golem = bound.id if bound.id != target.id else None
    if golem is not None:
        call.remember_creation(golem)
    return result(SonResult.SPIRIT_BOUND, golem=golem)


async def hang(call: SonCall, args: HangStarInput) -> str:
    cost = share(call.rules.cosmic_costs.ignite_star, call.rules.son_tools.cosmic_hang_star_pct)
    require_essence(call, cost)
    name = " ".join(args.name.split())
    if await NameRepository(call.session).is_taken(name):
        fail(SonResult.NAME_IN_USE)
    star = await hang_star(call.tick, name, args.type or StarType.YELLOW_DWARF, call.son.name, args.description)
    call.spend_essence(cost)
    call.target(star.id)
    return result(SonResult.STAR_HUNG, id=star.id, name=star.name)


async def _star(call: SonCall, star_id: int) -> StarRow:
    star = await call.session.get(StarRow, star_id)
    if star is None:
        fail(SonResult.NO_SUCH_STAR)
    return star


async def extinguish(call: SonCall, args: ExtinguishInput) -> str:
    tools = call.rules.son_tools
    star = await _star(call, args.star_id)
    if star.star_type in EXTINGUISHED_STAR_TYPES:
        fail(SonResult.STAR_ALREADY_DEAD, name=star.name)
    cost = share(call.rules.cosmic_costs.ignite_star, tools.cosmic_extinguish_pct)
    require_essence(call, cost)
    await extinguish_star(call.tick, star.id, call.son.name)
    call.spend_essence(cost)
    call.son.fame += tools.extinguish_star_renown
    for sibling in await call.session.scalars(select(SonRow).where(SonRow.id != call.son.id)):
        await shift_relation(call, sibling.id, -tools.extinguish_star_relation)
    call.target(star.id)
    return result(SonResult.STAR_EXTINGUISHED, reason=args.reason)


async def talk_to_foreign_god(call: SonCall, args: TalkInput) -> str:
    tools = call.rules.son_tools
    god = await known_god(call, args.god_id)
    if god.status is not ForeignGodStatus.AWAKE:
        fail(SonResult.GOD_CANNOT_SPEAK, name=god.name, state=god.status.value)
    if await call.target_uses(ActionKind.FOREIGN_GOD_TALK, god.id) >= tools.foreign_talk_per_god:
        fail(SonResult.TALK_LIMIT, name=god.name, cap=tools.foreign_talk_per_god)
    if call.world_id is not None and not await WorldRepository(call.session).connected(call.world_id, god.world_id):
        fail(SonResult.VOICE_OUT_OF_REACH, name=god.name)
    me = call.son
    powers = await powers_of(call.session, god.id)
    leaning = (
        (me.strength - god.power) / tools.foreign_threat_strength_divisor if args.intent is TalkIntent.THREAT else god.stance / tools.foreign_attitude_divisor
    )
    resist = stat_effect(call.rules, god, Stat.WILL, call.rules.foreign_gods.talk_will)
    sharp = call.rules.foreign_gods.power_sharp_tongue if ForeignGodPowerEffect.SHARP_TONGUED in powers else 0
    roll = call.die(PERCENT, "talk") + me.charisma / tools.foreign_talk_charisma_divisor + leaning - resist - sharp
    gained = 0
    if args.intent is TalkIntent.ALLIANCE:
        won = roll >= tools.foreign_alliance_threshold
        god.stance += tools.foreign_alliance_attitude if won else -tools.foreign_reject_attitude
    elif args.intent is TalkIntent.THREAT:
        won = roll >= tools.foreign_threat_threshold
        god.stance -= tools.foreign_threat_attitude if won else tools.foreign_threat_fail_attitude
        if won:
            god.power = max(0, god.power - tools.foreign_threat_strength)
    else:
        won = roll >= tools.foreign_bargain_threshold
        god.stance += tools.foreign_bargain_attitude if won else -tools.foreign_reject_attitude
        gained = call.gain_essence(tools.foreign_bargain_essence) if won else 0
    god.stance = max(RELATION_MIN, min(RELATION_MAX, god.stance))
    outcome = lines.TALK_OUTCOMES[(args.intent.value, won)].format(god=god.name, gain=gained)
    call.target(god.id)
    await call.chronicle(
        ChronicleKind.FOREIGN_GOD,
        lines.FOREIGN_TALK,
        world_id=god.world_id,
        son=me.name,
        god=god.name,
        manner=lines.TALK_MANNERS[args.intent.value],
        words=args.words,
        outcome=outcome,
    )
    return result(SonResult.TALKED, outcome=outcome[:1].upper() + outcome[1:])


async def seal_leak(call: SonCall, args: LeakSealInput) -> str:
    tools = call.rules.son_tools
    await call.within_limit(TurnCounter.LEAK_STITCHED, tools.seal_per_epoch, "son_tools.seal_per_epoch", SonResult.STITCH_LIMIT)
    world = await call.session.get(WorldRow, call.world_id) if call.world_id is not None else None
    if world is None:
        fail(SonResult.WORLD_UNREGISTERED)
    if world.leakage <= 0:
        fail(SonResult.NO_TEAR, name=world.name)
    require_essence(call, tools.seal_cost)
    old = world.leakage
    world.leakage = max(0, old - tools.seal_leak_reduction)
    call.spend_essence(tools.seal_cost)
    call.target(world.id)
    await call.bump(TurnCounter.LEAK_STITCHED)
    await call.chronicle(ChronicleKind.COSMIC, lines.STITCH, world_id=world.id, son=call.son.name, world=world.name, how=args.how, old=old, new=world.leakage)
    return result(SonResult.STITCHED, old=old, new=world.leakage)


async def bargain_with_outsider(call: SonCall, args: OuterBargainInput) -> str:
    if call.son.outer_bargain_forbidden:
        fail(SonResult.OUTER_FORBIDDEN)
    cap = call.rules.son_tools.outer_bargain_per_epoch
    await call.within_limit(TurnCounter.OUTER_BARGAIN, cap, "son_tools.outer_bargain_per_epoch", SonResult.OUTER_LIMIT)
    gain = await bargain_with_outer(call.tick, call.son.id, args.outsider_id, args.request)
    call.target(args.outsider_id)
    await call.bump(TurnCounter.OUTER_BARGAIN)
    return result(SonResult.OUTER_BARGAINED, gain=gain)


async def _birth_place(call: SonCall, args: BirthWorldInput) -> None:
    chosen = [args.star_id is not None, args.parent_world_id is not None, args.new_star]
    if args.star_id is not None and await call.session.get(StarRow, args.star_id) is None:
        fail(SonResult.NO_SUCH_STAR_ID, id=args.star_id)
    if args.parent_world_id is not None and await call.session.get(WorldRow, args.parent_world_id) is None:
        fail(SonResult.NO_SUCH_WORLD_ID, id=args.parent_world_id)
    if sum(chosen) > 1:
        fail(SonResult.ONE_PLACE_ONLY)


async def birth_world(call: SonCall, args: BirthWorldInput) -> ToolOutcome:
    port = call.ports.world_birth
    tools = call.rules.son_tools
    cost = call.rules.balance.birth_world
    await _birth_place(call, args)
    require_essence(call, cost)
    if port is None:
        fail(SonResult.WORLD_BIRTH_FAILED)
    birth: WorldBirth = port
    order = WorldBirthOrder(call.son.id, args.inspiration, args.type, args.star_id, args.parent_world_id, args.new_star)
    call.spend_essence(cost)
    call.charge_actions(tools.birth_world_ap)

    async def run() -> BornWorld:
        return await birth.birth_world(order)

    async def finish(after: SonCall, world: BornWorld) -> str:
        level = await grant(after, after.son, tools.birth_world_xp, tools.birth_world_renown)
        after.target(world.world_id)
        return result(SonResult.WORLD_BORN, id=world.world_id, name=world.name, type=world.type_label, level=level)

    return LongJob(
        PendingJobKind.WORLD_BIRTH, cost, tools.birth_world_ap, result(SonResult.WORLD_BIRTH_FAILED), run, finish, lambda world: f"world#{world.world_id}"
    )


def specs() -> list[ToolSpec[SonCall, Any]]:
    son = AgentKind.SON
    star_gate = gate(Gate.HANG_EXTINGUISH_STAR)
    return [
        ToolSpec(SonToolId.MOVE_TO_WORLD, son, WorldInput, ToolMeta(ActionKind.MOVE_TO_WORLD, no_cost), move_to_world),
        ToolSpec(
            SonToolId.SEVER_LEY,
            son,
            SeverLeyInput,
            ToolMeta(
                ActionKind.SEVER_LEY,
                son_standard_action,
                essence_cost=lambda rules: rules.son_tools.sever_ley_essence,
                rarity_gate=gate(Gate.RARE_TOOLS),
            ),
            sever_ley_line,
        ),
        ToolSpec(
            SonToolId.REORDER_SEASONS,
            son,
            ReorderSeasonsInput,
            ToolMeta(
                ActionKind.REORDER_SEASONS,
                lambda rules: rules.son_tools.reorder_seasons_ap,
                essence_cost=lambda rules: rules.son_tools.reorder_seasons_essence,
                rarity_gate=gate(Gate.RARE_TOOLS),
            ),
            reorder_world_seasons,
        ),
        ToolSpec(
            SonToolId.SHAPE_WEATHER,
            son,
            ShapeWeatherInput,
            ToolMeta(
                ActionKind.SHAPE_WEATHER,
                lambda rules: rules.son_tools.shape_weather_ap,
                essence_cost=lambda rules: rules.son_tools.shape_weather_essence,
                rarity_gate=gate(Gate.RARE_TOOLS),
            ),
            shape_weather,
        ),
        ToolSpec(SonToolId.DECLARE_HOLY_WORLD, son, WorldInput, ToolMeta(ActionKind.HOLY_WORLD, no_cost, rarity_gate=gate(Gate.HOLY_WORLD)), declare_holy),
        ToolSpec(
            SonToolId.SEAL_GATE,
            son,
            SealInput,
            ToolMeta(
                ActionKind.SEAL_GATE,
                son_standard_action,
                essence_cost=lambda rules: share(rules.cosmic_costs.seal_gate, rules.son_tools.cosmic_seal_pct),
                rarity_gate=gate(Gate.SEAL_GATE),
            ),
            seal,
        ),
        ToolSpec(
            SonToolId.REKINDLE_STAR,
            son,
            StarInput,
            ToolMeta(
                ActionKind.REKINDLE_STAR,
                lambda rules: rules.son_tools.rekindle_star_ap,
                essence_cost=lambda rules: share(rules.cosmic_costs.rekindle_dead_star, rules.son_tools.cosmic_rekindle_pct),
                rarity_gate=gate(Gate.REKINDLE_STAR),
            ),
            rekindle,
        ),
        ToolSpec(
            SonToolId.BIND_SPIRIT,
            son,
            BindSpiritInput,
            ToolMeta(
                ActionKind.SPIRIT_CLOAK,
                son_standard_action,
                essence_cost=lambda rules: share(rules.cosmic_costs.spirit_cloak, rules.son_tools.cosmic_spirit_cloak_pct),
                rarity_gate=gate(Gate.SPIRIT_CLOAK),
            ),
            bind_spirit,
        ),
        ToolSpec(
            SonToolId.HANG_STAR,
            son,
            HangStarInput,
            ToolMeta(
                ActionKind.HANG_STAR,
                lambda rules: rules.son_tools.hang_star_ap,
                essence_cost=lambda rules: share(rules.cosmic_costs.ignite_star, rules.son_tools.cosmic_hang_star_pct),
                rarity_gate=star_gate,
            ),
            hang,
        ),
        ToolSpec(
            SonToolId.EXTINGUISH_STAR,
            son,
            ExtinguishInput,
            ToolMeta(
                ActionKind.EXTINGUISH_STAR,
                lambda rules: rules.son_tools.extinguish_star_ap,
                essence_cost=lambda rules: share(rules.cosmic_costs.ignite_star, rules.son_tools.cosmic_extinguish_pct),
                rarity_gate=star_gate,
            ),
            extinguish,
        ),
        ToolSpec(SonToolId.TALK_TO_FOREIGN_GOD, son, TalkInput, ToolMeta(ActionKind.FOREIGN_GOD_TALK, son_standard_action), talk_to_foreign_god),
        ToolSpec(
            SonToolId.SEAL_LEAK,
            son,
            LeakSealInput,
            ToolMeta(
                ActionKind.STITCH_LEAK,
                lambda rules: rules.son_tools.seal_ap,
                essence_cost=lambda rules: rules.son_tools.seal_cost,
                rarity_gate=gate(Gate.SEAL_LEAK),
            ),
            seal_leak,
        ),
        ToolSpec(SonToolId.BARGAIN_WITH_OUTSIDER, son, OuterBargainInput, ToolMeta(ActionKind.OUTER_BARGAIN, no_cost), bargain_with_outsider),
        ToolSpec(
            SonToolId.BIRTH_WORLD,
            son,
            BirthWorldInput,
            ToolMeta(
                ActionKind.BIRTH_WORLD,
                lambda rules: rules.son_tools.birth_world_ap,
                essence_cost=lambda rules: rules.balance.birth_world,
                rarity_gate=gate(Gate.BIRTH_WORLD),
                long_job=PendingJobKind.WORLD_BIRTH,
            ),
            birth_world,
            frozenset({"world_birth"}),
        ),
    ]
