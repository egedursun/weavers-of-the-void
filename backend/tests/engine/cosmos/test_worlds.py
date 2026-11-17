import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ValidationFailedError
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.repositories.entities import EntityRepository
from aerona.db.repositories.sons import SonRepository
from aerona.db.tables.celestial import StarRow
from aerona.db.tables.economy import ResourceProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.lore import LexemeRow
from aerona.db.tables.routes import RouteRow
from aerona.domain.enums.chronicle import PartOfSpeech
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EngineKind, EntityFlag, EntityOrigin, EntityType
from aerona.domain.enums.society import ResourceMechanic
from aerona.domain.enums.travel import TravelMethod
from aerona.domain.enums.world import Atmosphere, Discovery, Gravity, StarType, WorldType
from aerona.domain.models.entity_stats import RegionStats
from aerona.engine.context import TickContext
from aerona.engine.cosmos.birth import BirthRequest, fits, process_world_birth
from aerona.engine.cosmos.discovery import mark_world_discovered
from aerona.engine.cosmos.worlds import (
    align_moons,
    assign_mirror_twin,
    cosmos_overview,
    declare_holy_world,
    forget_world,
    pair_mirrors,
)
from aerona.engine.primitives.physics import world_physics
from aerona.prompts.schemas.cosmos import (
    BirthLanguageOutput,
    BirthRegionOutput,
    BirthWordOutput,
    CosmicResourceOutput,
    NativeKind,
    NativeOutput,
    NewWorldOutput,
    OldGodOutput,
    PlacementChoice,
    SkyBodyOutput,
    UniqueResourceOutput,
)
from aerona.prompts.schemas.shared import NamingRuleOutput
from aerona.rules.registry import Rules
from tests.engine.cosmos.factories import Cosmos, make_entity, make_route, make_son, make_world


def birth_output(**changes: object) -> NewWorldOutput:
    base = NewWorldOutput(
        placement=PlacementChoice.EXISTING_STAR,
        type=WorldType.CRYSTAL,
        dialect=NamingRuleOutput(vowels="aeiou", consonants="klmnrstv", syllable_patterns=["CV", "CVC"], sample_names=["Kalim", "Tesra", "Vorun"]),
        name="Kelmira",
        language=BirthLanguageOutput(
            name="Kelmiran",
            subtype="native language",
            description="A ringing tongue.",
            words=[
                BirthWordOutput(word="kalo", meaning="light", kind=PartOfSpeech.NOUN, origin="old"),
                BirthWordOutput(word="vesti", meaning="glass", kind=PartOfSpeech.NOUN, origin="old"),
                BirthWordOutput(word="mornu", meaning="echo", kind=PartOfSpeech.NOUN, origin="old"),
            ],
        ),
        description="A world of prisms where light sings.",
        cosmology="Light remembers everything.",
        gravity=Gravity.HIGH,
        atmosphere=Atmosphere.THIN,
        time_factor=9.0,
        day="Its day lasts as long as an echo.",
        regions=[
            BirthRegionOutput(name="Kalesta", subtype="continent", description="Glass plains.", danger=30, fertility=60, magic=70, image_prompt="glass"),
            BirthRegionOutput(
                name="Moravin", subtype="archipelago", description="Islands of quartz.", danger=50, fertility=40, magic=40, image_prompt="quartz"
            ),
        ],
        sky=SkyBodyOutput(name="Tessaro", subtype="ring", description="A singing ring.", image_prompt="ring"),
        unique_resource=UniqueResourceOutput(
            name="Echo Salt",
            subtype="mineral",
            description="It hums.",
            rule="Only in silence.",
            mechanics=[ResourceMechanic.DECAYING, ResourceMechanic.SACRED],
            commodity=CommodityKind.LUXURIES,
            region_index=1,
            image_prompt="salt",
        ),
        cosmic_resource=CosmicResourceOutput(
            name="Starglass", description="Folding glass.", rule="Melt to fold.", side_effect="Eyes turn silver.", region_index=0, image_prompt="glass"
        ),
        old_god=OldGodOutput(name="Vesmorn", title="the Listener", domains="Glass/Sound", description="It listens.", attitude=-40, image_prompt="god"),
        natives=[NativeOutput(kind=NativeKind.PEOPLE, name="Kalesi", subtype="people", description="Glass folk.", region_index=1, image_prompt="folk")],
        image_prompt="orbit",
    )
    return base.model_copy(update=changes)


async def test_world_birth_creates_the_whole_world(ctx: TickContext, cosmos: Cosmos) -> None:
    son = await make_son(ctx.session, "Velan", cosmos.home.id)
    world = await process_world_birth(ctx, birth_output(), BirthRequest(creator_son_id=son.id))
    assert world.star_id == cosmos.star.id and world.world_type is WorldType.CRYSTAL
    assert world.time_factor == ctx.rules.world_physics.time_factor_max / 100
    assert world.phonology is not None and "k" in world.phonology.consonants
    entities = list(await ctx.session.scalars(select(EntityRow).where(EntityRow.world_id == world.id)))
    by_type = {entity.entity_type: entity for entity in entities}
    assert {EntityType.REGION, EntityType.CELESTIAL, EntityType.RESOURCE, EntityType.LANGUAGE, EntityType.PEOPLE} <= set(by_type)
    assert all(entity.origin is EntityOrigin.COSMOS for entity in entities)
    originals = await EntityRepository(ctx.session).with_flag(EntityFlag.ORIGINAL_RESOURCE)
    resource = originals[0]
    assert resource.name != "Echo Salt"
    assert EntityFlag.NAME_FROM_LANGUAGE in await EntityRepository(ctx.session).flags(resource.id)
    assert resource.resource_mechanic is ResourceMechanic.SACRED and resource.sacred_to_son_id == son.id
    deposit = next(entity for entity in entities if entity.engine_kind is EngineKind.COSMIC_TRAVEL_RESOURCE)
    assert deposit.name == "Starglass Deposit"
    cosmos_row = await CosmosRepository(ctx.session).require_cosmos()
    assert cosmos_row.travel_resource is not None and cosmos_row.travel_resource.name == "Starglass"
    words = list(await ctx.session.scalars(select(LexemeRow).where(LexemeRow.language_entity_id == by_type[EntityType.LANGUAGE].id)))
    assert len(words) == 3
    assert EntityFlag.NATIVE in await EntityRepository(ctx.session).flags(by_type[EntityType.PEOPLE].id)
    god = await ctx.session.scalar(select(ForeignGodRow).where(ForeignGodRow.world_id == world.id))
    assert god is not None and god.stance == -40
    assert son.current_world_id == world.id
    route = await ctx.session.scalar(select(RouteRow).where(RouteRow.world_b_id == world.id))
    assert route is not None and route.world_a_id == cosmos.home.id and not route.known


async def test_world_birth_needs_regions_and_a_name(ctx: TickContext, cosmos: Cosmos) -> None:
    with pytest.raises(ValidationFailedError):
        await process_world_birth(ctx, birth_output(regions=[]), BirthRequest())
    with pytest.raises(ValidationFailedError):
        await process_world_birth(ctx, birth_output(name=" "), BirthRequest())


async def test_world_birth_forced_type_mechanics_and_new_star(ctx: TickContext, cosmos: Cosmos) -> None:
    world = await process_world_birth(
        ctx, birth_output(cosmic_resource=None, old_god=None, natives=[]), BirthRequest(forced_type=WorldType.ASTEROID_BELT, new_star=True)
    )
    assert world.world_type is WorldType.ASTEROID_BELT and world.gravity is Gravity.LOW
    assert world.star_id != cosmos.star.id


def test_phoneme_fit() -> None:
    assert fits("Kalo", frozenset("kalo"))
    assert not fits("Zed", frozenset("kalo"))


async def test_prose_never_picks_a_star_only_typed_fields_do(ctx: TickContext, cosmos: Cosmos) -> None:
    output = birth_output(
        description="A world under a red giant.", day="A red giant fills the sky.", cosmology="", placement=PlacementChoice.NEW_STAR, star=None
    )
    world = await process_world_birth(ctx, output, BirthRequest())
    assert world.star_id == cosmos.star.id
    originals = await EntityRepository(ctx.session).with_flag(EntityFlag.ORIGINAL_RESOURCE)
    resource = originals[-1]
    profile = await ctx.session.get(ResourceProfileRow, resource.id)
    assert profile is not None and profile.commodity is CommodityKind.LUXURIES


async def test_world_physics_includes_world_type(rules: Rules, session: AsyncSession, cosmos: Cosmos) -> None:
    belt = await make_world(session, "Shards", WorldType.ASTEROID_BELT)
    belt.atmosphere = Atmosphere.THIN
    belt.gravity = Gravity.HIGH
    physics = world_physics(rules, belt)
    assert physics.capacity == pytest.approx(rules.world_physics.capacity_thin / 100 * rules.world_physics.asteroid_belt_capacity / 100)
    assert physics.war == rules.world_physics.martiality_high_gravity


async def test_mirror_twin_prefers_same_star(session: AsyncSession, cosmos: Cosmos) -> None:
    far = await make_world(session, "Far")
    mirror = await make_world(session, "Glassa", WorldType.MIRROR, star_id=cosmos.star.id)
    assert far.star_id is None
    twin = await assign_mirror_twin(session, mirror)
    assert twin is not None and twin.id == cosmos.home.id
    assert await pair_mirrors(session) == 0


async def test_holy_world_trampling_costs_relation(ctx: TickContext, cosmos: Cosmos) -> None:
    first = await make_son(ctx.session, "Velan", cosmos.home.id)
    second = await make_son(ctx.session, "Morak", cosmos.home.id)
    await declare_holy_world(ctx, first, cosmos.home)
    text = await declare_holy_world(ctx, second, cosmos.home)
    assert "trampling" in text and cosmos.home.patron_son_id == second.id
    assert await SonRepository(ctx.session).relation(first.id, second.id) == -ctx.rules.pantheon.holy_world_take_relation


async def test_forget_world_and_rules(ctx: TickContext, cosmos: Cosmos) -> None:
    other = await make_world(ctx.session, "Velmor")
    son = await make_son(ctx.session, "Velan", other.id)
    route = await make_route(ctx.session, cosmos.home.id, other.id)
    with pytest.raises(ValidationFailedError):
        await forget_world(ctx, cosmos.home.id, cosmos.creator.id)
    await forget_world(ctx, other.id, cosmos.creator.id)
    assert other.discovery is Discovery.FORGOTTEN and not route.active and son.current_world_id == cosmos.home.id


async def test_discovery_and_moons(ctx: TickContext, cosmos: Cosmos) -> None:
    legend = await make_world(ctx.session, "Mythra")
    legend.discovery = Discovery.LEGEND
    assert await mark_world_discovered(ctx, legend, method=TravelMethod.ANCIENT_GATE)
    assert legend.discovery is Discovery.KNOWN
    moon = await make_world(ctx.session, "Lunet")
    moon.parent_world_id = cosmos.home.id
    assert await align_moons(ctx.session) == 1 and moon.star_id == cosmos.star.id


async def test_overview_counts(ctx: TickContext, cosmos: Cosmos) -> None:
    await make_entity(ctx.session, "Coast", EntityType.REGION, RegionStats(), world_id=cosmos.home.id)
    overview = await cosmos_overview(ctx.session, ctx.rules, ctx.epoch)
    home = next(item for item in overview.worlds if item.world.id == cosmos.home.id)
    assert home.counts.regions == 1
    assert overview.quests.dead_star is False
    assert len(overview.types) == len(WorldType)


async def test_world_birth_honours_the_requested_star_type(ctx: TickContext, cosmos: Cosmos) -> None:
    world = await process_world_birth(ctx, birth_output(), BirthRequest(new_star=True, new_star_type=StarType.BLUE_GIANT))
    star = await ctx.session.get(StarRow, world.star_id)
    assert star is not None and star.id != cosmos.star.id and star.star_type is StarType.BLUE_GIANT
