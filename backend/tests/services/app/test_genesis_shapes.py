from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from sqlalchemy import select

from aerona.db.repositories.cosmos import CosmosDraft, CosmosRepository, CreatorDraft
from aerona.db.repositories.worlds import StarDraft, WorldDraft, WorldRepository
from aerona.db.session import Database
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.cosmography import RiftRow
from aerona.db.tables.cosmos import CosmosRow
from aerona.db.tables.routes import RouteRow
from aerona.domain.enums.cosmography import DimensionKind, GalaxyType, RiftCause
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.travel import TravelMethod
from aerona.domain.enums.world import CosmosShape, CosmosSize, StarType, WorldType
from aerona.domain.models.entity_stats import RegionStats
from aerona.domain.models.genesis import GenesisOutcome
from aerona.engine.cosmos.ladder import DimensionDraft, GalaxyDraft, create_dimension, create_galaxy, ensure_ladder
from aerona.rules.registry import Rules
from aerona.services.genesis_wizard import GenesisCommand, GenesisWizard, WizardInput, sanitize
from aerona.services.lore_ports import GenesisRequest, LorePorts
from aerona.services.player.ports import WorldCreationRequest
from tests.conftest import OpenDatabase
from tests.services.app.factories import make_entity, make_world

SEED = "A world grown from one plain idea."


@pytest.fixture
async def database(tmp_path: Path, open_database: OpenDatabase) -> AsyncIterator[Database]:
    database = open_database(tmp_path / "shapes.db")
    yield database
    await database.dispose()


class LayeringGenesis:
    def __init__(self, database: Database, rules: Rules) -> None:
        self.database = database
        self.rules = rules

    async def create(self, request: GenesisRequest) -> GenesisOutcome:
        async with self.database.write() as session:
            repository = CosmosRepository(session)
            cosmos = await repository.create(
                CosmosDraft(name="Genesis", rng_seed=1, lore_language=request.lore_language, seed_idea=request.seed, cosmology="", tone="", rules=self.rules)
            )
            await repository.create_creator(CreatorDraft(request.creator_name, 150, 50, 10, 50, 20))
            world = await make_world(session, "First")
            cosmos.primary_world_id = world.id
            await make_entity(session, "Vale", EntityType.REGION, world_id=world.id, stats=RegionStats(magic=0, danger=100))
            layered = request.settings is not None and request.settings.cosmos_shape is CosmosShape.LAYERED
            if not layered:
                return GenesisOutcome(world_id=world.id)
            await ensure_ladder(session, self.rules)
            dimension = await create_dimension(session, self.rules, DimensionDraft("Velun", DimensionKind.ASTRAL, 1))
            galaxy = await create_galaxy(session, self.rules, GalaxyDraft("Velun Galaxy", GalaxyType.SPIRAL, 1, dimension_id=dimension.id))
            return GenesisOutcome(world_id=world.id, layer_galaxy_id=galaxy.id)


class RealWorlds:
    def __init__(self, database: Database) -> None:
        self.database = database
        self.requests: list[WorldCreationRequest] = []

    async def create(self, request: WorldCreationRequest) -> int:
        self.requests.append(request)
        number = len(self.requests)
        async with self.database.write() as session:
            worlds = WorldRepository(session)
            star = await worlds.create_star(StarDraft(f"Sun {number}", StarType.YELLOW_DWARF, 70, 10.0 * number, 1.0, 1, None, request.galaxy_id))
            world = await worlds.create_world(
                WorldDraft(f"Further {number}", WorldType.ORDINARY, 1.0, f"further{number}", 0.4, 0.3, 0.0, 20, 1, star_id=star.id)
            )
            return world.id


class Counting:
    def __init__(self) -> None:
        self.calls: list[tuple[int, int | None]] = []

    async def awaken(self, count: int, world_id: int | None) -> list[int]:
        self.calls.append((count, world_id))
        return []


def wizard(database: Database, rules: Rules) -> tuple[GenesisWizard, RealWorlds]:
    worlds = RealWorlds(database)
    return GenesisWizard(database, rules, LorePorts(genesis=LayeringGenesis(database, rules), awakener=Counting(), worlds=worlds)), worlds


async def test_further_worlds_grow_from_the_seed_and_circle_their_own_suns(database: Database) -> None:
    rules = Rules()
    genesis, worlds = wizard(database, rules)
    await genesis.run(GenesisCommand("Aeron", SEED, wizard=WizardInput(cosmos="large", shape="many_suns", seed=SEED)))
    assert len(worlds.requests) == rules.setup_wizard.large_cosmos_worlds
    assert all(request.new_star and request.galaxy_id is None and SEED in request.inspiration for request in worlds.requests)
    assert not any("different" in request.inspiration for request in worlds.requests)


async def test_by_default_every_further_world_circles_the_first_sun(database: Database) -> None:
    genesis, worlds = wizard(database, Rules())
    await genesis.run(GenesisCommand("Aeron", SEED, wizard=WizardInput(cosmos="large", seed=SEED)))
    async with database.read() as session:
        cosmos = await session.get(CosmosRow, 1)
        home = await session.get(WorldRow, cosmos.primary_world_id if cosmos is not None else 0)
    assert home is not None and home.star_id is not None
    assert [(request.star_id, request.new_star, request.galaxy_id) for request in worlds.requests] == [(home.star_id, False, None)] * 2


async def test_a_layered_cosmos_births_its_further_worlds_in_the_layer_and_joins_them_by_a_rift(database: Database) -> None:
    genesis, worlds = wizard(database, Rules())
    await genesis.run(GenesisCommand("Aeron", SEED, wizard=WizardInput(cosmos="small", shape="layered", seed=SEED)))
    async with database.read() as session:
        cosmos = await session.get(CosmosRow, 1)
        rift = await session.scalar(select(RiftRow))
        route = await session.scalar(select(RouteRow).where(RouteRow.method == TravelMethod.DIMENSIONAL_RIFT))
        further = await session.scalar(select(WorldRow).where(WorldRow.name == "Further 1"))
    assert cosmos is not None and further is not None
    assert worlds.requests[0].galaxy_id is not None and "Velun" in worlds.requests[0].inspiration
    assert rift is not None and rift.world_id == cosmos.primary_world_id and rift.target_world_id == further.id
    assert rift.cause is RiftCause.CREATOR
    assert route is not None and {route.world_a_id, route.world_b_id} == {cosmos.primary_world_id, further.id}


async def test_the_shape_and_layer_only_hold_where_further_worlds_exist(database: Database) -> None:
    rules = Rules()
    single = sanitize(rules, WizardInput(cosmos="single", shape="layered", layer_kind="astral"))
    assert (single.cosmos_shape, single.layer_kind) == (CosmosShape.ONE_SUN, None)
    suns = sanitize(rules, WizardInput(cosmos="small", shape="many_suns", layer_kind="astral"))
    assert (suns.cosmos_shape, suns.layer_kind) == (CosmosShape.MANY_SUNS, None)
    layered = sanitize(rules, WizardInput(cosmos="small", shape="layered", layer_kind="prime"))
    assert (layered.cosmos_size, layered.layer_kind) == (CosmosSize.SMALL, None)
    chosen = sanitize(rules, WizardInput(cosmos="small", shape="layered", layer_kind="astral", sea_pct=150, moisture_pct=-300, world_type="lava"))
    assert (chosen.layer_kind, chosen.sea_pct, chosen.moisture_pct, chosen.world_type) == (DimensionKind.ASTRAL, 100, -100, WorldType.LAVA)
    assert sanitize(rules, WizardInput(world_type="nowhere", climate_era="", world_age="ancient")).world_type is None


async def test_the_first_world_danger_follows_its_pulled_regions(database: Database) -> None:
    genesis, _ = wizard(database, Rules())
    await genesis.run(GenesisCommand("Aeron", SEED, wizard=WizardInput(danger=0, seed=SEED)))
    async with database.read() as session:
        cosmos = await session.get(CosmosRow, 1)
        world = await session.get(WorldRow, cosmos.primary_world_id if cosmos is not None else 0)
    assert world is not None and world.danger == 50
