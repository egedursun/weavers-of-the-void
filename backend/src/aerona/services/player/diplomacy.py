from enum import StrEnum
from itertools import combinations

from sqlalchemy import select

from aerona.constants.player import FEDERATION_MIN_MEMBERS
from aerona.core.errors import ConflictError, ValidationFailedError
from aerona.core.grammar import several, spoken
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.entities import EntityDraft, EntityRepository
from aerona.db.repositories.names import NameRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.routes import JourneyRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EngineKind, EntityFlag, EntityOrigin, EntityStatus, EntityType
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import ClauseKind
from aerona.domain.enums.polity import TreatyKind as PolityTreatyKind
from aerona.domain.enums.travel import JourneyIntent, JourneyStatus
from aerona.domain.enums.war import WarCause, WarEnding
from aerona.domain.models.entity_stats import FactionStats
from aerona.engine.cosmos.routes import can_use_route
from aerona.engine.gods.devotion import RiteKind
from aerona.engine.phases.diplomacy import decree_alliance
from aerona.engine.phases.exploration import SearchStatus, planet_exploration, record_intuition, search_route, send_to_explore
from aerona.engine.phases.travel import send_expedition
from aerona.engine.polity.accords import Clause
from aerona.engine.polity.treaties import sign_derived
from aerona.engine.primitives.stats import stat
from aerona.engine.recording.record import record
from aerona.engine.services.community_relations import change_relation
from aerona.engine.services.war import WarBlock, can_open_war, declare_war
from aerona.engine.services.war_resolution import settle_peace
from aerona.services.gods import death
from aerona.services.player import guards
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

TRAVELLER_TYPES = frozenset(COMMUNITY_TYPES | {EntityType.MORTAL})
DECREE_REASON = "the god's command"
SEEK_HOW = "following the stars the god showed"
FEDERATION_SUBTYPE = "federation"
INTERWORLD_FEDERATION_SUBTYPE = "interworld federation"


class DecreeKind(StrEnum):
    WAR = "war"
    PEACE = "peace"
    ALLIANCE = "alliance"
    MARRIAGE = "marriage"
    TRADE = "trade"


class Decree(Command):
    entity_id: int
    target_id: int
    kind: DecreeKind


class Expedition(Command):
    entity_id: int
    route_id: int
    intent: JourneyIntent = JourneyIntent.EXPLORATION
    percent: int | None = None


class LandKind(StrEnum):
    REGION = "region"
    PLACE = "place"


class Explore(Command):
    entity_id: int
    kind: LandKind | None = None


class EntityTarget(Command):
    entity_id: int


class Rite(Command):
    entity_id: int
    son_id: int
    kind: RiteKind
    victim_id: int | None = None


class DiscoveryRound(Command):
    world_id: int


class Federation(Command):
    member_ids: tuple[int, ...]
    name: str = ""


async def _traveller(scope: PlayerScope, entity_id: int) -> EntityRow:
    target = await guards.entity(scope.session, entity_id)
    if target.status is not EntityStatus.CANON:
        raise ValidationFailedError(f"{target.name} no longer lives.")
    if target.entity_type not in TRAVELLER_TYPES:
        raise ValidationFailedError("Only communities and mortals go on expeditions.")
    return target


@player_action("decree", ActionKind.DIPLOMACY)
async def decree(scope: PlayerScope, command: Decree) -> Effect:
    if command.entity_id == command.target_id:
        raise ValidationFailedError("A decree needs two different parties.")
    first = await guards.entity(scope.session, command.entity_id)
    second = await guards.entity(scope.session, command.target_id)
    if command.kind is not DecreeKind.PEACE:
        if first.status is not EntityStatus.CANON or second.status is not EntityStatus.CANON:
            raise ValidationFailedError("A command is only set between the living.")
        if not await guards.reachable(scope.session, first, second):
            raise ValidationFailedError(f"{first.name} and {second.name} are in separate worlds with no open road between them.")
    hand_rules = scope.rules.god_hand
    ctx = await scope.context(f"decree.{command.kind.value}")
    bonds = BondRepository(scope.session)
    kind = ActionKind.DIPLOMACY
    if command.kind is DecreeKind.WAR:
        block = await can_open_war(scope.session, scope.rules, first.id, second.id, ctx.epoch)
        if block is not None and block is not WarBlock.ALREADY_ENEMIES:
            raise ConflictError(f"No war can be commanded between {first.name} and {second.name}: {spoken(block)}.")
        await declare_war(ctx, first.id, second.id, DECREE_REASON, cause=WarCause.DECLARED)
        await change_relation(ctx, first.id, second.id, -hand_rules.decree_war_relation, MemoryKind.DIVINE_WILL, note=DECREE_REASON)
        kind = ActionKind.DECLARE_WAR
    elif command.kind is DecreeKind.PEACE:
        await settle_peace(ctx, first.id, second.id, WarEnding.PEACE, DECREE_REASON, truce=True, apply_relation=False)
        await change_relation(ctx, first.id, second.id, hand_rules.decree_peace_relation, MemoryKind.DIVINE_WILL, note=DECREE_REASON)
    elif command.kind is DecreeKind.ALLIANCE:
        await bonds.close_between(first.id, second.id, [BondKind.ENEMY], ctx.epoch, DECREE_REASON)
        if not await bonds.exists_between(first.id, second.id, BondKind.ALLY):
            await sign_derived(
                ctx,
                PolityTreatyKind.ALLIANCE_DEFENSIVE,
                first.id,
                second.id,
                until=ctx.epoch + ctx.rules.treaties.alliance_epochs,
                clauses=[Clause(ClauseKind.CALL_TO_ARMS, first.id, second.id), Clause(ClauseKind.CALL_TO_ARMS, second.id, first.id)],
            )
        await change_relation(ctx, first.id, second.id, hand_rules.decree_alliance_relation, MemoryKind.DIVINE_WILL, note=DECREE_REASON)
    elif command.kind is DecreeKind.MARRIAGE:
        await bonds.close_between(first.id, second.id, [BondKind.ENEMY], ctx.epoch, DECREE_REASON)
        await decree_alliance(ctx, first.id, second.id, marriage=True)
    else:
        await bonds.close_between(first.id, second.id, [BondKind.ENEMY], ctx.epoch, DECREE_REASON)
        if not await bonds.exists_between(first.id, second.id, BondKind.TRADES_WITH):
            await sign_derived(ctx, PolityTreatyKind.TRADE_PACT, first.id, second.id, until=ctx.epoch + ctx.rules.treaties.trade_epochs)
        await change_relation(ctx, first.id, second.id, hand_rules.decree_trade_relation, MemoryKind.DIVINE_WILL, note=DECREE_REASON)
        kind = ActionKind.ESTABLISH_TRADE
    creator = await scope.creator()
    message = (
        await record(
            ctx,
            "player.entity.decree",
            roles={IncidentRole.SUBJECT: [first.id, second.id], IncidentRole.AUTHORITY: creator.id},
            facts={"decree": spoken(command.kind).capitalize()},
            kind=ChronicleKind.DIPLOMACY,
        )
    ).text
    return Effect(message, first.id, kind=kind, tool=f"decree:{command.kind.value}")


@player_action("expedition", ActionKind.SET_OUT)
async def expedition(scope: PlayerScope, command: Expedition) -> Effect:
    traveller = await _traveller(scope, command.entity_id)
    route = await guards.route(scope.session, command.route_id)
    if traveller.world_id not in (route.world_a_id, route.world_b_id):
        raise ValidationFailedError(f"There is no such road out of {traveller.name}'s world.")
    if not route.known:
        raise ValidationFailedError("This road is hidden; reveal it first (Reveal action).")
    epoch = await scope.epoch()
    problem = await can_use_route(scope.session, scope.rules, epoch, traveller, route)
    if problem is not None:
        raise ValidationFailedError(problem)
    travelling = await scope.session.scalar(
        select(JourneyRow.id)
        .where(JourneyRow.traveller_entity_id == traveller.id, JourneyRow.status.in_([JourneyStatus.UNDERWAY, JourneyStatus.WAITING]))
        .limit(1)
    )
    if travelling is not None:
        raise ValidationFailedError("Already on the road.")
    hand_rules = scope.rules.god_hand
    percent = command.percent if command.percent is not None else hand_rules.decree_expedition_pct
    if percent < 1:
        raise ValidationFailedError("At least 1% of the population must join.")
    if percent > hand_rules.decree_expedition_max_pct:
        cap = hand_rules.decree_expedition_max_pct
        raise ValidationFailedError(f"At most {cap}% of the population may join (world rule god_hand.decree_expedition_max_pct = {cap}).")
    population = stat(traveller, "population")
    travellers = round(population * percent / 100) if population else 1
    journey = await send_expedition(scope.session, scope.rules, traveller.id, route.id, command.intent, population=travellers)
    destination = await guards.world(scope.session, journey.destination_world_id)
    epochs = journey.epochs_left
    creator = await scope.creator()
    ctx = await scope.context("expedition")
    message = (
        await record(
            ctx,
            "player.entity.expedition",
            roles={IncidentRole.TARGET: traveller.id, IncidentRole.AUTHORITY: creator.id},
            facts={"intent": command.intent, "world": str(destination.name), "epochs": epochs},
            kind=ChronicleKind.CREATOR_HAND,
        )
    ).text
    return Effect(message, traveller.id, created_ids=(journey.id,), values={"journey_id": journey.id, "travellers": travellers})


@player_action("explore", ActionKind.EXPLORE_LAND)
async def explore(scope: PlayerScope, command: Explore) -> Effect:
    explorer = await _traveller(scope, command.entity_id)
    kind = EntityType.REGION if command.kind is LandKind.REGION else EntityType.PLACE if command.kind is LandKind.PLACE else None
    found = await send_to_explore(scope.session, scope.rules, explorer.id, kind)
    if found is None:
        raise ValidationFailedError("There is no region to explore in this world; a new region must be found first (land: region).")
    creator = await scope.creator()
    ctx = await scope.context("explore")
    message = (
        await record(
            ctx,
            "player.entity.explored",
            roles={IncidentRole.TARGET: explorer.id, IncidentRole.PLACE: found.land.id, IncidentRole.AUTHORITY: creator.id},
            place=found.land.id,
            kind=ChronicleKind.EXPLORATION,
        )
    ).text
    return Effect(message, explorer.id, created_ids=(found.land.id,))


@player_action("seek_route", ActionKind.DISCOVER_ROUTE)
async def seek_route(scope: PlayerScope, command: EntityTarget) -> Effect:
    seeker = await _traveller(scope, command.entity_id)
    creator = await scope.creator()
    ctx = await scope.context("seek_route")
    result = await search_route(ctx, seeker, SEEK_HOW, certain=True)
    if result.status is SearchStatus.ROUTE:
        await record(ctx, "player.entity.road", roles={IncidentRole.ACTOR: creator.id, IncidentRole.TARGET: seeker.id}, kind=ChronicleKind.EXPLORATION)
        return Effect(result.text, seeker.id, created_ids=(result.route.id,) if result.route is not None else ())
    if result.status is SearchStatus.INTUITION:
        await record_intuition(ctx, seeker, SEEK_HOW, result.method)
        message = (
            await record(ctx, "player.entity.sensed", roles={IncidentRole.ACTOR: creator.id, IncidentRole.TARGET: seeker.id}, kind=ChronicleKind.EXPLORATION)
        ).text
        return Effect(message, seeker.id)
    raise ValidationFailedError(
        "There is already a road to every known world and no new world can be sensed this epoch (world rule mortal_tools.unknown_world_per_epoch)."
    )


@player_action("rite", ActionKind.RESURRECTION_RITE)
async def order_rite(scope: PlayerScope, command: Rite) -> Effect:
    worshipper = await guards.canon_entity(scope.session, command.entity_id)
    son = await guards.son(scope.session, command.son_id)
    result = await death.order_rite(scope.session, scope.rules, worshipper.id, son.id, command.kind, victim_id=command.victim_id)
    creator = await scope.creator()
    ctx = await scope.context("rite")
    await record(
        ctx,
        "player.entity.rite",
        roles={IncidentRole.TARGET: worshipper.id, IncidentRole.SUBJECT: son.id, IncidentRole.AUTHORITY: creator.id},
        kind=ChronicleKind.RESURRECTION,
        son_id=son.id,
    )
    return Effect(result.text, worshipper.id)


@player_action("discovery_round", ActionKind.EXPLORE_LAND)
async def discovery_round(scope: PlayerScope, command: DiscoveryRound) -> Effect:
    world = await guards.world(scope.session, command.world_id)
    ctx = await scope.context("discovery_round")
    found = await planet_exploration(ctx, world.id)
    result = f"{several(len(found), 'new land', 'new lands')} found" if found else "this time nobody found a new land"
    creator = await scope.creator()
    message = (
        await record(
            ctx,
            "player.world.discovery",
            roles={IncidentRole.AUTHORITY: creator.id},
            facts={"world": str(world.name), "result": str(result)},
            kind=ChronicleKind.EXPLORATION,
            world_id=world.id,
        )
    ).text
    return Effect(message, world.id, created_ids=tuple(item.land.id for item in found))


@player_action("federation", ActionKind.COVENANT)
async def found_federation(scope: PlayerScope, command: Federation) -> Effect:
    member_ids = list(dict.fromkeys(command.member_ids))
    if len(member_ids) < FEDERATION_MIN_MEMBERS:
        raise ValidationFailedError("Choose at least two communities for a federation.")
    members: list[EntityRow] = []
    for member_id in member_ids:
        member = await guards.entity(scope.session, member_id)
        if member.status is not EntityStatus.CANON or member.entity_type not in COMMUNITY_TYPES:
            raise ValidationFailedError(f"{member.name} is not a living community.")
        members.append(member)
    civ = scope.rules.civilization
    creator = await scope.creator()
    epoch = await scope.epoch()
    names = ", ".join(member.name for member in members)
    spans = len({member.world_id for member in members}) > 1
    name = command.name.strip() or f"{members[0].name} Federation"
    faction = await EntityRepository(scope.session).create(
        EntityDraft(
            name=await NameRepository(scope.session).unique_name(name),
            entity_type=EntityType.FACTION,
            description=f"{names} united in one federation by {creator.name}'s command.",
            stats=FactionStats(strength=civ.federation_strength, wealth=civ.federation_wealth, sway=civ.federation_sway),
            power_level=civ.federation_power,
            origin=EntityOrigin.CREATOR,
            birth_epoch=epoch,
            world_id=members[0].world_id,
            location_id=members[0].location_id,
            subtype=INTERWORLD_FEDERATION_SUBTYPE if spans else FEDERATION_SUBTYPE,
            engine_kind=EngineKind.INTERWORLD_FEDERATION if spans else None,
            flags=(EntityFlag.FEDERATION, EntityFlag.FIXED_NAME) if command.name.strip() else (EntityFlag.FEDERATION,),
            pending_name=True,
            split_title=False,
        )
    )
    bonds = BondRepository(scope.session)
    for member in members:
        await bonds.connect(BondDraft(member.id, faction.id, BondKind.MEMBER_OF, epoch, "federation"))
    ctx = await scope.context("federation")
    for first, second in combinations(members, 2):
        await bonds.close_between(first.id, second.id, [BondKind.ENEMY], epoch, "federation")
        if not await bonds.exists_between(first.id, second.id, BondKind.ALLY):
            await sign_derived(
                ctx,
                PolityTreatyKind.ALLIANCE_DEFENSIVE,
                first.id,
                second.id,
                until=None,
                clauses=[Clause(ClauseKind.CALL_TO_ARMS, first.id, second.id), Clause(ClauseKind.CALL_TO_ARMS, second.id, first.id)],
            )
    message = (
        await record(
            ctx,
            "player.entity.federation",
            roles={IncidentRole.ACTOR: creator.id, IncidentRole.SUBJECT: [*([faction.id, *member_ids])]},
            facts={"name": str(faction.name), "members": names},
            kind=ChronicleKind.CIVILIZATION,
        )
    ).text
    return Effect(message, faction.id, created_ids=(faction.id,))
