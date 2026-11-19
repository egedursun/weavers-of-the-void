from enum import StrEnum
from typing import Annotated, Any

from pydantic import Field

from aerona.catalog.gates import Gate
from aerona.catalog.weather import SEASON_DOMAIN_WORDS, SEASON_DOMAINS
from aerona.constants.tool_inputs import NAME_MAX, NAME_MIN, REASON_MAX, REASON_MIN
from aerona.core.errors import AeronaError
from aerona.core.grammar import spoken
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.culture import MagicSchool
from aerona.domain.enums.divine import DomainHook
from aerona.domain.enums.dominion import MagicSiteKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus, EntityType
from aerona.domain.enums.faith import SpiritAlignment
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import StepAction
from aerona.domain.enums.travel import TravelMethod
from aerona.domain.enums.world import Discovery
from aerona.engine.cosmos.routes import RouteSpec
from aerona.engine.cosmos.routes import open_route as engine_open_route
from aerona.engine.dominion import control as dominion
from aerona.engine.environment.control import forge_ley
from aerona.engine.environment.time_control import add_season as engine_add_season
from aerona.engine.faith import control as faith
from aerona.engine.phases.births import crown_ruler as engine_crown_ruler
from aerona.engine.phases.creatures import introduce_species
from aerona.engine.phases.life_seed import seed_life as engine_seed_life
from aerona.engine.phases.warfare import bless_army
from aerona.engine.polity.control import found_house_by_hand
from aerona.engine.recording.record import StepDraft
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, gate, son_standard_action
from aerona.tools.framework.validation import fail, require_canon, require_type
from aerona.tools.son.heavens import world_in_hand
from aerona.tools.son.support import ensure_in_reach, require_essence

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]
Shift = Annotated[int, Field(ge=-100, le=100)]
Share = Annotated[int, Field(ge=0, le=100)]


class HostAspect(StrEnum):
    MORALE = "morale"
    EQUIPMENT = "equipment"
    EXPERIENCE = "experience"


class ForgeLeyInput(ToolInput):
    first_region_id: int
    second_region_id: int
    reason: Reason


class AddSeasonInput(ToolInput):
    world_id: int
    name: Annotated[str, Field(min_length=NAME_MIN, max_length=NAME_MAX)]
    temperature_shift: Shift = 0
    rain_shift: Shift = 0
    growth: Share = 50
    travel: Share = 50
    campaign: Share = 50


class OpenRoadInput(ToolInput):
    first_world_id: int
    second_world_id: int
    method: TravelMethod
    reason: Reason


class ThroneInput(ToolInput):
    place_id: int
    reason: Reason


class MagicSiteInput(ToolInput):
    place_id: int
    kind: MagicSiteKind
    school: MagicSchool
    revealed: bool = False
    reason: Reason


class CarrySpeciesInput(ToolInput):
    species_id: int
    region_id: int
    reason: Reason


class SeedLifeInput(ToolInput):
    world_id: int
    people: bool = False
    reason: Reason


class CallUpSoulInput(ToolInput):
    mortal_id: int
    alignment: SpiritAlignment = SpiritAlignment.NEUTRAL
    reason: Reason


class CommunityInput(ToolInput):
    community_id: int
    reason: Reason


class FoundHouseInput(ToolInput):
    mortal_id: int
    reason: Reason


class BlessHostInput(ToolInput):
    army_id: int
    aspect: HostAspect
    reason: Reason


async def forge_ley_line(call: SonCall, args: ForgeLeyInput) -> str:
    first = require_type(await require_canon(call.session, args.first_region_id), {EntityType.REGION}, SonResult.NOT_A_REGION, name=f"#{args.first_region_id}")
    second = require_type(
        await require_canon(call.session, args.second_region_id), {EntityType.REGION}, SonResult.NOT_A_REGION, name=f"#{args.second_region_id}"
    )
    await ensure_in_reach(call, first)
    await ensure_in_reach(call, second)
    cost = call.rules.son_tools.forge_ley_essence
    require_essence(call, cost)
    try:
        line = await forge_ley(call.session, call.rules, first.id, second.id, epoch=call.tick.epoch)
    except AeronaError as error:
        fail(SonResult.WORK_REFUSED, reason=error.message)
    call.spend_essence(cost)
    call.target(first.id)
    await call.record(
        "tools.son.forge_ley_line",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: [first.id, second.id]},
        facts={"reason": args.reason},
        kind=ChronicleKind.COSMIC,
    )
    return result(SonResult.LEY_FORGED, first=first.name, second=second.name, strength=line.strength)


async def add_season(call: SonCall, args: AddSeasonInput) -> str:
    if not {call.son.domain_primary, call.son.domain_secondary} & SEASON_DOMAINS:
        fail(SonResult.SEASONS_NOT_YOURS, domains=SEASON_DOMAIN_WORDS)
    world = await world_in_hand(call, args.world_id)
    cost = call.rules.son_tools.add_season_essence
    require_essence(call, cost)
    values = args.model_dump(include={"temperature_shift", "rain_shift", "growth", "travel", "campaign"})
    try:
        season = await engine_add_season(call.session, world.id, " ".join(args.name.split()), values, None)
    except AeronaError as error:
        fail(SonResult.WORK_REFUSED, reason=error.message)
    call.spend_essence(cost)
    call.target(world.id)
    await call.record(
        "tools.son.add_season",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.PLACE: world.id},
        facts={"season": str(season.name)},
        kind=ChronicleKind.COSMIC,
        world_id=world.id,
    )
    return result(SonResult.SEASON_ADDED, season=season.name, world=world.name)


async def open_road(call: SonCall, args: OpenRoadInput) -> str:
    if args.first_world_id == args.second_world_id:
        fail(SonResult.WORK_REFUSED, reason="a road needs two different worlds")
    worlds = [await call.session.get(WorldRow, world_id) for world_id in (args.first_world_id, args.second_world_id)]
    first, second = worlds
    if first is None or second is None:
        fail(SonResult.NO_SUCH_WORLD)
    if not (await call.reachable_world(first.id) or await call.reachable_world(second.id)):
        fail(SonResult.WORLD_OUT_OF_REACH, name=first.name)
    for world in (first, second):
        if world.discovery is not Discovery.KNOWN:
            fail(SonResult.WORK_REFUSED, reason=f"{world.name} is not known to the gods")
    cost = call.rules.son_tools.open_road_essence
    require_essence(call, cost)
    spec = RouteSpec(first.id, second.id, args.method, builder_son_id=call.son.id, description=args.reason)
    try:
        route = await engine_open_route(call.session, call.rules, call.tick.rng("open_road"), call.tick.epoch, spec)
    except AeronaError as error:
        fail(SonResult.WORK_REFUSED, reason=error.message)
    call.spend_essence(cost)
    await call.record(
        "tools.son.open_road",
        roles={IncidentRole.ACTOR: call.son.id},
        facts={"first": str(first.name), "second": str(second.name), "reason": args.reason},
        kind=ChronicleKind.COSMIC,
    )
    return result(SonResult.ROAD_OPENED, id=route.id, first=first.name, second=second.name)


async def place_in_hand(call: SonCall, place_id: int) -> EntityRow:
    place = require_type(await require_canon(call.session, place_id), dominion.PLACE_TYPES, SonResult.WORK_NOT_A_PLACE, id=place_id)
    await ensure_in_reach(call, place)
    return place


async def raise_throne(call: SonCall, args: ThroneInput) -> str:
    place = await place_in_hand(call, args.place_id)
    cost = call.rules.son_tools.throne_essence
    require_essence(call, cost)
    try:
        await dominion.create_throne(call.tick, place.id, call.rules.son_tools.throne_power, call.son.id)
    except AeronaError as error:
        fail(SonResult.WORK_REFUSED, reason=error.message)
    call.spend_essence(cost)
    call.target(place.id)
    await call.record(
        "tools.son.raise_throne",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.PLACE: place.id},
        facts={"reason": args.reason},
        place=place.id,
        kind=ChronicleKind.ASCENSION,
    )
    return result(SonResult.THRONE_RAISED, place=place.name)


async def lay_magic_site(call: SonCall, args: MagicSiteInput) -> str:
    place = await place_in_hand(call, args.place_id)
    cost = call.rules.son_tools.magic_site_essence
    require_essence(call, cost)
    try:
        await dominion.create_site(call.tick, place.id, args.kind, args.school, call.rules.son_tools.magic_site_strength, found_now=args.revealed)
    except AeronaError as error:
        fail(SonResult.WORK_REFUSED, reason=error.message)
    call.spend_essence(cost)
    call.target(place.id)
    await call.record(
        "tools.son.lay_magic_site",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.PLACE: place.id},
        facts={"reason": args.reason},
        place=place.id,
        kind=ChronicleKind.COSMIC,
    )
    return result(SonResult.MAGIC_SITE_LAID, place=place.name)


async def carry_species(call: SonCall, args: CarrySpeciesInput) -> str:
    species = require_type(await require_canon(call.session, args.species_id), {EntityType.SPECIES}, SonResult.NOT_A_SPECIES, id=args.species_id)
    region = require_type(await require_canon(call.session, args.region_id), {EntityType.REGION}, SonResult.NOT_A_REGION, name=f"#{args.region_id}")
    await ensure_in_reach(call, region)
    cost = call.rules.son_tools.carry_species_essence
    require_essence(call, cost)
    try:
        carried = await introduce_species(call.session, call.rules, species.id, region.id)
    except AeronaError as error:
        fail(SonResult.WORK_REFUSED, reason=error.message)
    call.spend_essence(cost)
    call.target(carried.id)
    await call.record(
        "tools.son.carry_species",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: [species.id, carried.id], IncidentRole.PLACE: region.id},
        facts={"reason": args.reason},
        place=region.id,
        kind=ChronicleKind.CREATION,
    )
    return result(SonResult.SPECIES_CARRIED, kind=species.name, place=region.name)


async def seed_life(call: SonCall, args: SeedLifeInput) -> str:
    world = await world_in_hand(call, args.world_id)
    cost = call.rules.son_tools.seed_life_essence
    require_essence(call, cost)
    try:
        born = await engine_seed_life(call.tick, world.id, args.people)
    except AeronaError as error:
        fail(SonResult.WORK_REFUSED, reason=error.message)
    call.spend_essence(cost)
    call.remember_creation(born.id)
    call.target(born.id)
    await call.record(
        "tools.son.seed_life",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.PLACE: world.id, IncidentRole.SUBJECT: born.id},
        facts={"life": str(born.name), "reason": args.reason},
        kind=ChronicleKind.CREATION,
    )
    return result(SonResult.LIFE_SEEDED, name=born.name, world=world.name)


async def call_up_soul(call: SonCall, args: CallUpSoulInput) -> str:
    mortal = await call.session.get(EntityRow, args.mortal_id)
    if mortal is None or mortal.entity_type is not EntityType.MORTAL or mortal.status is not EntityStatus.DEAD:
        fail(SonResult.NOT_A_DEAD_MORTAL, id=args.mortal_id)
    await ensure_in_reach(call, mortal)
    death_god = await call.tick.god_share(call.son.id, DomainHook.SOUL_HOLD) > 0
    if mortal.creator_son_id != call.son.id and not death_god:
        fail(SonResult.SOUL_NOT_YOURS, name=mortal.name)
    cost = call.rules.son_tools.call_up_soul_essence
    require_essence(call, cost)
    try:
        spirit = await faith.raise_soul(call.tick, mortal.id, alignment=args.alignment, place_id=None, by=call.son.name)
    except AeronaError as error:
        fail(SonResult.WORK_REFUSED, reason=error.message)
    _, profile = await faith.spirit_profile(call.tick, spirit.id)
    profile.patron_son_id = call.son.id
    call.spend_essence(cost)
    call.remember_creation(spirit.id)
    call.target(spirit.id)
    await call.record(
        "tools.son.call_up_soul",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.TARGET: mortal.id, IncidentRole.SUBJECT: spirit.id},
        facts={"reason": args.reason},
        kind=ChronicleKind.WORSHIP,
    )
    return result(SonResult.SOUL_CALLED_UP, name=spirit.name)


async def crown_ruler(call: SonCall, args: CommunityInput) -> str:
    community = require_type(await require_canon(call.session, args.community_id), COMMUNITY_TYPES, SonResult.NOT_A_COMMUNITY, id=args.community_id)
    await ensure_in_reach(call, community)
    cost = call.rules.son_tools.crown_ruler_essence
    require_essence(call, cost)
    try:
        ruler = await engine_crown_ruler(call.tick, community.id)
    except AeronaError as error:
        fail(SonResult.WORK_REFUSED, reason=error.message)
    call.spend_essence(cost)
    call.target(ruler.id)
    await call.record(
        "tools.son.crown_ruler",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: [community.id, ruler.id]},
        facts={"ruler": str(ruler.name), "reason": args.reason},
        kind=ChronicleKind.ASCENSION,
        steps=(StepDraft(StepAction.CROWN, actor=call.son.id, target=ruler.id),),
    )
    return result(SonResult.RULER_CROWNED, ruler=ruler.name, community=community.name)


async def found_house(call: SonCall, args: FoundHouseInput) -> str:
    mortal = require_type(await require_canon(call.session, args.mortal_id), {EntityType.MORTAL}, SonResult.NOT_A_MORTAL, name=f"#{args.mortal_id}")
    await ensure_in_reach(call, mortal)
    cost = call.rules.son_tools.found_house_essence
    require_essence(call, cost)
    try:
        house = await found_house_by_hand(call.tick, mortal.id)
    except AeronaError as error:
        fail(SonResult.WORK_REFUSED, reason=error.message)
    call.spend_essence(cost)
    call.remember_creation(house.id)
    call.target(house.id)
    await call.record(
        "tools.son.found_house",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: house.id, IncidentRole.TARGET: mortal.id},
        facts={"reason": args.reason},
        kind=ChronicleKind.ASCENSION,
    )
    return result(SonResult.HOUSE_FOUNDED, house=house.name, mortal=mortal.name)


async def bless_host(call: SonCall, args: BlessHostInput) -> str:
    army = require_type(await require_canon(call.session, args.army_id), {EntityType.ARMY}, SonResult.NOT_AN_ARMY, id=args.army_id)
    await ensure_in_reach(call, army)
    cost = call.rules.son_tools.bless_host_essence
    require_essence(call, cost)
    amount = call.rules.son_tools.bless_host_amount
    try:
        await bless_army(call.tick, army.id, **{args.aspect.value: amount})
    except AeronaError as error:
        fail(SonResult.WORK_REFUSED, reason=error.message)
    call.spend_essence(cost)
    call.target(army.id)
    await call.record(
        "tools.son.bless_host",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.INSTRUMENT: army.id},
        facts={"aspect": str(args.aspect.value), "reason": args.reason},
        kind=ChronicleKind.WAR,
    )
    return result(SonResult.HOST_BLESSED, army=army.name, aspect=spoken(args.aspect), amount=amount)


def specs() -> list[ToolSpec[SonCall, Any]]:
    son = AgentKind.SON
    standard = son_standard_action
    sites = gate(Gate.POWER_SITES)
    return [
        ToolSpec(
            SonToolId.FORGE_LEY_LINE,
            son,
            ForgeLeyInput,
            ToolMeta(ActionKind.OTHER, standard, essence_cost=lambda rules: rules.son_tools.forge_ley_essence, rarity_gate=gate(Gate.RARE_TOOLS)),
            forge_ley_line,
        ),
        ToolSpec(
            SonToolId.ADD_SEASON,
            son,
            AddSeasonInput,
            ToolMeta(
                ActionKind.REORDER_SEASONS,
                lambda rules: rules.son_tools.reorder_seasons_ap,
                essence_cost=lambda rules: rules.son_tools.add_season_essence,
                rarity_gate=gate(Gate.RARE_TOOLS),
            ),
            add_season,
        ),
        ToolSpec(
            SonToolId.OPEN_ROAD,
            son,
            OpenRoadInput,
            ToolMeta(
                ActionKind.REPAIR_ROUTE,
                lambda rules: rules.son_tools.open_road_ap,
                essence_cost=lambda rules: rules.son_tools.open_road_essence,
                rarity_gate=gate(Gate.ROAD_OPENING),
            ),
            open_road,
        ),
        ToolSpec(
            SonToolId.RAISE_THRONE,
            son,
            ThroneInput,
            ToolMeta(
                ActionKind.CREATE_ENTITY,
                lambda rules: rules.son_tools.throne_ap,
                essence_cost=lambda rules: rules.son_tools.throne_essence,
                rarity_gate=sites,
            ),
            raise_throne,
        ),
        ToolSpec(
            SonToolId.LAY_MAGIC_SITE,
            son,
            MagicSiteInput,
            ToolMeta(ActionKind.CREATE_ENTITY, standard, essence_cost=lambda rules: rules.son_tools.magic_site_essence, rarity_gate=sites),
            lay_magic_site,
        ),
        ToolSpec(
            SonToolId.CARRY_SPECIES,
            son,
            CarrySpeciesInput,
            ToolMeta(ActionKind.INTRODUCE_SPECIES, standard, essence_cost=lambda rules: rules.son_tools.carry_species_essence),
            carry_species,
        ),
        ToolSpec(
            SonToolId.SEED_LIFE,
            son,
            SeedLifeInput,
            ToolMeta(
                ActionKind.CREATE_ENTITY,
                lambda rules: rules.son_tools.seed_life_ap,
                essence_cost=lambda rules: rules.son_tools.seed_life_essence,
                rarity_gate=gate(Gate.BIRTH_WORLD),
            ),
            seed_life,
        ),
        ToolSpec(
            SonToolId.CALL_UP_SOUL,
            son,
            CallUpSoulInput,
            ToolMeta(ActionKind.CREATE_ENTITY, standard, essence_cost=lambda rules: rules.son_tools.call_up_soul_essence),
            call_up_soul,
        ),
        ToolSpec(
            SonToolId.CROWN_RULER,
            son,
            CommunityInput,
            ToolMeta(ActionKind.CROWN_RULER, standard, essence_cost=lambda rules: rules.son_tools.crown_ruler_essence),
            crown_ruler,
        ),
        ToolSpec(
            SonToolId.FOUND_HOUSE,
            son,
            FoundHouseInput,
            ToolMeta(ActionKind.CREATE_ENTITY, standard, essence_cost=lambda rules: rules.son_tools.found_house_essence),
            found_house,
        ),
        ToolSpec(
            SonToolId.BLESS_HOST,
            son,
            BlessHostInput,
            ToolMeta(ActionKind.BLESS_ARMY, standard, essence_cost=lambda rules: rules.son_tools.bless_host_essence),
            bless_host,
        ),
    ]
