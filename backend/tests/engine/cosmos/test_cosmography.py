import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ValidationFailedError
from aerona.db.tables.cosmography import DimensionRow, GalaxyRow, PhenomenonProfileRow, RiftRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.routes import JourneyRow, RouteRow
from aerona.domain.enums.cosmography import (
    BeingKind,
    BeingPhase,
    ClusterKind,
    DimensionKind,
    GalaxyType,
    PhenomenonCause,
    PhenomenonKind,
    RiftCause,
    RiftState,
    RouteScope,
)
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import CoastKind, RiverClass, SoilKind, TemperatureBand, TerrainKind
from aerona.domain.enums.travel import JourneyIntent, JourneyStatus
from aerona.domain.models.entity_stats import PeopleStats
from aerona.domain.models.records import CargoLine
from aerona.engine.context import TickContext
from aerona.engine.cosmos import control
from aerona.engine.cosmos.beings import banish_near
from aerona.engine.cosmos.climate import ClimateTurn
from aerona.engine.cosmos.ladder import ClusterDraft, DimensionDraft, GalaxyDraft, create_cluster, create_dimension, create_galaxy, ensure_ladder
from aerona.engine.cosmos.placement import Cosmography
from aerona.engine.cosmos.rifts import leak_peaks, open_rift
from aerona.rules.registry import Rules
from tests.engine.cosmos.factories import Cosmos, make_entity, make_region, make_route, make_world, tick, tuned

GROUND_NUMBERS = (
    "elevation_mean",
    "roughness",
    "latitude",
    "moisture",
    "base_forest",
    "forest_cover",
    "base_wetland",
    "wetland",
    "soil_fertility",
    "soil_base",
    "temperature",
    "rainfall",
    "seasonality",
    "disease_load",
    "magic_density",
    "defensibility",
)


def ground_of(region_id: int, world_id: int, **values: object) -> RegionEnvironmentRow:
    return RegionEnvironmentRow(
        entity_id=region_id,
        world_id=world_id,
        dominant_terrain=TerrainKind.PLAIN,
        river_class=RiverClass.NONE,
        coast_kind=CoastKind.NONE,
        soil=SoilKind.LOAM,
        temperature_band=TemperatureBand.TEMPERATE,
        **dict.fromkeys(GROUND_NUMBERS, 50),
        **values,
    )


async def test_the_ladder_sets_every_star_into_the_prime_dimension_once(ctx: TickContext, cosmos: Cosmos) -> None:
    assert await ensure_ladder(ctx.session, ctx.rules) == 1
    placement = (await Cosmography.load(ctx.session)).place_world(cosmos.home)
    assert placement.dimension is not None and placement.dimension.dimension_kind is DimensionKind.PRIME
    assert placement.galaxy is not None and placement.cluster is not None
    assert cosmos.star.galaxy_id == placement.galaxy.id
    assert await ensure_ladder(ctx.session, ctx.rules) == 0
    assert len(list(await ctx.session.scalars(select(GalaxyRow)))) == 1


async def test_the_scale_between_two_worlds_names_the_route_scope(ctx: TickContext, cosmos: Cosmos) -> None:
    await ensure_ladder(ctx.session, ctx.rules)
    home = (await Cosmography.load(ctx.session)).place_world(cosmos.home)
    assert home.galaxy is not None and home.cluster is not None and home.dimension is not None
    neighbour = await create_galaxy(ctx.session, ctx.rules, GalaxyDraft("Near Wheel", GalaxyType.SPIRAL, ctx.epoch, cluster_id=home.cluster.id, x=3000.0))
    far_group = await create_cluster(ctx.session, ctx.rules, ClusterDraft("Far Wall", ClusterKind.WALL, ctx.epoch, dimension_id=home.dimension.id))
    far = await create_galaxy(ctx.session, ctx.rules, GalaxyDraft("Far Wheel", GalaxyType.ELLIPTICAL, ctx.epoch, cluster_id=far_group.id))
    plane = await create_dimension(ctx.session, ctx.rules, DimensionDraft("Astral Reach", DimensionKind.ASTRAL, ctx.epoch))
    sister = await make_world(ctx.session, "Sister", star_id=cosmos.star.id)
    rover = await make_world(ctx.session, "Rover")
    rover.galaxy_id = home.galaxy.id
    near = await make_world(ctx.session, "Nearer")
    near.galaxy_id = neighbour.id
    yonder = await make_world(ctx.session, "Yonder")
    yonder.galaxy_id = far.id
    astral = await make_world(ctx.session, "Astral")
    astral.dimension_id = plane.id
    await ctx.session.flush()
    ladder = await Cosmography.load(ctx.session)
    assert ladder.scope(cosmos.home, sister) is RouteScope.SYSTEM
    assert ladder.scope(cosmos.home, rover) is RouteScope.STELLAR
    assert ladder.scope(cosmos.home, near) is RouteScope.GALACTIC
    assert ladder.scope(cosmos.home, yonder) is RouteScope.INTERCLUSTER
    assert ladder.scope(cosmos.home, astral) is RouteScope.INTERDIMENSIONAL


async def test_a_dimension_sets_the_time_and_magic_of_its_worlds(ctx: TickContext, cosmos: Cosmos) -> None:
    await ensure_ladder(ctx.session, ctx.rules)
    plane = await create_dimension(ctx.session, ctx.rules, DimensionDraft("Slow Reach", DimensionKind.ASTRAL, ctx.epoch))
    await control.edit_dimension(ctx, plane.id, {"time_factor": 3.0, "magic": 60}, [])
    world = await make_world(ctx.session, "Slowland")
    await control.edit_world_life(ctx, world.id, {"dimension_id": plane.id}, [])
    ladder = await Cosmography.load(ctx.session)
    pull = ladder.pull(ctx.rules, ladder.place_world(world))
    assert pull.time == pytest.approx(3.0) and pull.magic >= 60
    assert {"time_factor", "magic"} <= set(plane.locked)
    with pytest.raises(ValidationFailedError):
        await control.edit_world_life(ctx, cosmos.home.id, {"dimension_id": plane.id}, [])


async def test_a_rift_opens_a_passage_and_a_seal_closes_it(ctx: TickContext, cosmos: Cosmos) -> None:
    await ensure_ladder(ctx.session, ctx.rules)
    plane = await create_dimension(ctx.session, ctx.rules, DimensionDraft("Astral Reach", DimensionKind.ASTRAL, ctx.epoch))
    far = await make_world(ctx.session, "Beyond")
    far.dimension_id = plane.id
    region = await make_region(ctx.session, "Torn Field", cosmos.home.id)
    await ctx.session.flush()
    rift = await open_rift(ctx, cosmos.home, region, plane, RiftCause.GOD, target_world=far)
    assert rift.state is RiftState.OPENING and rift.route_id is not None
    route = await ctx.session.get(RouteRow, rift.route_id)
    assert route is not None and route.world_b_id in {far.id, cosmos.home.id}
    with pytest.raises(ValidationFailedError):
        await open_rift(ctx, far, None, plane, RiftCause.GOD)
    sealed = await control.close_rift(ctx, rift.id, "Aeron")
    assert sealed.state is RiftState.SEALED
    assert (await ctx.session.scalar(select(RiftRow.id).where(RiftRow.id == rift.id))) == rift.id


async def test_a_ward_holds_a_phenomenon_back(ctx: TickContext, cosmos: Cosmos) -> None:
    region = await make_region(ctx.session, "Fogland", cosmos.home.id)
    body = await control.new_phenomenon(ctx, PhenomenonKind.LIVING_FOG, region.id, 60, PhenomenonCause.DIVINE)
    profile = await control.ward_phenomenon(ctx, body.id, 30, "Aeron")
    assert profile.containment >= 30
    footprint = await control.set_footprint(ctx, body.id, region.id, None)
    assert footprint is None


async def test_turning_a_region_moves_its_climate_shift(ctx: TickContext, cosmos: Cosmos) -> None:
    region = await make_region(ctx.session, "Coldfield", cosmos.home.id)
    ctx.session.add(ground_of(region.id, cosmos.home.id))
    await ctx.session.flush()
    await control.turn_climate(ctx, region.id, ClimateTurn.WARMER, "Aeron")
    await control.turn_climate(ctx, region.id, ClimateTurn.DRIER, "Aeron")
    ground = await ctx.session.get(RegionEnvironmentRow, region.id)
    assert ground is not None
    assert ground.temperature_shift == ctx.rules.world_life.imposed_shift
    assert ground.rainfall_shift == -ctx.rules.world_life.imposed_shift


async def test_a_held_load_stays_on_the_voyage(ctx: TickContext, cosmos: Cosmos) -> None:
    other = await make_world(ctx.session, "Harbour")
    route = await make_route(ctx.session, cosmos.home.id, other.id)
    trader = await make_entity(ctx.session, "Tarn", EntityType.PEOPLE, PeopleStats(population=500), world_id=cosmos.home.id)
    journey = JourneyRow(
        traveller_entity_id=trader.id,
        route_id=route.id,
        origin_world_id=cosmos.home.id,
        destination_world_id=other.id,
        intent=JourneyIntent.TRADE,
        population=10,
        epochs_left=2,
        status=JourneyStatus.UNDERWAY,
        start_epoch=ctx.epoch,
        events=[],
    )
    ctx.session.add(journey)
    await ctx.session.flush()
    loaded = await control.load_journey(ctx, journey.id, convoy=3, escorts=2, cargo=[CargoLine(commodity=CommodityKind.GRAIN, amount=40)], passengers=None)
    assert (loaded.convoy, loaded.escorts) == (3, 2)
    assert {"convoy", "escorts", "cargo"} <= set(loaded.locked)
    with pytest.raises(ValidationFailedError):
        await control.load_journey(ctx, journey.id, convoy=0, escorts=None, cargo=None, passengers=None)
    released = await control.release_journey(ctx, journey.id, ["cargo"])
    assert "cargo" not in released.locked and "convoy" in released.locked


async def test_a_called_being_can_be_bound_and_banished(ctx: TickContext, cosmos: Cosmos) -> None:
    await ensure_ladder(ctx.session, ctx.rules)
    being = await control.call_being(ctx, BeingKind.DIMENSION_WALKER, cosmos.home.id, region_id=None, home_dimension_id=None, name=None)
    bound = await control.bind(ctx, being.id, cosmos.creator.id, "Aeron")
    assert bound.phase is BeingPhase.BOUND
    banished = await control.banish(ctx, being.id, "Aeron")
    assert banished.phase is BeingPhase.BANISHED
    assert await ctx.session.get(DimensionRow, banished.home_dimension_id or 0) is not None or banished.home_dimension_id is None


async def test_a_ward_of_enough_power_drives_a_manifest_being_home(ctx: TickContext, cosmos: Cosmos) -> None:
    await ensure_ladder(ctx.session, ctx.rules)
    region = await make_region(ctx.session, "Haunted Vale", cosmos.home.id)
    being = await control.call_being(ctx, BeingKind.DIMENSION_WALKER, cosmos.home.id, region_id=region.id, home_dimension_id=None, name=None)
    profile = await control.edit_being(ctx, being.id, {"phase": "manifest"}, [])
    assert profile.phase is BeingPhase.MANIFEST
    assert await banish_near(ctx, region.id, "Aeron") == being.name
    assert profile.phase is BeingPhase.BANISHED
    assert await banish_near(ctx, region.id, "Aeron") is None


async def test_a_region_at_its_leak_peak_forms_a_leak_wound(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    ctx = tick(session, tuned(tuned(rules, "phenomena", leak_peak_chance=100), "rifts", peak_chance=0))
    await ensure_ladder(session, ctx.rules)
    region = await make_region(session, "Thin Place", cosmos.home.id)
    session.add(ground_of(region.id, cosmos.home.id, leak=ctx.rules.rifts.leak_peak))
    await session.flush()
    assert await leak_peaks(ctx, await Cosmography.load(session)) == 0
    kinds = list(await session.scalars(select(PhenomenonProfileRow.kind)))
    assert kinds == [PhenomenonKind.LEAK_WOUND]
