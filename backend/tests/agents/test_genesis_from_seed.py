import copy
from pathlib import Path
from typing import Any

from sqlalchemy import select

from aerona.agents.awakening import creation_settings_text
from aerona.agents.context.creation import creation_text
from aerona.agents.context.scope import load_scope
from aerona.agents.genesis import GenesisRequest, genesis
from aerona.agents.runtime import AgentRuntime
from aerona.catalog.worlds import WORLD_TYPES
from aerona.db.session import Database
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.cosmography import DimensionRow, GalaxyRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import ChronicleRow
from aerona.domain.enums.cosmography import DimensionKind, WorldAge
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.world import ClimateEra, CosmosShape, CosmosSize, Gravity, LoreLanguage, StarType, WorldType
from aerona.domain.models.genesis import GenesisOutcome, GenesisSettings
from aerona.prompts import PromptId, output_model
from aerona.rules.registry import Rules
from tests.agents.fakes import FakeModel
from tests.conftest import OpenDatabase
from tests.prompts.payloads import PAYLOADS

LAYER = {"name": "Velun", "kind": "astral", "description": "It lies beside the first world."}


def scripted(extra: dict[str, Any] | None = None) -> FakeModel:
    data = copy.deepcopy(PAYLOADS[PromptId.GENESIS_USER])
    data["sons"] = [{**data["sons"][index], "name": name} for index, name in enumerate(("Ozzeh", "Varum", "Kessa"))]
    data.update(extra or {})
    model = FakeModel()
    model.script(output_model(PromptId.GENESIS_USER), output_model(PromptId.GENESIS_USER).model_validate(data))
    return model


async def create(database: Database, rules: Rules, model: FakeModel, settings: GenesisSettings | None) -> GenesisOutcome:
    runtime = AgentRuntime(database=database, model=model, rules_override=rules)
    return await genesis(runtime, GenesisRequest("Aeron", "a salt lake", LoreLanguage.ENGLISH, 7, settings=settings), rules)


async def test_the_seed_shapes_the_first_world_and_regions_keep_the_model_values(tmp_path: Path, rules: Rules, open_database: OpenDatabase) -> None:
    database = open_database(tmp_path / "seeded.db")
    settings = GenesisSettings(magic=100, danger=100, peoples=2)
    outcome = await create(database, rules, scripted(), settings)
    async with database.read() as session:
        world = await session.get(WorldRow, outcome.world_id)
        region = await session.scalar(select(EntityRow).where(EntityRow.entity_type == EntityType.REGION))
        line = await session.scalar(select(ChronicleRow.text).where(ChronicleRow.text.contains("Aeron")).order_by(ChronicleRow.id))
    await database.dispose()
    assert world is not None and region is not None
    assert (world.world_type, world.terrain_sea, world.terrain_mountains, world.terrain_humidity) == (WorldType.ORDINARY, 0.4, 0.3, 0.1)
    assert (world.climate_era, world.age_stage) == (ClimateEra.TEMPERATE, WorldAge.YOUNG)
    assert world.climate_epochs_left is not None and world.climate_epochs_left >= rules.climate_effects.first_duration
    assert region.stats.model_dump()["magic"] == PAYLOADS[PromptId.GENESIS_USER]["regions"][0]["magic"]
    assert region.stats.model_dump()["danger"] == PAYLOADS[PromptId.GENESIS_USER]["regions"][0]["danger"]
    assert line is not None and "named the void" not in line and "lands and waters" not in line
    assert outcome.layer_galaxy_id is None


async def test_the_first_world_is_born_with_its_sun_as_one_system(tmp_path: Path, rules: Rules, open_database: OpenDatabase) -> None:
    database = open_database(tmp_path / "system.db")
    outcome = await create(database, rules, scripted(), None)
    async with database.read() as session:
        world = await session.get(WorldRow, outcome.world_id)
        star = await session.get(StarRow, world.star_id if world is not None else 0)
        galaxy = await session.scalar(select(GalaxyRow).order_by(GalaxyRow.id))
        line = await session.scalar(select(ChronicleRow.text).where(ChronicleRow.text.contains("around the star")))
    await database.dispose()
    assert world is not None and star is not None
    assert (star.name, star.star_type) == ("Ivar", StarType.RED_DWARF)
    assert galaxy is not None and star.galaxy_id == galaxy.id
    assert line is not None and "Ivar" in line


async def test_the_player_choices_override_the_seed_for_the_first_world(tmp_path: Path, rules: Rules, open_database: OpenDatabase) -> None:
    database = open_database(tmp_path / "chosen.db")
    settings = GenesisSettings(
        magic=40,
        danger=60,
        peoples=2,
        world_type=WorldType.ASTEROID_BELT,
        sea_pct=90,
        mountains_pct=5,
        moisture_pct=70,
        climate_era=ClimateEra.ICE_AGE,
        world_age=WorldAge.OLD,
    )
    model = scripted()
    outcome = await create(database, rules, model, settings)
    async with database.read() as session:
        world = await session.get(WorldRow, outcome.world_id)
    await database.dispose()
    assert world is not None
    assert (world.world_type, world.terrain_sea, world.terrain_mountains, world.terrain_humidity) == (WorldType.ASTEROID_BELT, 0.9, 0.05, 0.7)
    assert world.gravity is Gravity.LOW
    assert (world.climate_era, world.age_stage) == (ClimateEra.ICE_AGE, WorldAge.OLD)
    prompt = model.calls[0].prompt
    assert "Danger 60/100" in prompt and WORLD_TYPES[WorldType.ASTEROID_BELT].label in prompt and "Water covers 90%" in prompt
    assert "temperament" not in creation_text(rules, settings, for_genesis=True)


async def test_a_layered_cosmos_opens_its_second_layer_beside_the_home_galaxy(tmp_path: Path, rules: Rules, open_database: OpenDatabase) -> None:
    database = open_database(tmp_path / "layered.db")
    settings = GenesisSettings(magic=50, danger=50, peoples=2, cosmos_size=CosmosSize.SMALL, cosmos_shape=CosmosShape.LAYERED)
    model = scripted({"layer": LAYER})
    outcome = await create(database, rules, model, settings)
    async with database.read() as session:
        galaxies = list(await session.scalars(select(GalaxyRow).order_by(GalaxyRow.id)))
        layer = await session.scalar(select(DimensionRow).where(DimensionRow.dimension_kind == DimensionKind.ASTRAL))
        told = await session.scalar(select(ChronicleRow.text).where(ChronicleRow.text.contains("Velun")))
    await database.dispose()
    assert layer is not None and layer.name == "Velun"
    assert outcome.layer_galaxy_id == galaxies[-1].id and galaxies[-1].dimension_id == layer.id
    assert galaxies[0].id != outcome.layer_galaxy_id and galaxies[0].dimension_id != layer.id
    assert told is not None and "second layer" in told
    assert "second layer of the cosmos that lies beside the first world" in model.calls[0].prompt


async def test_a_chosen_layer_kind_wins_over_the_seed(tmp_path: Path, rules: Rules, open_database: OpenDatabase) -> None:
    database = open_database(tmp_path / "kind.db")
    settings = GenesisSettings(
        magic=50, danger=50, peoples=2, cosmos_size=CosmosSize.LARGE, cosmos_shape=CosmosShape.LAYERED, layer_kind=DimensionKind.UNDERWORLD
    )
    await create(database, rules, scripted({"layer": LAYER}), settings)
    async with database.read() as session:
        kinds = set(await session.scalars(select(DimensionRow.dimension_kind)))
    await database.dispose()
    assert DimensionKind.UNDERWORLD in kinds and DimensionKind.ASTRAL not in kinds


async def test_peoples_awakening_at_creation_read_the_creation_settings(tmp_path: Path, rules: Rules, open_database: OpenDatabase) -> None:
    database = open_database(tmp_path / "awaken.db")
    settings = GenesisSettings(magic=70, danger=20, peoples=2, world_type=WorldType.OCEAN)
    outcome = await create(database, rules, scripted(), settings)
    async with database.write() as session:
        scope = await load_scope(session, rules)
        scope.cosmos.genesis_settings = settings
        first = creation_settings_text(scope, outcome.world_id)
        other = creation_settings_text(scope, outcome.world_id + 1)
        scope.cosmos.epoch = 3
        later = creation_settings_text(scope, outcome.world_id)
    await database.dispose()
    assert first is not None and "Ocean world" in first and "Danger 20/100" in first
    assert "regions' danger values" not in first
    assert other is None and later is None
