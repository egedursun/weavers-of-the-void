from collections.abc import AsyncIterator
from dataclasses import replace
from pathlib import Path

import pytest
from sqlalchemy import select

from aerona.agents.context.creation import creation_text
from aerona.catalog.genesis import TEMPLATES
from aerona.core.errors import BusyError, ConflictError, ValidationFailedError
from aerona.db.repositories.cosmos import CosmosDraft, CosmosRepository, CreatorDraft
from aerona.db.session import Database
from aerona.db.tables.cosmos import CosmosRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.storyteller import StorytellerProfile
from aerona.domain.enums.world import CosmosShape, CosmosSize, GenesisTemplate, LanguageTexture, LoreLanguage, TechnologyEra
from aerona.domain.models.entity_stats import CelestialStats, RegionStats
from aerona.domain.models.genesis import GenesisOutcome
from aerona.domain.models.profiles import EntityDepth
from aerona.events.bus import EventBus
from aerona.rules.registry import Rules
from aerona.services.bulk_deepen import BulkDeepening, TargetKind
from aerona.services.genesis_wizard import GenesisCommand, GenesisWizard, WizardInput, extra_worlds, options, pulled, sanitize
from aerona.services.lore_ports import GenesisRequest, LorePorts
from aerona.services.player.ports import ContentJob, RevelationRequest, WorldCreationRequest
from aerona.services.startup_completion import StartupCompletion
from tests.conftest import OpenDatabase
from tests.services.app.factories import make_entity, make_world, seed_cosmos


@pytest.fixture
async def database(tmp_path: Path, open_database: OpenDatabase) -> AsyncIterator[Database]:
    database = open_database(tmp_path / "jobs.db")
    yield database
    await database.dispose()


async def no_sleep(seconds: float) -> None:
    del seconds


class FakeDeepener:
    def __init__(self, database: Database, busy_once: bool = False, fail: bool = False) -> None:
        self.database = database
        self.busy_once = busy_once
        self.fail = fail
        self.calls: list[int] = []

    async def deepen_entity(self, entity_id: int) -> None:
        self.calls.append(entity_id)
        if self.busy_once:
            self.busy_once = False
            raise BusyError("pool full")
        if self.fail:
            raise RuntimeError("model refused")
        async with self.database.write() as session:
            entity = await session.get(EntityRow, entity_id)
            assert entity is not None
            entity.depth = EntityDepth(history="Old.", epoch=1)

    async def deepen_foreign_god(self, god_id: int) -> None:
        self.calls.append(god_id)


async def test_bulk_deepening_runs_and_retries(database: Database) -> None:
    async with database.write() as session:
        await seed_cosmos(session)
    deepener = FakeDeepener(database, busy_once=True)
    bus = EventBus()
    bulk = BulkDeepening(database, Rules, deepener, bus=bus, sleep=no_sleep)
    state = await bulk.start()
    with pytest.raises(ConflictError):
        await bulk.start()
    await bulk.wait()
    assert state.done == 2
    assert state.failed == 0
    status = await bulk.status()
    assert status.waiting == 0
    assert any("Done: 2 deepened" in line.text for line in status.log)
    with pytest.raises(ConflictError):
        await bulk.start()
    with pytest.raises(ConflictError):
        bulk.stop()


async def test_bulk_deepening_failures(database: Database) -> None:
    async with database.write() as session:
        await seed_cosmos(session)
    deepener = FakeDeepener(database, fail=True)
    bulk = BulkDeepening(database, Rules, deepener, sleep=no_sleep)
    await bulk.start()
    await bulk.wait()
    assert bulk.state.failed == 2
    assert len(deepener.calls) == 2 * (Rules().batch.retries + 1)
    await bulk.deepen_one(TargetKind.FOREIGN_GOD, 5)
    assert deepener.calls[-1] == 5
    with pytest.raises(ConflictError):
        await BulkDeepening(database, Rules, None).start()


def test_wizard_sanitize_and_text() -> None:
    rules = Rules()
    settings = sanitize(rules, WizardInput(template="cosmic_horror", magic="200", peoples=99, technology="laser"))
    assert settings.template is GenesisTemplate.COSMIC_HORROR
    assert settings.magic == 100
    assert settings.danger == 90
    assert settings.peoples == rules.setup_wizard.peoples_max
    assert settings.technology is TechnologyEra.IRON
    assert settings.cosmos_size is CosmosSize.SMALL
    defaults = sanitize(rules, WizardInput(template="__class__"))
    assert defaults.template is None
    assert defaults.language_texture is LanguageTexture.FREE
    assert defaults.magic == rules.setup_wizard.magic
    assert defaults.storyteller is StorytellerProfile.CYCLIC
    assert sanitize(rules, WizardInput(storyteller="chaotic")).storyteller is StorytellerProfile.CHAOTIC
    assert sanitize(rules, WizardInput(storyteller="loud")).storyteller is StorytellerProfile.CYCLIC
    assert set(options(rules).storyteller) == set(StorytellerProfile)
    assert extra_worlds(rules, CosmosSize.LARGE) == rules.setup_wizard.large_cosmos_worlds
    assert [option.worlds for option in options(rules).cosmos] == [1, 2, 3]
    assert "Cosmic horror" in creation_text(rules, settings, for_genesis=True)
    assert pulled(None, 100, 50) == 75
    assert pulled(20, 80, 50) == 50


def test_every_template_survives_sanitizing_and_every_era_has_one() -> None:
    rules = Rules()
    assert set(TEMPLATES) == set(GenesisTemplate)
    for template in TEMPLATES.values():
        settings = sanitize(rules, WizardInput(template=template.key.value))
        assert (settings.magic, settings.danger, settings.peoples) == (template.magic, template.danger, template.peoples)
        assert (settings.tone, settings.seed_idea) == (template.tone, template.seed)
        assert (settings.storyteller, settings.world_type, settings.climate_era, settings.world_age) == (
            template.storyteller,
            template.world_type,
            template.climate_era,
            template.world_age,
        )
        assert settings.cosmos_shape is (template.shape if template.cosmos is not CosmosSize.SINGLE else CosmosShape.ONE_SUN)
        assert template.name in creation_text(rules, settings, for_genesis=True)
    assert {template.technology for template in TEMPLATES.values()} == set(TechnologyEra)


class FakeGenesis:
    def __init__(self, database: Database) -> None:
        self.database = database
        self.request: GenesisRequest | None = None

    async def create(self, request: GenesisRequest) -> GenesisOutcome:
        self.request = request
        async with self.database.write() as session:
            await CosmosRepository(session).create(
                CosmosDraft(
                    name="Genesis", rng_seed=request.rng_seed, lore_language=request.lore_language, seed_idea=request.seed, cosmology="", tone="", rules=Rules()
                )
            )
            await CosmosRepository(session).create_creator(CreatorDraft(request.creator_name, 150, 50, 10, 50, 20))
            world = await make_world(session, "First")
            cosmos = await session.get(CosmosRow, 1)
            assert cosmos is not None
            cosmos.primary_world_id = world.id
            await make_entity(session, "Vale", EntityType.REGION, world_id=world.id, stats=RegionStats(magic=0, danger=100))
        return GenesisOutcome(world_id=world.id)


class FakeAwakener:
    def __init__(self) -> None:
        self.calls: list[tuple[int, int | None]] = []

    async def awaken(self, count: int, world_id: int | None) -> list[int]:
        self.calls.append((count, world_id))
        return [101]


class FakeWorlds:
    def __init__(self) -> None:
        self.requests: list[WorldCreationRequest] = []

    async def create(self, request: WorldCreationRequest) -> int:
        self.requests.append(request)
        return 200 + len(self.requests)


async def test_genesis_pipeline(database: Database) -> None:
    genesis = FakeGenesis(database)
    awakener = FakeAwakener()
    worlds = FakeWorlds()
    wizard = GenesisWizard(database, Rules(), LorePorts(genesis=genesis, awakener=awakener, worlds=worlds))
    with pytest.raises(ValidationFailedError):
        await wizard.run(GenesisCommand(creator_name="", seed=""))
    result = await wizard.run(
        GenesisCommand(creator_name="Aeron", seed="salt", lore_language=LoreLanguage.TURKISH, wizard=WizardInput(template="star_myth", magic=100, danger=0))
    )
    assert genesis.request is not None
    assert genesis.request.lore_language is LoreLanguage.TURKISH
    assert genesis.request.settings is not None
    assert awakener.calls == [(3, awakener.calls[0][1])]
    assert result["worlds"] == [201, 202]
    assert "second world" in worlds.requests[0].inspiration
    assert genesis.request.seed in worlds.requests[0].inspiration
    assert "different" not in worlds.requests[0].inspiration
    async with database.read() as session:
        cosmos = await session.get(CosmosRow, 1)
        assert cosmos is not None
        assert cosmos.genesis_settings is not None
        assert cosmos.rules_snapshot
        region = await session.scalar(select(EntityRow).where(EntityRow.name == "Vale"))
        assert region is not None
        assert region.stats.model_dump()["magic"] == 50
        assert region.stats.model_dump()["danger"] == 50
    with pytest.raises(ConflictError):
        await wizard.run(GenesisCommand(creator_name="Aeron", seed="again"))


class FakeWriter:
    def __init__(self) -> None:
        self.jobs: list[ContentJob] = []

    async def write(self, job: ContentJob) -> str:
        self.jobs.append(job)
        return "ok"


class FakeRevelations:
    def __init__(self, database: Database) -> None:
        self.database = database

    async def reveal(self, request: RevelationRequest) -> int:
        async with self.database.write() as session:
            cosmos = await session.get(CosmosRow, 1)
            assert cosmos is not None and cosmos.primary_world_id is not None
            star = await make_entity(session, "First Light", EntityType.CELESTIAL, world_id=cosmos.primary_world_id, stats=CelestialStats())
            return star.id


async def test_startup_awakens_the_first_peoples_on_a_world_without_peoples(database: Database) -> None:
    async with database.write() as session:
        world = await seed_cosmos(session)
        world.people.status = EntityStatus.REJECTED
    rules = replace(Rules(), awakening=replace(Rules().awakening, first_peoples=4))
    awakener = FakeAwakener()
    completion = StartupCompletion(database, lambda: rules, LorePorts(awakener=awakener))
    assert (await completion.needed()).first_people
    result = await completion.run()
    assert "peoples" in result["completed"]
    assert [count for count, _ in awakener.calls] == [rules.awakening.first_peoples]


async def test_startup_completion(database: Database) -> None:
    async with database.write() as session:
        await seed_cosmos(session)
    writer = FakeWriter()
    completion = StartupCompletion(database, Rules, LorePorts(writer=writer, revelations=FakeRevelations(database)))
    work = await completion.needed()
    assert work.portrait
    assert work.sky_body
    assert not work.first_people
    assert completion.enabled()
    result = await completion.run()
    assert "portrait" in result["completed"]
    assert "first star" in result["completed"]
    after = await completion.needed()
    assert not after.sky_body
    disabled = StartupCompletion(database, Rules, LorePorts(), read_only=lambda: True)
    assert not disabled.enabled()
