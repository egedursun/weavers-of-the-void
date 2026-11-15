from sqlalchemy import select

from aerona.catalog.stars import STAR_TYPES
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import SkyEventRow, StarRow
from aerona.db.tables.physics import WorldPhysicsRow
from aerona.db.tables.routes import JourneyRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.economy import ExtractionKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.intervention import Disaster
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.son import SonStatus
from aerona.domain.enums.travel import JourneyEventKind, JourneyIntent, JourneyStatus, RouteClosure, RouteState, TravelMethod
from aerona.domain.enums.world import HorrorEventKind, SkyEventKind, StarType, WorldType
from aerona.domain.models.entity_stats import MortalStats, PeopleStats
from aerona.engine.context import TickContext
from aerona.engine.cosmos.leak import leak_delta
from aerona.engine.cosmos.orbits import eclipse_period
from aerona.engine.cosmos.routes import RouteBook, RouteSpec, can_use_route, open_route, sky_calendar
from aerona.engine.cosmos.star_types import brightness_band
from aerona.engine.cosmos.stars import StarSpec, create_star, rekindle_star, supernova
from aerona.engine.cosmos.world_views import default_view, view_of
from aerona.engine.economy.extraction import world_share
from aerona.engine.environment.book import active_sky
from aerona.engine.phases.afterlife import void_storm
from aerona.engine.phases.climate import star_instability
from aerona.engine.phases.disasters import DisasterWorld
from aerona.engine.phases.horror import _sanity_context, horror_event
from aerona.engine.phases.sky import SkyOrder, sky_event, spontaneous_bag, star_event_weight
from aerona.engine.phases.travel import bridge_collapse
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.physics import PhysicsTable
from aerona.rules.registry import Rules
from tests.engine.cosmos.factories import Cosmos, make_entity, make_region, make_route, make_son, make_world, tick, tuned


async def test_a_new_star_is_kindled_inside_its_type_band(ctx: TickContext, cosmos: Cosmos) -> None:
    for star_type in (StarType.BROWN_DWARF, StarType.BLUE_SUPERGIANT, StarType.BLACK_HOLE):
        star = await create_star(ctx.session, ctx.rules, ctx.rng(f"band.{star_type}"), ctx.epoch, StarSpec(star_type.value, star_type, 40, 55))
        low, high = brightness_band(ctx.rules, star_type)
        assert low <= star.brightness <= high


async def test_a_supernova_leaves_the_remnant_of_its_type(ctx: TickContext, cosmos: Cosmos) -> None:
    cosmos.star.star_type = StarType.BLUE_SUPERGIANT
    await supernova(ctx, cosmos.star)
    assert cosmos.star.star_type is STAR_TYPES[StarType.BLUE_SUPERGIANT].remnant is StarType.BLACK_HOLE
    assert cosmos.star.brightness == 0


async def test_star_light_sets_the_life_capacity_of_its_worlds(ctx: TickContext, cosmos: Cosmos) -> None:
    base = (await PhysicsTable.load(ctx.session, ctx.rules)).of(cosmos.home.id).capacity
    cosmos.star.star_type = StarType.BLACK_HOLE
    dark = (await PhysicsTable.load(ctx.session, ctx.rules)).of(cosmos.home.id).capacity
    assert dark < base


async def test_watching_and_chained_stars_move_the_leak(ctx: TickContext, cosmos: Cosmos) -> None:
    knowledge = await KnowledgeMap.load(ctx.session)
    old_epoch = cosmos.home.created_epoch + ctx.rules.deep_world.young_world_epochs + 1
    cosmos.star.star_type = StarType.WATCHING_STAR
    watched = await leak_delta(ctx.session, ctx.rules, cosmos.home, old_epoch, 0.0, knowledge=knowledge)
    assert watched.items["star"] == ctx.rules.star_types.watching_star_leak
    cosmos.star.star_type = StarType.CHAINED_STAR
    chained = await leak_delta(ctx.session, ctx.rules, cosmos.home, old_epoch, 0.0, knowledge=knowledge)
    assert chained.items["star's hold"] == -ctx.rules.star_types.chained_star_leak_repair


async def test_a_watching_star_erodes_the_sanity_beneath_it(ctx: TickContext, cosmos: Cosmos) -> None:
    calm = (await _sanity_context(ctx, await KnowledgeMap.load(ctx.session))).void_erosion[cosmos.home.id]
    cosmos.star.star_type = StarType.WATCHING_STAR
    await ctx.session.flush()
    watched = (await _sanity_context(ctx, await KnowledgeMap.load(ctx.session))).void_erosion[cosmos.home.id]
    assert watched == calm + ctx.rules.star_types.watching_star_sanity_erosion


async def test_a_variable_star_shortens_the_climate_ages(ctx: TickContext, cosmos: Cosmos) -> None:
    assert await star_instability(ctx, cosmos.home) == 0
    cosmos.star.star_type = StarType.VARIABLE_STAR
    assert await star_instability(ctx, cosmos.home) == ctx.rules.star_types.variable_star_instability


async def test_collapse_and_flare_weights_pick_the_star(ctx: TickContext, cosmos: Cosmos) -> None:
    cosmos.star.star_type = StarType.YELLOW_DWARF
    assert star_event_weight(ctx.rules, SkyEventKind.SUPERNOVA, cosmos.star) == 0
    cosmos.star.star_type = StarType.HYPERGIANT
    assert star_event_weight(ctx.rules, SkyEventKind.SUPERNOVA, cosmos.star) == ctx.rules.star_types.hypergiant_collapse_weight
    cosmos.star.star_type = StarType.RED_DWARF
    assert star_event_weight(ctx.rules, SkyEventKind.FLARE, cosmos.star) == ctx.rules.star_types.red_dwarf_flare_weight > 1


async def test_a_flare_scorches_fields_omens_and_sails(ctx: TickContext, cosmos: Cosmos) -> None:
    region = await make_region(ctx.session, "Dun", cosmos.home.id, fertility=50)
    people = await make_entity(ctx.session, "Tarn", EntityType.PEOPLE, PeopleStats(population=500, piety=10), world_id=cosmos.home.id, location_id=region.id)
    other = await make_world(ctx.session, "Velmor")
    sail = await make_route(ctx.session, cosmos.home.id, other.id, TravelMethod.LIGHT_SAIL)
    sail.bound_star_id = cosmos.star.id
    flare_ctx = tick(ctx.session, tuned(ctx.rules, "sky", flare_sail_scorch_chance=100))
    result = await sky_event(flare_ctx, SkyEventKind.FLARE, SkyOrder(star_id=cosmos.star.id))
    assert "flared" in result.text
    assert region.stats.fertility == 50 - ctx.rules.sky.flare_fertility_loss
    aurora = cosmos.home.magnetism // 2 * ctx.rules.orbits.aurora_piety_pct // 100
    assert people.stats.piety == 10 + ctx.rules.sky.flare_piety_gain + aurora
    assert not sail.active and sail.closure is RouteClosure.SCORCHED
    assert sail.temp_closed_until_epoch == ctx.epoch + ctx.rules.sky.flare_sail_epochs
    book = await RouteBook.load(ctx.session, ctx.rules, ctx.epoch)
    assert book.status(sail).state is RouteState.SCORCHED


async def test_sky_events_end_and_star_events_reach_every_world_of_the_star(ctx: TickContext, cosmos: Cosmos) -> None:
    moon = await make_world(ctx.session, "Lune", star_id=cosmos.star.id)
    await sky_event(ctx, SkyEventKind.ECLIPSE, SkyOrder(world_id=cosmos.home.id))
    await sky_event(ctx, SkyEventKind.FLARE, SkyOrder(star_id=cosmos.star.id))
    now = await active_sky(ctx.session, ctx.epoch)
    assert SkyEventKind.FLARE in now[cosmos.home.id] and SkyEventKind.FLARE in now[moon.id]
    later = await active_sky(ctx.session, ctx.epoch + 1)
    assert SkyEventKind.ECLIPSE not in later.get(cosmos.home.id, frozenset())
    assert SkyEventKind.FLARE not in later.get(moon.id, frozenset())


async def test_a_black_sun_lasts_until_its_star_is_rekindled(ctx: TickContext, cosmos: Cosmos) -> None:
    await sky_event(ctx, SkyEventKind.BLACK_SUN, SkyOrder(star_id=cosmos.star.id))
    assert SkyEventKind.BLACK_SUN in (await active_sky(ctx.session, ctx.epoch + 20))[cosmos.home.id]
    later = tick(ctx.session, ctx.rules, epoch=ctx.epoch + 3)
    await rekindle_star(later, cosmos.star.id, "The Creator")
    row = await ctx.session.scalar(select(SkyEventRow).where(SkyEventRow.kind == SkyEventKind.BLACK_SUN))
    assert row is not None and row.until_epoch == ctx.epoch + 3
    assert SkyEventKind.BLACK_SUN not in (await active_sky(ctx.session, ctx.epoch + 4)).get(cosmos.home.id, frozenset())


async def test_a_magnetar_makes_its_light_sails_dangerous(ctx: TickContext, cosmos: Cosmos) -> None:
    rules = tuned(ctx.rules, "travel", route_danger_die=1, route_danger_shift=1)
    other = await make_world(ctx.session, "Velmor")
    calm = await open_route(ctx.session, rules, ctx.rng("calm"), ctx.epoch, RouteSpec(cosmos.home.id, other.id, TravelMethod.LIGHT_SAIL))
    calm_danger = calm.danger
    calm.active = False
    cosmos.star.star_type = StarType.MAGNETAR
    wild = await open_route(ctx.session, rules, ctx.rng("wild"), ctx.epoch, RouteSpec(cosmos.home.id, other.id, TravelMethod.LIGHT_SAIL))
    assert wild.danger == calm_danger + ctx.rules.star_types.magnetar_sail_danger


async def test_the_dimming_drinks_the_light_of_the_star(ctx: TickContext, cosmos: Cosmos) -> None:
    before = cosmos.star.brightness
    text = await horror_event(ctx, HorrorEventKind.THE_DIMMING, cosmos.home)
    assert text is not None and cosmos.star.brightness == before - ctx.rules.cosmic_horror.dimming_brightness_loss
    cosmos.star.star_type = StarType.DEAD_STAR
    assert await horror_event(ctx, HorrorEventKind.THE_DIMMING, cosmos.home) is None


async def test_whispers_from_beyond_teach_forbidden_knowledge(ctx: TickContext, cosmos: Cosmos) -> None:
    sage = await make_entity(ctx.session, "Ilsa", EntityType.MORTAL, MortalStats(intellect=90), world_id=cosmos.home.id)
    await make_entity(ctx.session, "Bram", EntityType.MORTAL, MortalStats(intellect=20), world_id=cosmos.home.id)
    text = await horror_event(ctx, HorrorEventKind.WHISPERS_FROM_BEYOND, cosmos.home)
    assert text is not None and "Ilsa" in text
    knowledge = await KnowledgeMap.load(ctx.session)
    assert knowledge.knows(sage.id, KnowledgeBranch.FORBIDDEN)
    assert sage.sanity == ctx.rules.cosmic_horror.default_sanity - ctx.rules.cosmic_horror.whispers_sanity_loss


async def test_a_wormhole_throat_opens_and_shuts(ctx: TickContext, cosmos: Cosmos) -> None:
    other = await make_world(ctx.session, "Velmor")
    route = await make_route(ctx.session, cosmos.home.id, other.id, TravelMethod.WORMHOLE)
    shut = sky_calendar(tuned(ctx.rules, "travel_methods", wormhole_open_pct=0), ctx.epoch, None)
    open_ = sky_calendar(tuned(ctx.rules, "travel_methods", wormhole_open_pct=100), ctx.epoch, None)
    assert RouteBook([route], shut, set()).status(route).state is RouteState.UNSTABLE
    assert RouteBook([route], open_, set()).status(route).state is RouteState.OPEN
    calendar = sky_calendar(ctx.rules, ctx.epoch, None)
    states = {calendar.throat_open(route.id, epoch) for epoch in range(1, 60)}
    assert states == {True, False}


async def test_the_river_of_the_dead_flows_from_a_corpse_world(ctx: TickContext, cosmos: Cosmos) -> None:
    corpse = await make_world(ctx.session, "Godbody", WorldType.CORPSE_WORLD)
    river = await make_route(ctx.session, cosmos.home.id, corpse.id, TravelMethod.RIVER_OF_DEAD)
    people = await make_entity(ctx.session, "Tarn", EntityType.PEOPLE, PeopleStats(population=500), world_id=cosmos.home.id)
    problem = await can_use_route(ctx.session, ctx.rules, ctx.epoch, people, river)
    assert problem is None or "river" not in problem


async def test_a_collapsing_bridge_takes_its_travellers(ctx: TickContext, cosmos: Cosmos) -> None:
    other = await make_world(ctx.session, "Velmor")
    son = await make_son(ctx.session, "Velan", cosmos.home.id)
    bridge = await make_route(ctx.session, cosmos.home.id, other.id, TravelMethod.DIVINE_BRIDGE)
    bridge.builder_son_id = son.id
    son.status = SonStatus.ASLEEP
    people = await make_entity(ctx.session, "Tarn", EntityType.PEOPLE, PeopleStats(population=500), world_id=cosmos.home.id)
    journey = JourneyRow(
        traveller_entity_id=people.id,
        route_id=bridge.id,
        origin_world_id=cosmos.home.id,
        destination_world_id=other.id,
        intent=JourneyIntent.TRADE,
        epochs_left=1,
        start_epoch=1,
    )
    ctx.session.add(journey)
    await ctx.session.flush()
    fall = tick(ctx.session, tuned(ctx.rules, "travel_methods", bridge_collapse_loss_pct=100))
    assert await bridge_collapse(fall) == 1
    assert bridge.closure is RouteClosure.COLLAPSED and journey.status is JourneyStatus.LOST
    assert [event.kind for event in journey.events] == [JourneyEventKind.BRIDGE_COLLAPSED]
    book = await RouteBook.load(ctx.session, ctx.rules, ctx.epoch)
    assert book.status(bridge).state is RouteState.COLLAPSED


async def test_whispers_find_a_new_listener_each_time(ctx: TickContext, cosmos: Cosmos) -> None:
    sage = await make_entity(ctx.session, "Ilsa", EntityType.MORTAL, MortalStats(intellect=90), world_id=cosmos.home.id)
    pupil = await make_entity(ctx.session, "Bram", EntityType.MORTAL, MortalStats(intellect=20), world_id=cosmos.home.id)
    await horror_event(ctx, HorrorEventKind.WHISPERS_FROM_BEYOND, cosmos.home)
    second = await horror_event(ctx, HorrorEventKind.WHISPERS_FROM_BEYOND, cosmos.home)
    assert second is not None and "Bram" in second
    knowledge = await KnowledgeMap.load(ctx.session)
    assert knowledge.knows(sage.id, KnowledgeBranch.FORBIDDEN) and knowledge.knows(pupil.id, KnowledgeBranch.FORBIDDEN)
    bonds = list(await ctx.session.scalars(select(BondRow).where(BondRow.source_node_id == sage.id, BondRow.kind == BondKind.KNOWS)))
    assert len(bonds) == 1


async def test_iron_worlds_yield_more_ore_to_their_communities(ctx: TickContext, cosmos: Cosmos) -> None:
    cosmos.home.world_type = WorldType.IRON
    await ctx.session.flush()
    view = await view_of(ctx.session, ctx.rules, cosmos.home.id)
    assert world_share(ctx.rules, view, ExtractionKind.MINING) == ctx.rules.world_physics.iron_ore_yield / 100
    assert world_share(ctx.rules, await view_of(ctx.session, ctx.rules, None), ExtractionKind.MINING) == 1.0


async def test_nature_of_the_world_shapes_its_disasters(ctx: TickContext, cosmos: Cosmos) -> None:
    quaking = DisasterWorld(await ctx.laws(), {}, views={cosmos.home.id: default_view(ctx.rules, WorldType.CHTHONIAN)})
    assert quaking.nature_mult(ctx.rules, cosmos.home.id, Disaster.EARTHQUAKE) == ctx.rules.world_physics.chthonian_earthquake_pct / 100
    built = DisasterWorld(await ctx.laws(), {}, views={cosmos.home.id: default_view(ctx.rules, WorldType.GODS_PALACE)})
    assert built.nature_mult(ctx.rules, cosmos.home.id, Disaster.EARTHQUAKE) == 0


def test_a_great_eclipse_comes_sooner_under_many_suns(rules: Rules) -> None:
    physics = WorldPhysicsRow(eclipse_years=3)
    lone = eclipse_period(rules, physics, StarRow(star_type=StarType.YELLOW_DWARF))
    many = eclipse_period(rules, physics, StarRow(star_type=StarType.TRINARY))
    assert lone is not None and many is not None and many < lone
    assert eclipse_period(rules, WorldPhysicsRow(eclipse_years=0), StarRow(star_type=StarType.TRINARY)) is None
    assert not any(kind in spontaneous_bag(rules) for kind in (SkyEventKind.ECLIPSE, SkyEventKind.TRANSIT))


async def test_the_afterlife_void_storm_darkens_the_weather_of_both_ends(ctx: TickContext, cosmos: Cosmos) -> None:
    other = await make_world(ctx.session, "Velmor")
    await make_route(ctx.session, cosmos.home.id, other.id)
    storm = tick(ctx.session, tuned(ctx.rules, "beyond", void_storm_chance=100))
    assert await void_storm(storm) is not None
    sky = await active_sky(ctx.session, ctx.epoch)
    assert SkyEventKind.VOID_STORM in sky[cosmos.home.id] and SkyEventKind.VOID_STORM in sky[other.id]
