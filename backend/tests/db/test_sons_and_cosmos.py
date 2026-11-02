import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ConflictError, ValidationFailedError
from aerona.db.repositories.cosmos import CosmosDraft, CosmosRepository, CreatorDraft, rules_from_snapshot, snapshot_differences, snapshot_rules
from aerona.db.repositories.foreign_gods import ForeignGodDraft, ForeignGodPowerDraft, ForeignGodRepository
from aerona.db.repositories.sons import PowerDraft, SonDraft, SonRepository
from aerona.db.repositories.worlds import WorldDraft, WorldRepository
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.routes import RouteRow
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.foreign_god import ForeignGodPowerEffect, ForeignGodStatus
from aerona.domain.enums.rarity import Rarity
from aerona.domain.enums.son import PowerEffect, Stat
from aerona.domain.enums.travel import RouteClosure, TravelMethod
from aerona.domain.enums.world import Discovery, LoreLanguage, WorldType
from aerona.domain.models.profiles import Personality
from aerona.domain.models.stats import PassionBlock, StatBlock
from aerona.rules.registry import Rules
from aerona.rules.snapshot import apply_overrides
from tests.db.factories import make_son, seed_world


async def test_cosmos_stores_an_immutable_rule_snapshot(session: AsyncSession) -> None:
    tuned = apply_overrides(Rules(), {("time", "years_per_epoch"): 80})
    repository = CosmosRepository(session)
    cosmos = await repository.create(
        CosmosDraft(
            name="Orvael",
            rng_seed=1234,
            lore_language=LoreLanguage.TURKISH,
            seed_idea="First create light",
            cosmology="A sea of light.",
            tone="solemn",
            rules=tuned,
        )
    )
    assert cosmos.lore_language is LoreLanguage.TURKISH
    restored = await repository.rules()
    assert restored.time.years_per_epoch == 80
    assert restored == tuned
    assert snapshot_differences(cosmos.rules_snapshot, Rules()) == {("time", "years_per_epoch"): (80.0, 50.0)}
    with pytest.raises(ConflictError):
        await repository.create(CosmosDraft(name="Again", rng_seed=1, lore_language=LoreLanguage.ENGLISH, seed_idea="", cosmology="", tone="", rules=Rules()))


def test_snapshot_round_trip_matches_defaults() -> None:
    assert rules_from_snapshot(snapshot_rules(Rules())) == Rules()


async def test_creator_is_a_named_node(session: AsyncSession, world_id: int) -> None:
    repository = CosmosRepository(session)
    creator = await repository.create_creator(CreatorDraft(name="Aeron", essence=150, mood_contentment=50, mood_anger=10, mood_interest=60, mood_loneliness=20))
    assert (await repository.require_creator()).id == creator.id
    with pytest.raises(ConflictError):
        await make_son(session, "Aeron", world_id)


async def test_son_powers_and_relations(session: AsyncSession, world_id: int) -> None:
    sons = SonRepository(session)
    first = await make_son(session, "Orrin", world_id)
    second = await make_son(session, "Pella", world_id)
    await sons.set_powers(
        first.id,
        [
            PowerDraft("Hand of Clay", "Shapes cheaply.", PowerEffect.CHEAP_CREATION, param_entity_type=EntityType.SETTLEMENT),
            PowerDraft("Iron Grip", "Wins duels.", PowerEffect.DUEL_MASTER, param_stat=Stat.STRENGTH),
        ],
    )
    assert [power.effect for power in await sons.powers(first.id)] == [PowerEffect.CHEAP_CREATION, PowerEffect.DUEL_MASTER]
    assert await sons.change_relation(second.id, first.id, 70, "shared a war") == 70
    assert await sons.change_relation(first.id, second.id, 70) == 100
    assert await sons.relation(second.id, first.id) == 100
    assert first.stat_block.get(Stat.WISDOM) == 50


async def test_sons_have_at_most_three_powers(session: AsyncSession, world_id: int) -> None:
    power = PowerDraft("Spring", "Essence.", PowerEffect.ESSENCE_SPRING)
    draft = SonDraft(
        name="Quill",
        title="the Overgifted",
        rarity=Rarity.EPIC,
        domains=(Domain.LIGHT, Domain.OATH),
        stats=StatBlock.uniform(60),
        passions=PassionBlock(loyalty=50, ambition=50, wrath=50, mercy=50),
        personality=Personality(),
        existence=60,
        hp=100,
        essence=40,
        birth_epoch=1,
        powers=(power,) * 4,
    )
    with pytest.raises(ValidationFailedError):
        await SonRepository(session).create(draft)


async def test_forgetting_a_world_closes_and_remembering_reopens_routes(session: AsyncSession, world_id: int) -> None:
    worlds = WorldRepository(session)
    other = await seed_world(session, name="Lumen", star_name="Lumen Star")
    route = RouteRow(world_a_id=world_id, world_b_id=other.id, method=TravelMethod.LIGHT_SAIL, duration_epochs=3, danger=20, created_epoch=1)
    session.add(route)
    await session.flush()
    assert await worlds.connected(world_id, other.id)
    await worlds.set_discovery(other, Discovery.FORGOTTEN)
    assert (route.active, route.closure, route.closed_by_forgetting_world_id) == (False, RouteClosure.FORGOTTEN, other.id)
    assert not await worlds.connected(world_id, other.id)
    await worlds.set_discovery(other, Discovery.KNOWN)
    assert route.active
    assert route.closed_by_forgetting_world_id is None


async def test_moons_inherit_the_root_star(session: AsyncSession, world_id: int) -> None:
    worlds = WorldRepository(session)
    planet = await worlds.require(WorldRow, world_id, "world")
    moon = await worlds.create_world(
        WorldDraft(
            name="Pale Moon",
            world_type=WorldType.ICE,
            orbit=0.15,
            terrain_seed="moon",
            terrain_sea=0.3,
            terrain_mountains=1.0,
            terrain_humidity=0.0,
            danger=10,
            created_epoch=1,
            parent_world_id=planet.id,
        )
    )
    assert moon.star_id == planet.star_id


async def test_genesis_choices_are_frozen(session: AsyncSession) -> None:
    cosmos = await CosmosRepository(session).create(
        CosmosDraft(name="Orvael", rng_seed=99, lore_language=LoreLanguage.ENGLISH, seed_idea="", cosmology="", tone="", rules=Rules())
    )
    with pytest.raises(ValidationFailedError):
        cosmos.lore_language = LoreLanguage.TURKISH
    with pytest.raises(ValidationFailedError):
        cosmos.rng_seed = 100
    cosmos.lore_language = LoreLanguage.ENGLISH


async def test_foreign_gods_join_the_name_registry(session: AsyncSession, world_id: int) -> None:
    repository = ForeignGodRepository(session)
    god = await repository.create(
        ForeignGodDraft(
            name="Ummar",
            world_id=world_id,
            domain_primary=Domain.EARTH,
            domain_secondary=Domain.MEMORY,
            power=40,
            stats=StatBlock.uniform(40),
            created_epoch=1,
            status=ForeignGodStatus.ASLEEP,
            powers=(ForeignGodPowerDraft("Stone Skin", ForeignGodPowerEffect.SHIELD, "Hard to wound."),),
        )
    )
    assert [row.id for row in await repository.in_world(world_id, (ForeignGodStatus.ASLEEP,))] == [god.id]
    with pytest.raises(ConflictError):
        await make_son(session, "ummar", world_id)
