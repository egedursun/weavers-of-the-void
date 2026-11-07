from enum import StrEnum

from sqlalchemy import delete, func, or_, select

from aerona.constants.player import ORBIT_MOON_BASE, ORBIT_MOON_STEP, ORBIT_PLANET_BASE, ORBIT_PLANET_STEP, STAR_NAME_MIN_LENGTH
from aerona.core.errors import ValidationFailedError
from aerona.db.repositories.bonds import BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.repositories.names import NameRepository, normalize_name
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind, LegendaryQuestKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.travel import TravelMethod
from aerona.domain.enums.world import EXTINGUISHED_STAR_TYPES, ClimateEra, Discovery, SkyEventKind, StarType
from aerona.domain.models.profiles import TravelResource
from aerona.engine.cosmos.actions import cleanse_leak as engine_cleanse_leak
from aerona.engine.cosmos.actions import seal_gate as engine_seal_gate
from aerona.engine.cosmos.quests import open_quest
from aerona.engine.cosmos.resources import define_cosmic_resource
from aerona.engine.cosmos.routes import RouteSpec, reveal_hidden_route, sever_route, stitch_route
from aerona.engine.cosmos.routes import open_route as engine_open_route
from aerona.engine.cosmos.routes import recall_journey as engine_recall_journey
from aerona.engine.cosmos.stars import extinguish_star
from aerona.engine.cosmos.stars import hang_star as engine_hang_star
from aerona.engine.cosmos.stars import rekindle_star as engine_rekindle_star
from aerona.engine.cosmos.worlds import align_moons, forget_world
from aerona.engine.phases.afterlife import pardon as engine_pardon
from aerona.engine.phases.afterlife import soul_bind
from aerona.engine.phases.climate import impose_climate
from aerona.engine.phases.sky import SkyOrder, sky_event
from aerona.engine.primitives.naming import Namer, seed_of
from aerona.engine.primitives.numbers import ordinal
from aerona.language.generator import NameKind
from aerona.services.gods import cosmic_economy
from aerona.services.player import guards
from aerona.services.player.chronicle import hand, tell
from aerona.services.player.lines import (
    CLIMATE_COMMANDED,
    DEPOSIT_OPENED,
    EXILED_ENTITY,
    HOSTILITY_SEVERED,
    RESOURCE_DEFINED,
    ROUTE_OPENED,
    STAR_EDITED,
    STAR_REMOVED,
    WORLD_RESHAPED,
)
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

EXILE_TYPES = frozenset(COMMUNITY_TYPES | {EntityType.MORTAL})
HOSTILE_KINDS = (BondKind.ENEMY, BondKind.SPY_NETWORK, BondKind.RIVAL, BondKind.HUNTS)
STAR_NAME = "The {ordinal} Star of {world}'s sky"


class RouteAction(StrEnum):
    SEVER = "sever"
    STITCH = "stitch"
    REVEAL = "reveal"


class RouteCommand(Command):
    route_id: int
    action: RouteAction
    duration: int | None = None


class JourneyTarget(Command):
    journey_id: int


class HangStar(Command):
    name: str = ""
    star_type: StarType = StarType.YELLOW_DWARF
    description: str | None = None
    world_id: int | None = None


class RouteTarget(Command):
    route_id: int


class WorldTarget(Command):
    world_id: int


class StarTarget(Command):
    star_id: int


class SoulBind(Command):
    soul_id: int
    target_id: int


class LegendaryQuest(Command):
    kind: LegendaryQuestKind


class SkyEvent(Command):
    kind: SkyEventKind
    world_id: int | None = None
    star_id: int | None = None
    route_id: int | None = None
    duration: int | None = None


class Exile(Command):
    entity_id: int
    world_id: int


class EntityTarget(Command):
    entity_id: int


class Orbit(Command):
    world_id: int
    star_id: int | None = None
    parent_world_id: int | None = None


class EditStar(Command):
    star_id: int
    name: str | None = None
    star_type: StarType | None = None
    description: str | None = None
    image_prompt: str | None = None
    brightness: int | None = None
    x: float | None = None
    y: float | None = None


class OpenRoute(Command):
    first_world_id: int
    second_world_id: int
    method: TravelMethod


class Climate(Command):
    era: ClimateEra
    epochs: int | None = None
    world_id: int | None = None


class DefineResource(Command):
    name: str
    description: str = ""
    rule: str = ""
    side_effect: str = ""


class OpenDeposit(Command):
    place_id: int


@player_action("route", ActionKind.SEVER_ROUTE)
async def route_action(scope: PlayerScope, command: RouteCommand) -> Effect:
    route = await guards.route(scope.session, command.route_id)
    creator = await scope.creator()
    ctx = await scope.context(f"route.{command.action.value}")
    tool = f"route:{command.action.value}"
    if command.action is RouteAction.SEVER:
        spent = guards.charge(creator, scope.rules.beyond.sever_route_cost, "beyond.sever_route_cost")
        result = await sever_route(ctx, route.id, duration=command.duration, by=creator.name)
        message = f"The route was severed until epoch {result.severed_until}."
        return Effect(message, route.id, essence_spent=spent, kind=ActionKind.SEVER_ROUTE, tool=tool, values={"until": result.severed_until})
    if command.action is RouteAction.STITCH:
        spent = guards.charge(creator, scope.rules.beyond.reopen_route_cost, "beyond.reopen_route_cost")
        message = await stitch_route(ctx, route.id, creator.name)
        return Effect(message, route.id, essence_spent=spent, kind=ActionKind.STITCH_ROUTE, tool=tool)
    if route.known:
        raise ValidationFailedError("This route is not hidden.")
    spent = guards.charge(creator, scope.rules.travel.reveal_route_cost, "travel.reveal_route_cost")
    message = await reveal_hidden_route(ctx, route.id, creator.name)
    if not route.active:
        message = f"{message} The road is still closed."
    return Effect(message, route.id, essence_spent=spent, kind=ActionKind.REVEAL_ROUTE, tool=tool)


@player_action("journey:recall", ActionKind.RECALL_JOURNEY)
async def recall_journey(scope: PlayerScope, command: JourneyTarget) -> Effect:
    creator = await scope.creator()
    ctx = await scope.context("recall")
    return Effect(await engine_recall_journey(ctx, command.journey_id, creator.name), command.journey_id)


async def _star_name(scope: PlayerScope, world_id: int | None) -> str:
    cosmos = await scope.cosmos()
    world = await guards.world(scope.session, world_id or cosmos.primary_world_id or 0)
    language = await scope.session.scalar(
        select(EntityRow)
        .where(EntityRow.world_id == world.id, EntityRow.entity_type == EntityType.LANGUAGE, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
        .limit(1)
    )
    stars = int(await scope.session.scalar(select(func.count()).select_from(StarRow)) or 0)
    if language is not None:
        generated = await Namer(scope.session, scope.rules).from_language(language, seed_of("star", stars, await scope.epoch()), NameKind.PLACE)
        if generated:
            return generated
    return await NameRepository(scope.session).unique_name(STAR_NAME.format(ordinal=ordinal(stars + 1), world=world.name))


@player_action("cosmic:hang_star", ActionKind.HANG_STAR)
async def hang_star(scope: PlayerScope, command: HangStar) -> Effect:
    creator = await scope.creator()
    name = command.name.strip() or await _star_name(scope, command.world_id)
    if len(name) < STAR_NAME_MIN_LENGTH:
        raise ValidationFailedError(f"A star's name needs at least {STAR_NAME_MIN_LENGTH} letters.")
    if await NameRepository(scope.session).is_taken(name):
        raise ValidationFailedError(f'"{name}" is already used in the cosmos; choose another name.')
    spent = guards.charge(creator, scope.rules.cosmic_costs.ignite_star, "cosmic_costs.ignite_star")
    ctx = await scope.context("hang_star")
    star = await engine_hang_star(ctx, name, command.star_type, creator.name, (command.description or "").strip() or None)
    return Effect(f"{star.name} now hangs in the sky.", star.id, essence_spent=spent, created_ids=(star.id,))


@player_action("cosmic:seal_gate", ActionKind.SEAL_GATE)
async def seal_gate(scope: PlayerScope, command: RouteTarget) -> Effect:
    route = await guards.route(scope.session, command.route_id)
    creator = await scope.creator()
    spent = guards.charge(creator, scope.rules.cosmic_costs.seal_gate, "cosmic_costs.seal_gate")
    message = await engine_seal_gate(await scope.context("seal_gate"), route.id, creator.name)
    return Effect(message, route.id, essence_spent=spent)


@player_action("cosmic:cleanse_leak", ActionKind.CLEANSE_LEAK)
async def cleanse_leak(scope: PlayerScope, command: WorldTarget) -> Effect:
    world = await guards.world(scope.session, command.world_id)
    creator = await scope.creator()
    spent = guards.charge(creator, scope.rules.cosmic_costs.cleanse_leak, "cosmic_costs.cleanse_leak")
    message = await engine_cleanse_leak(await scope.context("cleanse_leak"), world.id, creator.name)
    return Effect(message, world.id, essence_spent=spent)


@player_action("cosmic:forget_world", ActionKind.FORGET_WORLD)
async def forget(scope: PlayerScope, command: WorldTarget) -> Effect:
    world = await guards.open_world(scope.session, command.world_id)
    creator = await scope.creator()
    spent = guards.charge(creator, scope.rules.cosmic_costs.forget_world, "cosmic_costs.forget_world")
    message = await forget_world(await scope.context("forget_world"), world.id, creator.name)
    return Effect(message, world.id, essence_spent=spent)


@player_action("cosmic:rekindle_star", ActionKind.REKINDLE_STAR)
async def rekindle(scope: PlayerScope, command: StarTarget) -> Effect:
    star = await guards.star(scope.session, command.star_id)
    creator = await scope.creator()
    spent = guards.charge(creator, scope.rules.cosmic_costs.rekindle_dead_star, "cosmic_costs.rekindle_dead_star")
    message = await engine_rekindle_star(await scope.context("rekindle"), star.id, creator.name)
    return Effect(message, star.id, essence_spent=spent)


@player_action("cosmic:extinguish_star", ActionKind.EXTINGUISH_STAR)
async def extinguish(scope: PlayerScope, command: StarTarget) -> Effect:
    star = await guards.star(scope.session, command.star_id)
    if star.star_type in EXTINGUISHED_STAR_TYPES:
        raise ValidationFailedError(f"{star.name} is already dark.")
    creator = await scope.creator()
    spent = guards.charge(creator, scope.rules.cosmic_costs.extinguish_star, "cosmic_costs.extinguish_star")
    message = await extinguish_star(await scope.context("extinguish_star"), star.id, creator.name)
    return Effect(message, star.id, essence_spent=spent)


@player_action("cosmic:soul_bind", ActionKind.SPIRIT_CLOAK)
async def bind_soul(scope: PlayerScope, command: SoulBind) -> Effect:
    creator = await scope.creator()
    spent = guards.charge(creator, scope.rules.cosmic_costs.spirit_cloak, "cosmic_costs.spirit_cloak")
    result = await soul_bind(await scope.context("soul_bind"), command.soul_id, command.target_id, creator.name)
    return Effect(f"A soul now dwells in {result.name}.", result.id, essence_spent=spent)


@player_action("cosmic:legendary_quest", ActionKind.LEGENDARY_QUEST)
async def legendary_quest(scope: PlayerScope, command: LegendaryQuest) -> Effect:
    creator = await scope.creator()
    spent = guards.charge(creator, scope.rules.cosmic_costs.legendary_expedition, "cosmic_costs.legendary_expedition")
    quest = await open_quest(await scope.context("legendary_quest"), command.kind, creator.name, ActorKind.CREATOR)
    return Effect(f"A legendary quest began: {command.kind.value.replace('_', ' ')}.", essence_spent=spent, values={"thread_id": quest.thread_id})


@player_action("cosmic:sky_event", ActionKind.SKY_EVENT)
async def order_sky_event(scope: PlayerScope, command: SkyEvent) -> Effect:
    if command.world_id is None and command.star_id is None and command.route_id is None:
        raise ValidationFailedError("A sky event needs a world, a star or a route.")
    if command.world_id is not None:
        await guards.world(scope.session, command.world_id)
    if command.star_id is not None:
        await guards.star(scope.session, command.star_id)
    if command.route_id is not None:
        await guards.route(scope.session, command.route_id)
    creator = await scope.creator()
    spent = guards.charge(creator, scope.rules.cosmic_costs.sky_event, "cosmic_costs.sky_event")
    order = SkyOrder(world_id=command.world_id, star_id=command.star_id, route_id=command.route_id, duration=command.duration, by=creator.name)
    result = await sky_event(await scope.context("sky_event"), command.kind, order)
    return Effect(result.text, result.world_id, essence_spent=spent)


async def _descendants(scope: PlayerScope, root_id: int) -> list[EntityRow]:
    found: list[EntityRow] = []
    frontier = [root_id]
    seen = {root_id}
    while frontier:
        children = list(await scope.session.scalars(select(EntityRow).where(EntityRow.location_id.in_(frontier)).order_by(EntityRow.id)))
        frontier = []
        for child in children:
            if child.id not in seen:
                seen.add(child.id)
                found.append(child)
                frontier.append(child.id)
    return found


@player_action("exile", ActionKind.EXILE_ENTITY)
async def exile(scope: PlayerScope, command: Exile) -> Effect:
    target = await guards.canon_entity(scope.session, command.entity_id)
    if target.entity_type not in EXILE_TYPES:
        raise ValidationFailedError("Only communities and mortals can be exiled.")
    world = await guards.open_world(scope.session, command.world_id)
    if world.id == target.world_id:
        raise ValidationFailedError(f"{target.name} already lives in {world.name}.")
    regions = list(
        await scope.session.scalars(
            select(EntityRow).where(EntityRow.world_id == world.id, EntityRow.entity_type == EntityType.REGION, EntityRow.status == EntityStatus.CANON)
        )
    )
    if not regions:
        raise ValidationFailedError(f"{world.name} has no region to receive an exile.")
    region = max(regions, key=lambda item: (item.stats.model_dump().get("danger") or 0, -item.id))
    epoch = await scope.epoch()
    await EntityRepository(scope.session).move(target, region.id, epoch)
    target.map_x = None
    target.map_y = None
    moved = [target, *await _descendants(scope, target.id)]
    for item in moved[1:]:
        item.world_id = world.id
        item.map_x = None
        item.map_y = None
    await EntityRepository(scope.session).add_flag(target.id, EntityFlag.EXILE, epoch)
    moved_ids = {item.id for item in moved}
    severed = 0
    bonds = BondRepository(scope.session)
    hostile = await scope.session.scalars(
        select(BondRow).where(
            BondRow.kind.in_(HOSTILE_KINDS),
            BondRow.state == BondState.ACTIVE,
            or_(BondRow.source_node_id.in_(moved_ids), BondRow.target_node_id.in_(moved_ids)),
        )
    )
    for bond in list(hostile):
        other_id = bond.target_node_id if bond.source_node_id in moved_ids else bond.source_node_id
        other = await scope.session.get(EntityRow, other_id)
        if other is None or other.world_id != world.id:
            await bonds.deactivate(bond, epoch, "severed by exile")
            severed += 1
    (await scope.cosmos()).map_version += 1
    creator = await scope.creator()
    ctx = await scope.context("exile")
    carried = f", carrying {len(moved) - 1} of its own" if len(moved) > 1 else ""
    message = await tell(
        ctx,
        EXILED_ENTITY,
        ids=[target.id, region.id],
        kind=ChronicleKind.COSMIC_LAW,
        creator=creator.name,
        entity=target.name,
        region=region.name,
        world=world.name,
        carried=carried,
    )
    if severed:
        message = f"{message} {await tell(ctx, HOSTILITY_SEVERED, ids=[target.id], kind=ChronicleKind.COSMIC_LAW, entity=target.name)}"
    return Effect(message, target.id, values={"severed": severed, "moved": len(moved)})


@player_action("pardon", ActionKind.PARDON)
async def pardon(scope: PlayerScope, command: EntityTarget) -> Effect:
    target = await guards.canon_entity(scope.session, command.entity_id)
    flags = await EntityRepository(scope.session).flags(target.id)
    if not flags & {EntityFlag.OATHBREAKER, EntityFlag.EXILE, EntityFlag.CURSED}:
        raise ValidationFailedError(f"{target.name} carries no oath-breaking, exile or curse to pardon.")
    creator = await scope.creator()
    return Effect(await engine_pardon(await scope.context("pardon"), target.id, creator.name), target.id)


async def _orbit_cycle(scope: PlayerScope, world: WorldRow, parent: WorldRow) -> bool:
    current: WorldRow | None = parent
    seen: set[int] = set()
    while current is not None and current.id not in seen:
        if current.id == world.id:
            return True
        seen.add(current.id)
        current = await scope.session.get(WorldRow, current.parent_world_id) if current.parent_world_id is not None else None
    return False


@player_action("world:orbit", ActionKind.EDIT_RECORD)
async def set_orbit(scope: PlayerScope, command: Orbit) -> Effect:
    world = await guards.world(scope.session, command.world_id)
    if (command.star_id is None) == (command.parent_world_id is None):
        raise ValidationFailedError("Choose either a star to circle or a world to become the moon of.")
    if command.parent_world_id is not None:
        if command.parent_world_id == world.id:
            raise ValidationFailedError("A world cannot be its own moon.")
        parent = await guards.world(scope.session, command.parent_world_id)
        if await _orbit_cycle(scope, world, parent):
            raise ValidationFailedError(f"{parent.name} already orbits {world.name}.")
        siblings = int(
            await scope.session.scalar(select(func.count()).select_from(WorldRow).where(WorldRow.parent_world_id == parent.id, WorldRow.id != world.id)) or 0
        )
        world.parent_world_id = parent.id
        world.star_id = parent.star_id
        world.orbit = ORBIT_MOON_BASE + ORBIT_MOON_STEP * siblings
        note = f"it became a moon of {parent.name}"
    else:
        star = await guards.star(scope.session, command.star_id or 0)
        planets = int(
            await scope.session.scalar(
                select(func.count()).select_from(WorldRow).where(WorldRow.star_id == star.id, WorldRow.parent_world_id.is_(None), WorldRow.id != world.id)
            )
            or 0
        )
        world.parent_world_id = None
        world.star_id = star.id
        world.orbit = ORBIT_PLANET_BASE + ORBIT_PLANET_STEP * planets
        note = f"it now circles {star.name}"
    moons = await align_moons(scope.session)
    if moons:
        note += f"; {moons} moons moved to the new orbit with it"
    (await scope.cosmos()).map_version += 1
    ctx = await scope.context("orbit")
    return Effect(await tell(ctx, WORLD_RESHAPED, world_id=world.id, world=world.name, notes=f": {note}"), world.id)


@player_action("star:delete", ActionKind.EXTINGUISH_STAR)
async def delete_star(scope: PlayerScope, command: StarTarget) -> Effect:
    star = await guards.star(scope.session, command.star_id)
    planets = list(await scope.session.scalars(select(WorldRow).where(WorldRow.star_id == star.id, WorldRow.parent_world_id.is_(None))))
    moons = int(
        await scope.session.scalar(select(func.count()).select_from(WorldRow).where(WorldRow.star_id == star.id, WorldRow.parent_world_id.is_not(None))) or 0
    )
    if planets:
        names = ", ".join(world.name for world in planets)
        tail = f" (with {moons} moons)" if moons else ""
        pronoun = "them" if len(planets) > 1 else "it"
        raise ValidationFailedError(f"{star.name} cannot be removed: {names} orbit it{tail}. First move {pronoun} to another star; its moons go with it.")
    creator = await scope.creator()
    name = star.name
    ctx = await scope.context("delete_star")
    message = await tell(ctx, STAR_REMOVED, kind=ChronicleKind.COSMIC, creator=creator.name, star=name)
    await NameRepository(scope.session).release(star.id)
    await scope.session.execute(delete(StarRow).where(StarRow.id == star.id))
    return Effect(message, None)


@player_action("star:edit", ActionKind.EDIT_RECORD)
async def edit_star(scope: PlayerScope, command: EditStar) -> Effect:
    star = await guards.star(scope.session, command.star_id)
    fields: list[str] = []
    if command.name is not None and normalize_name(command.name) != normalize_name(star.name):
        if not command.name.strip():
            raise ValidationFailedError("A star's name cannot be empty.")
        names = NameRepository(scope.session)
        if await names.is_taken(command.name, ignore_node_id=star.id):
            raise ValidationFailedError(f'"{command.name}" is already used in the cosmos; choose another name.')
        await names.rename(star.id, command.name)
        fields.append("name")
    if command.star_type is not None:
        star.star_type = command.star_type
        fields.append("type")
    for name in ("description", "image_prompt"):
        value = getattr(command, name)
        if value is not None:
            setattr(star, name, value.strip() or None)
            fields.append(name.replace("_", " "))
    if command.brightness is not None:
        star.brightness = max(PERCENT_MIN, min(PERCENT_MAX, command.brightness))
        fields.append("brightness")
    if command.x is not None:
        star.x = command.x
        fields.append("position")
    if command.y is not None:
        star.y = command.y
        fields.append("position")
    if not fields:
        raise ValidationFailedError(f"Nothing to change on {star.name}.")
    ctx = await scope.context("edit_star")
    return Effect(await tell(ctx, STAR_EDITED, kind=ChronicleKind.COSMIC, star=star.name), star.id)


@player_action("route:open", ActionKind.STITCH_ROUTE)
async def open_route(scope: PlayerScope, command: OpenRoute) -> Effect:
    if command.first_world_id == command.second_world_id:
        raise ValidationFailedError("A road needs two different worlds.")
    first = await guards.world(scope.session, command.first_world_id)
    second = await guards.world(scope.session, command.second_world_id)
    for world in (first, second):
        if world.discovery is Discovery.FORGOTTEN:
            raise ValidationFailedError(f"{world.name} is forgotten; no road opens there.")
    epoch = await scope.epoch()
    ctx = await scope.context("open_route")
    route = await engine_open_route(
        scope.session, scope.rules, ctx.rng("open_route"), epoch, RouteSpec(first.id, second.id, command.method, description="a road opened by the god")
    )
    creator = await scope.creator()
    message = await hand(
        ctx, creator, ROUTE_OPENED, kind=ChronicleKind.COSMIC, first=first.name, second=second.name, method=command.method.value.replace("_", " ")
    )
    return Effect(message, route.id, created_ids=(route.id,))


@player_action("climate", ActionKind.OTHER)
async def command_climate(scope: PlayerScope, command: Climate) -> Effect:
    hand_rules = scope.rules.god_hand
    epochs = command.epochs if command.epochs is not None else hand_rules.decree_climate_epochs
    if epochs < 1:
        raise ValidationFailedError("A climate era must last at least 1 epoch.")
    if epochs > hand_rules.decree_climate_max_epochs:
        raise ValidationFailedError(
            f"A climate era lasts at most {hand_rules.decree_climate_max_epochs} epochs (world rule god_hand.decree_climate_max_epochs)."
        )
    if command.world_id is not None:
        world = await guards.world(scope.session, command.world_id)
        if world.discovery is Discovery.FORGOTTEN:
            raise ValidationFailedError(f"{world.name} is forgotten; no climate is commanded to the sky inside the mist.")
        targets = [world]
    else:
        targets = list(await scope.session.scalars(select(WorldRow).where(WorldRow.discovery != Discovery.FORGOTTEN).order_by(WorldRow.id)))
    ctx = await scope.context("climate")
    for world in targets:
        await impose_climate(ctx, world.id, command.era, epochs)
    creator = await scope.creator()
    target = targets[0].name if command.world_id is not None else "all worlds"
    message = await hand(ctx, creator, CLIMATE_COMMANDED, kind=ChronicleKind.CLIMATE, era=command.era.value.replace("_", " "), target=target, epochs=epochs)
    return Effect(message, command.world_id)


@player_action("cosmos:resource", ActionKind.OTHER)
async def define_resource(scope: PlayerScope, command: DefineResource) -> Effect:
    name = command.name.strip()
    if not name:
        raise ValidationFailedError("The resource must have a name.")
    resource = TravelResource(name=name, description=command.description.strip(), rule=command.rule.strip(), side_effect=command.side_effect.strip())
    await define_cosmic_resource(scope.session, resource, replace=True)
    creator = await scope.creator()
    ctx = await scope.context("cosmic_resource")
    return Effect(await hand(ctx, creator, RESOURCE_DEFINED, kind=ChronicleKind.COSMIC, name=name))


@player_action("cosmos:deposit", ActionKind.OPEN_COSMIC_BED)
async def open_deposit(scope: PlayerScope, command: OpenDeposit) -> Effect:
    place = await guards.entity(scope.session, command.place_id)
    if place.entity_type not in (EntityType.REGION, EntityType.PLACE):
        raise ValidationFailedError("A deposit is opened in a region or place.")
    deposit = await cosmic_economy.open_deposit(scope.session, scope.rules, place.id)
    cosmos = await scope.cosmos()
    resource = cosmos.travel_resource.name if cosmos.travel_resource is not None else deposit.name
    creator = await scope.creator()
    ctx = await scope.context("deposit")
    message = await hand(ctx, creator, DEPOSIT_OPENED, ids=[deposit.id, place.id], resource=resource, place=place.name)
    return Effect(message, deposit.id, created_ids=(deposit.id,))
