import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.bonds import endpoints_valid
from aerona.catalog.strata import hosts_for
from aerona.core.errors import ValidationFailedError
from aerona.db.repositories.bonds import BondRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.cosmography import CosmicBeingProfileRow, DimensionalEventRow, GalacticEventRow, GalacticStructureRow, RiftRow
from aerona.db.tables.economy import CommunityStockRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.faith import AfterlifeStratumRow
from aerona.db.tables.routes import JourneyRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.cosmography import (
    BeingAgenda,
    BeingKind,
    BeingPhase,
    ClusterKind,
    DimensionalEventKind,
    DimensionKind,
    GalacticEventKind,
    GalacticStructureKind,
    GalaxyAge,
    GalaxyType,
    RiftCause,
    RiftState,
    RouteScope,
    SkyObject,
)
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityFlag, EntityType
from aerona.domain.enums.faith import StratumKind
from aerona.domain.enums.society import KnowledgeBranch, NaturalLaw, SocialClass
from aerona.domain.enums.travel import JourneyEventKind, JourneyIntent, TravelMethod
from aerona.domain.models.entity_stats import ArmyStats, MortalStats, PeopleStats, SettlementStats
from aerona.domain.models.records import PassengerLine
from aerona.engine.context import TickContext
from aerona.engine.cosmos import control
from aerona.engine.cosmos.beings import Scene, answer_incursion, found_cult, mirror, send_home, serve, take_rule
from aerona.engine.cosmos.commerce import carry, news_delay
from aerona.engine.cosmos.dimensions import dimension_cults
from aerona.engine.cosmos.galaxies import advance_mergers, galaxy_cults, may_merge, reshape
from aerona.engine.cosmos.influence import signature_minerals
from aerona.engine.cosmos.kinds import GALAXY_TYPE_MECHANICS
from aerona.engine.cosmos.ladder import (
    NUCLEI,
    ClusterDraft,
    DimensionDraft,
    GalaxyDraft,
    create_cluster,
    create_dimension,
    create_galaxy,
    ensure_ladder,
    nucleus_weights,
)
from aerona.engine.cosmos.placement import Cosmography, Placement, hidden_sky, pull_of
from aerona.engine.cosmos.rifts import seal_near, tear_toward
from aerona.engine.cosmos.routes import RouteSpec, _knowledge_problem, open_route, provision
from aerona.engine.cosmos.starlife import star_lives
from aerona.engine.cosmos.strata import drawing_dimensions, host_strata
from aerona.engine.cosmos.voyages import crossing_text
from aerona.engine.environment.dangers import DangerScene, _cosmic
from aerona.engine.faith.judgement import strata_of
from aerona.engine.lore.rites import magic_factor
from aerona.engine.phases.doom import cosmic_items
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.knowledge import LawBook
from aerona.engine.primitives.ledger import DoomItem
from aerona.engine.primitives.stats import stat_or
from aerona.rules.registry import Rules
from aerona.rules.renames import canonical_key
from tests.engine.cosmos.factories import Cosmos, make_entity, make_region, make_route, make_son, make_world, teach, tick, tuned
from tests.engine.cosmos.test_cosmography import ground_of


async def home_cluster(ctx: TickContext, cosmos: Cosmos) -> Placement:
    await ensure_ladder(ctx.session, ctx.rules)
    return (await Cosmography.load(ctx.session)).place_world(cosmos.home)


async def people(ctx: TickContext, name: str, world_id: int, **stats: int) -> int:
    row = await make_entity(ctx.session, name, EntityType.PEOPLE, PeopleStats(population=1000, piety=50, **stats), world_id=world_id)
    return row.id


async def test_a_dying_galaxy_hurries_its_stars_through_their_stages(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    ctx = tick(session, tuned(rules, "star_life", dying_galaxy_life_pct=1))
    home = await home_cluster(ctx, cosmos)
    assert home.galaxy is not None
    home.galaxy.age_stage = GalaxyAge.DYING
    cosmos.star.lifecycle_clock = 10
    await session.flush()
    await star_lives(ctx)
    assert cosmos.star.lifecycle_clock == 8


async def test_merging_galaxies_break_their_arms_while_they_fall_together(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    ctx = tick(session, tuned(rules, "galaxies", merger_arm_break=100))
    home = await home_cluster(ctx, cosmos)
    assert home.galaxy is not None and home.cluster is not None
    small = await create_galaxy(session, ctx.rules, GalaxyDraft("Falling Wheel", GalaxyType.SPIRAL, ctx.epoch, cluster_id=home.cluster.id))
    small.merging_with_galaxy_id = home.galaxy.id
    await session.flush()
    cosmography = await Cosmography.load(session)
    await advance_mergers(ctx, cosmography, [cosmography.galaxies[small.id]])
    arms = [row for row in cosmography.structures.values() if row.galaxy_id == small.id and row.kind is GalacticStructureKind.SPIRAL_ARM]
    assert arms and all(row.ended_epoch == ctx.epoch for row in arms)


async def test_the_central_galaxy_of_a_cluster_draws_its_neighbours_into_mergers(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    ctx = tick(session, tuned(tuned(rules, "galaxies", merger_chance=10), "clusters", central_pull_pct=1000))
    home = await home_cluster(ctx, cosmos)
    assert home.galaxy is not None and home.cluster is not None
    near = await create_galaxy(session, ctx.rules, GalaxyDraft("Close Wheel", GalaxyType.SPIRAL, ctx.epoch, cluster_id=home.cluster.id, x=home.galaxy.x))
    near.y = home.galaxy.y
    await session.flush()
    cosmography = await Cosmography.load(session)
    central = cosmography.central_galaxy(home.cluster.id)
    assert central is not None and central.id == home.galaxy.id
    assert may_merge(ctx, cosmography, cosmography.galaxies[home.galaxy.id], cosmography.galaxies[near.id])


async def test_strata_lie_in_the_dimension_their_kind_fits_and_a_death_ruler_draws_the_dead(ctx: TickContext, cosmos: Cosmos) -> None:
    await ensure_ladder(ctx.session, ctx.rules)
    realm = await make_region(ctx.session, "Hall of Shades", cosmos.home.id)
    unhosted = AfterlifeStratumRow(realm_entity_id=realm.id, kind=StratumKind.COMMON, name="Old Plain", criteria={})
    ctx.session.add(unhosted)
    await ctx.session.flush()
    below = await create_dimension(ctx.session, ctx.rules, DimensionDraft("The Below", DimensionKind.UNDERWORLD, ctx.epoch))
    assert unhosted.dimension_id == below.id
    strata = await strata_of(ctx, realm, set())
    plain = next(row for row in strata if row.kind is StratumKind.COMMON)
    assert plain.dimension_id == below.id and DimensionKind.UNDERWORLD in hosts_for(plain.valence, plain.activity)
    son = await make_son(ctx.session, "Morrow", cosmos.home.id, domains=(Domain.DEATH, Domain.SEA))
    below.ruler_node_id = son.id
    await ctx.session.flush()
    assert await drawing_dimensions(ctx.session) == {below.id}
    assert await host_strata(ctx.session) == 0


async def test_a_dark_nebula_hides_the_sky_and_the_cluster_heat_and_zone_reach_the_routes(ctx: TickContext, cosmos: Cosmos) -> None:
    home = await home_cluster(ctx, cosmos)
    assert home.galaxy is not None and home.cluster is not None
    nebula = GalacticStructureRow(
        galaxy_id=home.galaxy.id, kind=GalacticStructureKind.DARK_NEBULA, name="Shade", x=0.0, y=0.0, radius=10.0, intensity=100, created_epoch=1, locked=[]
    )
    ctx.session.add(nebula)
    await ctx.session.flush()
    cosmos.star.structure_id = nebula.id
    home.cluster.medium_heat = 100
    await ctx.session.flush()
    rules = ctx.rules
    assert await hidden_sky(ctx.session, rules, cosmos.home.id) == rules.galactic_structures.dark_nebula_hide / 100
    placement = (await Cosmography.load(ctx.session)).place_world(cosmos.home)
    pull = pull_of(rules, placement)
    assert pull.delay >= rules.galactic_structures.dark_nebula_delay
    cool = pull_of(rules, Placement(placement.dimension, None, None, placement.galaxy, placement.structure, placement.star, placement.zone))
    assert pull.danger - cool.danger >= 100 // rules.clusters.heat_danger_per


async def test_the_minerals_of_the_heavens_lie_in_the_ground_of_their_worlds(ctx: TickContext, cosmos: Cosmos) -> None:
    home = await home_cluster(ctx, cosmos)
    assert home.galaxy is not None
    remnant = GalacticStructureRow(
        galaxy_id=home.galaxy.id,
        kind=GalacticStructureKind.SUPERNOVA_REMNANT,
        name="Ember",
        x=0.0,
        y=0.0,
        radius=10.0,
        intensity=100,
        created_epoch=1,
        locked=[],
    )
    ctx.session.add(remnant)
    await ctx.session.flush()
    cosmos.star.structure_id = remnant.id
    region = await make_region(ctx.session, "Starfall", cosmos.home.id)
    ctx.session.add(ground_of(region.id, cosmos.home.id, mineral_layers={}))
    await ctx.session.flush()
    assert await signature_minerals(ctx) == 1
    ground = await ctx.session.get(RegionEnvironmentRow, region.id)
    assert ground is not None and ground.mineral_layers
    assert await signature_minerals(ctx) == 0


async def test_rites_tear_rifts_beings_tear_toward_home_and_wards_seal_them(ctx: TickContext, cosmos: Cosmos) -> None:
    await ensure_ladder(ctx.session, ctx.rules)
    plane = await create_dimension(ctx.session, ctx.rules, DimensionDraft("Dream Sea", DimensionKind.DREAM, ctx.epoch))
    region = await make_region(ctx.session, "Torn Hill", cosmos.home.id)
    rift = await tear_toward(ctx, cosmos.home, region, RiftCause.BEING, home_id=plane.id)
    assert rift is not None and rift.dimension_id == plane.id and rift.cause is RiftCause.BEING
    veil = plane.veil
    sealed = await seal_near(ctx, region.id, None)
    assert sealed is not None and sealed.state is RiftState.SEALED and plane.veil == min(100, veil + ctx.rules.rifts.ward_veil)
    assert await seal_near(ctx, region.id, None) is None


async def test_a_banished_being_goes_home_and_a_bound_one_serves_its_binder(ctx: TickContext, cosmos: Cosmos) -> None:
    await ensure_ladder(ctx.session, ctx.rules)
    plane = await create_dimension(ctx.session, ctx.rules, DimensionDraft("Far Shore", DimensionKind.ASTRAL, ctx.epoch))
    yonder = await make_world(ctx.session, "Yonder")
    yonder.dimension_id = plane.id
    await ctx.session.flush()
    being = await control.call_being(ctx, BeingKind.BOUNDARY_KEEPER, cosmos.home.id, region_id=None, home_dimension_id=plane.id, name=None)
    profile = await ctx.session.get(CosmicBeingProfileRow, being.id)
    assert profile is not None
    await send_home(ctx, being, profile)
    assert being.world_id == yonder.id
    son = await make_son(ctx.session, "Binder", cosmos.home.id)
    await control.bind(ctx, being.id, son.id, son.name)
    before = son.essence
    assert await serve(ctx, await Cosmography.load(ctx.session), being, profile) == profile.might * ctx.rules.cosmic_beings.serve_pct // 100
    assert son.essence > before or profile.might * ctx.rules.cosmic_beings.serve_pct // 100 == 0


async def test_armies_answer_an_incursion_and_worship_founds_a_cult(ctx: TickContext, cosmos: Cosmos) -> None:
    await ensure_ladder(ctx.session, ctx.rules)
    region = await make_region(ctx.session, "Breach", cosmos.home.id)
    army = await make_entity(ctx.session, "Home Guard", EntityType.ARMY, ArmyStats(size=100000), world_id=cosmos.home.id)
    being = await control.call_being(ctx, BeingKind.SYSTEM_SCALE_BEING, cosmos.home.id, region_id=region.id, home_dimension_id=None, name=None)
    profile = await ctx.session.get(CosmicBeingProfileRow, being.id)
    assert profile is not None
    profile.phase = BeingPhase.INCURSION
    cosmography = await Cosmography.load(ctx.session)
    scene = Scene(ctx, cosmography, being, profile, cosmos.home, cosmography.place_world(cosmos.home), [region], ctx.rng("test"))
    assert await answer_incursion(scene, region)
    assert profile.phase is BeingPhase.ROAMING and stat_or(army, "size", 0) < 100000
    community = await ctx.session.get(type(army), await people(ctx, "Kneelers", cosmos.home.id))
    assert community is not None
    cult = await found_cult(ctx, being, community)
    assert cult is not None and cult.entity_type is EntityType.CULT
    assert await BondRepository(ctx.session).exists_between(cult.id, being.id, BondKind.WORSHIPS)
    assert await found_cult(ctx, being, community) is None


async def test_an_echo_befriends_its_mortal_and_a_sovereign_takes_its_plane(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    ctx = tick(session, tuned(rules, "cosmic_beings", echo_replace_chance=0, befriend_chance=100, rule_chance=100))
    await ensure_ladder(session, ctx.rules)
    mortal = await make_entity(session, "Ilsa", EntityType.MORTAL, MortalStats(hp=10), world_id=cosmos.home.id)
    echo = await control.call_being(ctx, BeingKind.MIRRORED_DOUBLE, cosmos.home.id, region_id=None, home_dimension_id=None, name=None)
    profile = await session.get(CosmicBeingProfileRow, echo.id)
    assert profile is not None
    profile.mirrored_entity_id = mortal.id
    cosmography = await Cosmography.load(session)
    await mirror(Scene(ctx, cosmography, echo, profile, cosmos.home, cosmography.place_world(cosmos.home), [], ctx.rng("echo")))
    assert await BondRepository(session).exists_between(mortal.id, echo.id, BondKind.COMPANION)
    plane = await create_dimension(session, ctx.rules, DimensionDraft("Throne Plane", DimensionKind.ELEMENTAL, ctx.epoch))
    sovereign = await control.call_being(ctx, BeingKind.DIMENSION_RULER, cosmos.home.id, region_id=None, home_dimension_id=plane.id, name=None)
    crowned = await session.get(CosmicBeingProfileRow, sovereign.id)
    assert crowned is not None
    assert await take_rule(ctx, await Cosmography.load(session), sovereign, crowned)
    assert plane.ruler_node_id == sovereign.id


async def test_trade_fills_no_more_than_the_route_holds_and_far_news_waits(ctx: TickContext, cosmos: Cosmos) -> None:
    other = await make_world(ctx.session, "Market World", star_id=cosmos.star.id)
    route = await make_route(ctx.session, cosmos.home.id, other.id)
    route.capacity = 7
    first = await make_entity(ctx.session, "Seller", EntityType.SETTLEMENT, SettlementStats(population=100), world_id=cosmos.home.id)
    second = await make_entity(ctx.session, "Buyer", EntityType.SETTLEMENT, SettlementStats(population=100), world_id=other.id)
    ctx.session.add(CommunityStockRow(community_entity_id=first.id, commodity=CommodityKind.GRAIN, quantity=100000))
    await ctx.session.flush()
    moved, _ = await carry(ctx, route, RouteScope.SYSTEM, first, second)
    assert moved == 7
    assert news_delay(ctx.rules, RouteScope.INTERDIMENSIONAL) == ctx.rules.cosmography.interdimensional_news_epochs


async def test_a_journey_takes_food_for_the_way_and_tells_what_it_crossed(ctx: TickContext, cosmos: Cosmos) -> None:
    await ensure_ladder(ctx.session, ctx.rules)
    traveller = await make_entity(ctx.session, "Wanderers", EntityType.PEOPLE, PeopleStats(population=1000), world_id=cosmos.home.id)
    ctx.session.add(CommunityStockRow(community_entity_id=traveller.id, commodity=CommodityKind.GRAIN, quantity=1))
    other = await make_world(ctx.session, "Far Field")
    route = await make_route(ctx.session, cosmos.home.id, other.id)
    await ctx.session.flush()
    journey = JourneyRow(
        traveller_entity_id=traveller.id,
        route_id=route.id,
        origin_world_id=cosmos.home.id,
        destination_world_id=other.id,
        intent=JourneyIntent.COLONY,
        population=1000,
        epochs_left=5,
        start_epoch=ctx.epoch,
        events=[],
        passengers=[PassengerLine(community_entity_id=traveller.id, social_class=SocialClass.FARMER, count=1000)],
        locked=[],
        scope=RouteScope.INTERGALACTIC,
    )
    await provision(ctx, journey, traveller)
    assert [event.kind for event in journey.events] == [JourneyEventKind.PROVISIONS, JourneyEventKind.PROVISIONS]
    assert any("no fresh or preserved food" in event.text for event in journey.events)
    assert journey.passengers[0].condition < 100
    assert "crossing" in await crossing_text(ctx, journey)


async def test_a_long_journey_with_fresh_stores_keeps_its_travellers_whole(ctx: TickContext, cosmos: Cosmos) -> None:
    await ensure_ladder(ctx.session, ctx.rules)
    traveller = await make_entity(ctx.session, "Orchard Folk", EntityType.PEOPLE, PeopleStats(population=100), world_id=cosmos.home.id)
    ctx.session.add(CommunityStockRow(community_entity_id=traveller.id, commodity=CommodityKind.FRUIT, quantity=100000))
    other = await make_world(ctx.session, "Green Reach")
    route = await make_route(ctx.session, cosmos.home.id, other.id)
    await ctx.session.flush()
    journey = JourneyRow(
        traveller_entity_id=traveller.id,
        route_id=route.id,
        origin_world_id=cosmos.home.id,
        destination_world_id=other.id,
        intent=JourneyIntent.COLONY,
        population=100,
        epochs_left=5,
        start_epoch=ctx.epoch,
        events=[],
        passengers=[PassengerLine(community_entity_id=traveller.id, social_class=SocialClass.FARMER, count=100)],
        locked=[],
        scope=RouteScope.INTERGALACTIC,
    )
    await provision(ctx, journey, traveller)
    assert journey.events == [] and journey.passengers[0].condition == 100


async def test_a_void_ark_needs_high_sky_lore_and_a_filament_lane_needs_a_filament(ctx: TickContext, cosmos: Cosmos) -> None:
    home = await home_cluster(ctx, cosmos)
    assert home.dimension is not None
    other = await make_world(ctx.session, "Lane End")
    with pytest.raises(ValidationFailedError):
        await open_route(ctx.session, ctx.rules, ctx.rng("lane"), ctx.epoch, RouteSpec(cosmos.home.id, other.id, TravelMethod.FILAMENT_LANE))
    filament = await create_cluster(ctx.session, ctx.rules, ClusterDraft("Thread of Light", ClusterKind.FILAMENT, ctx.epoch, dimension_id=home.dimension.id))
    assert home.cluster is not None
    home.cluster.dimension_id = None
    home.cluster.parent_cluster_id = filament.id
    other.galaxy_id = home.galaxy_id
    await ctx.session.flush()
    route = await open_route(ctx.session, ctx.rules, ctx.rng("lane2"), ctx.epoch, RouteSpec(cosmos.home.id, other.id, TravelMethod.FILAMENT_LANE))
    assert route.method is TravelMethod.FILAMENT_LANE
    sailors = await make_entity(ctx.session, "Sailors", EntityType.PEOPLE, PeopleStats(population=100), world_id=cosmos.home.id)
    await teach(ctx.session, sailors, KnowledgeBranch.SKY_NAVIGATION)
    ark = await make_route(ctx.session, cosmos.home.id, other.id, TravelMethod.VOID_ARK)
    problem = await _knowledge_problem(ctx.session, ctx.rules, sailors, ark)
    assert problem is not None and str(ctx.rules.cosmography.ark_sky_level) in problem


async def test_unmaking_beings_are_a_doom_of_their_own(ctx: TickContext, cosmos: Cosmos) -> None:
    await ensure_ladder(ctx.session, ctx.rules)
    being = await control.call_being(ctx, BeingKind.STAR_FEEDER, cosmos.home.id, region_id=None, home_dimension_id=None, name=None)
    profile = await ctx.session.get(CosmicBeingProfileRow, being.id)
    assert profile is not None
    profile.phase, profile.agenda = BeingPhase.MANIFEST, BeingAgenda.UNMAKE
    await ctx.session.flush()
    items = await cosmic_items(ctx)
    assert items[DoomItem.UNMAKERS] >= ctx.rules.cosmic_beings.unmake_doom > 0


async def test_cults_of_stars_galaxies_and_dimensions_rise_when_they_stir(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    ctx = tick(session, tuned(tuned(rules, "galaxies", cult_chance=100), "dimensions", cult_chance=100))
    home = await home_cluster(ctx, cosmos)
    assert home.galaxy is not None
    folk = await people(ctx, "Skywatchers", cosmos.home.id)
    session.add(
        GalacticEventRow(kind=GalacticEventKind.STARBURST, galaxy_id=home.galaxy.id, epoch=ctx.epoch, until_epoch=ctx.epoch, intensity=50, text="A burst.")
    )
    await session.flush()
    assert await galaxy_cults(ctx, await Cosmography.load(session)) == 1
    assert await EntityRepository(session).has_flag(folk, EntityFlag.WORSHIPS_GALAXY)
    plane = await create_dimension(session, ctx.rules, DimensionDraft("Bleeding Plane", DimensionKind.SHADOW, ctx.epoch))
    session.add(
        DimensionalEventRow(
            kind=DimensionalEventKind.BLEED,
            dimension_id=plane.id,
            world_id=cosmos.home.id,
            epoch=ctx.epoch,
            until_epoch=ctx.epoch,
            intensity=5,
            text="A bleed.",
        )
    )
    await session.flush()
    assert await dimension_cults(ctx, await Cosmography.load(session)) == 1
    assert await BondRepository(session).exists_between(folk, plane.id, BondKind.WORSHIPS)


async def test_the_god_turns_peoples_to_their_star_galaxy_or_any_dimension(ctx: TickContext, cosmos: Cosmos) -> None:
    home = await home_cluster(ctx, cosmos)
    assert home.galaxy is not None and home.dimension is not None
    folk = await people(ctx, "Turned", cosmos.home.id)
    assert await control.set_sky_worship(ctx, folk, SkyObject.STAR, True) == cosmos.star.name
    assert await EntityRepository(ctx.session).has_flag(folk, EntityFlag.WORSHIPS_STAR)
    assert await control.set_sky_worship(ctx, folk, SkyObject.GALAXY, True) == home.galaxy.name
    assert await control.set_sky_worship(ctx, folk, SkyObject.DIMENSION, True, home.dimension.id) == home.dimension.name
    assert await BondRepository(ctx.session).exists_between(folk, home.dimension.id, BondKind.WORSHIPS)
    await control.set_sky_worship(ctx, folk, SkyObject.STAR, False)
    assert not await EntityRepository(ctx.session).has_flag(folk, EntityFlag.WORSHIPS_STAR)
    sunless = await make_world(ctx.session, "Dark Rock")
    lost = await people(ctx, "Lost", sunless.id)
    with pytest.raises(ValidationFailedError):
        await control.set_sky_worship(ctx, lost, SkyObject.STAR, True)


async def test_the_heavens_reach_the_danger_of_regions_and_the_power_of_rites(ctx: TickContext, cosmos: Cosmos) -> None:
    await ensure_ladder(ctx.session, ctx.rules)
    plane = await create_dimension(ctx.session, ctx.rules, DimensionDraft("Hostile Deep", DimensionKind.ABYSSAL, ctx.epoch))
    plane.hostility = 100
    wild = await make_world(ctx.session, "Abyss World")
    wild.dimension_id = plane.id
    region = await make_region(ctx.session, "Deep Field", wild.id, magic=100)
    ground = ground_of(region.id, wild.id)
    ctx.session.add(ground)
    await ctx.session.flush()
    scene = DangerScene(await RegionAtlas.load(ctx.session), {region.id: ground}, {region.id: region}, {})
    await _cosmic(ctx.session, ctx.rules, scene)
    assert scene.derived[region.id]
    caster = await make_entity(ctx.session, "Seer", EntityType.MORTAL, MortalStats(hp=10), world_id=wild.id, location_id=region.id)
    assert await magic_factor(ctx, caster) > 1


async def test_a_converging_dimension_carries_its_laws_across(ctx: TickContext, cosmos: Cosmos) -> None:
    home = await home_cluster(ctx, cosmos)
    assert home.dimension is not None
    plane = await create_dimension(ctx.session, ctx.rules, DimensionDraft("Underneath", DimensionKind.UNDERWORLD, ctx.epoch))
    ctx.session.add(
        DimensionalEventRow(
            kind=DimensionalEventKind.CONVERGENCE,
            dimension_id=plane.id,
            other_dimension_id=home.dimension.id,
            epoch=ctx.epoch,
            until_epoch=ctx.epoch,
            intensity=90,
            text="They meet.",
        )
    )
    await ctx.session.flush()
    book = await LawBook.load(ctx.session)
    assert book.has(NaturalLaw.THE_DEAD_SPEAK, cosmos.home.id)


@pytest.mark.parametrize("galaxy_type", list(GalaxyType), ids=lambda value: value.value)
async def test_every_galaxy_type_is_born_with_arms_and_a_nucleus_from_its_own_table(ctx: TickContext, cosmos: Cosmos, galaxy_type: GalaxyType) -> None:
    kind = GALAXY_TYPE_MECHANICS[galaxy_type]
    low, high = kind.arms_min(ctx.rules), kind.arms_max(ctx.rules)
    weights = dict(zip(NUCLEI, nucleus_weights(ctx.rules, galaxy_type), strict=True))
    assert low <= high and sum(weights.values()) > 0
    born = [await create_galaxy(ctx.session, ctx.rules, GalaxyDraft(f"{galaxy_type.value} {index}", galaxy_type, ctx.epoch)) for index in range(16)]
    assert all(low <= row.arm_count <= high for row in born)
    assert all(weights[row.nucleus] > 0 for row in born)
    if high > low:
        assert len({row.arm_count for row in born}) > 1


async def test_a_galaxy_that_becomes_elliptical_loses_its_arms_and_bar(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    ctx = tick(session, rules)
    home = await home_cluster(ctx, cosmos)
    assert home.galaxy is not None
    home.galaxy.galaxy_type = GalaxyType.ELLIPTICAL
    cosmography = await Cosmography.load(session)
    reshape(ctx, cosmography, cosmography.galaxies[home.galaxy.id])
    assert home.galaxy.arm_count == rules.galaxy_types.elliptical_arms_max
    left = [row for row in cosmography.structures.values() if row.galaxy_id == home.galaxy.id and row.kind is GalacticStructureKind.SPIRAL_ARM]
    assert all(row.ended_epoch == ctx.epoch for row in left)


def test_an_old_fixed_arm_count_carries_over_as_the_most_arms() -> None:
    assert canonical_key("galaxy_types", "spiral_arms") == ("galaxy_types", "spiral_arms_max")


async def test_a_rite_whose_backlash_leaks_can_tear_a_rift(ctx: TickContext, cosmos: Cosmos) -> None:
    await ensure_ladder(ctx.session, ctx.rules)
    await create_dimension(ctx.session, ctx.rules, DimensionDraft("Thin Plane", DimensionKind.ETHEREAL, ctx.epoch))
    region = await make_region(ctx.session, "Scorched Circle", cosmos.home.id)
    rift = await tear_toward(ctx, cosmos.home, region, RiftCause.RITE_BACKLASH, by_node_id=region.id)
    assert rift is not None and rift.cause is RiftCause.RITE_BACKLASH
    assert list(await ctx.session.scalars(select(RiftRow.cause))) == [RiftCause.RITE_BACKLASH]


@pytest.mark.parametrize(
    ("kind", "subject", "target"),
    [
        (BondKind.COMPANION, EntityType.MORTAL, EntityType.COSMIC_BEING),
        (BondKind.WORSHIPS, EntityType.PEOPLE, EntityType.COSMIC_BEING),
        (BondKind.WORSHIPS, EntityType.CULT, EntityType.COSMIC_BEING),
        (BondKind.DESCENDS_FROM, EntityType.CULT, EntityType.PEOPLE),
        (BondKind.COMMANDS, EntityType.MORTAL, EntityType.COSMIC_BEING),
    ],
)
def test_every_bond_the_beings_make_is_one_the_bond_book_allows(kind: BondKind, subject: EntityType, target: EntityType) -> None:
    assert endpoints_valid(kind, subject, target)
