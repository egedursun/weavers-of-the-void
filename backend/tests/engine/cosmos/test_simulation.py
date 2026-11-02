from dataclasses import fields, replace

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import ChronicleRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import CivilizationTier, EngineKind, EntityFlag, EntityType
from aerona.domain.enums.rarity import Rarity
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.travel import TravelMethod
from aerona.domain.enums.world import WorldType
from aerona.domain.models.entity_stats import (
    CelestialStats,
    CultStats,
    MortalStats,
    PeopleStats,
    ResourceStats,
    SettlementStats,
    SpeciesStats,
    SpiritStats,
    StructureStats,
)
from aerona.engine.cosmos.foreign_gods import NewForeignGod, add_foreign_god
from aerona.engine.phase import Phase
from aerona.engine.phases import afterlife, civilization, creatures, exploration, horror, pantheon, sky, travel
from aerona.rules.registry import Rules
from tests.engine.cosmos.factories import Cosmos, make_entity, make_region, make_route, make_son, make_world, teach, tick

ORDER: tuple[tuple[Phase, ...], ...] = (
    travel.PHASES,
    exploration.PHASES,
    horror.PHASES,
    creatures.PHASES[:1],
    pantheon.PHASES,
    civilization.PHASES,
    sky.PHASES,
    afterlife.PHASES,
    creatures.PHASES[1:],
)
CERTAIN_NAMESPACES = ("travel", "exploration", "beyond", "creatures", "sky", "pantheon", "civilization", "cosmic_horror")
CHANCE_SUFFIXES = ("_chance", "_pct")
KEPT = frozenset({"colony_share_pct", "people_mutation_share_pct", "silence_word_loss_pct", "supernova_population_loss_pct", "madness_population_loss_pct"})


def certain(rules: Rules) -> Rules:
    updated = rules
    for namespace in CERTAIN_NAMESPACES:
        block = getattr(updated, namespace)
        changes = {item.name: 100 for item in fields(block) if item.name.endswith(CHANCE_SUFFIXES[0]) and item.name not in KEPT}
        updated = replace(updated, **{namespace: replace(block, **changes)})
    return updated


async def populate(session: AsyncSession, cosmos: Cosmos) -> None:
    dead = await make_world(session, "Nethis", WorldType.DEAD, created_epoch=1)
    living = await make_world(session, "Carnis", WorldType.LIVING, star_id=cosmos.star.id)
    mirror = await make_world(session, "Glassa", WorldType.MIRROR, star_id=cosmos.star.id)
    mirror.mirror_twin_id = cosmos.home.id
    for world in (cosmos.home, dead, living, mirror):
        region = await make_region(session, f"{world.name} Vale", world.id, fertility=60, danger=40, magic=50, breadth=50)
        people = await make_entity(
            session,
            f"{world.name} Folk",
            EntityType.PEOPLE,
            PeopleStats(population=25000, prosperity=60, wealth=70, craft=50, magic=40, piety=40),
            world_id=world.id,
            location_id=region.id,
        )
        await make_entity(
            session,
            f"{world.name} Hold",
            EntityType.SETTLEMENT,
            SettlementStats(population=4000, prosperity=20, defense=30, piety=30),
            world_id=world.id,
            location_id=region.id,
        )
        await make_entity(
            session,
            f"{world.name} Beast",
            EntityType.SPECIES,
            SpeciesStats(hp=200, strength=60, agility=40, intelligence=60, danger=70),
            world_id=world.id,
            location_id=region.id,
            power=9,
        )
        await make_entity(
            session,
            f"{world.name} Grazer",
            EntityType.SPECIES,
            SpeciesStats(hp=50, strength=10, agility=40, intelligence=10, danger=10),
            world_id=world.id,
            location_id=region.id,
            power=2,
        )
        await make_entity(session, f"{world.name} Moon", EntityType.CELESTIAL, CelestialStats(brightness=60, influence=40), world_id=world.id)
        await make_entity(
            session,
            f"{world.name} Seer",
            EntityType.MORTAL,
            MortalStats(intellect=95, charisma=60, agility=60, age=40, lifespan=90),
            world_id=world.id,
            location_id=region.id,
        )
        for branch in (KnowledgeBranch.GATE_LORE, KnowledgeBranch.WRITING, KnowledgeBranch.FORBIDDEN, KnowledgeBranch.BIOMANCY, KnowledgeBranch.IMMORTALITY):
            await teach(session, people, branch)
        people.civ_tier = CivilizationTier.KINGDOM
        await make_entity(
            session, f"{world.name} Shrine", EntityType.STRUCTURE, StructureStats(), world_id=world.id, location_id=region.id, engine_kind=EngineKind.TEMPLE
        )
        await make_entity(session, f"{world.name} Shade", EntityType.SPIRIT, SpiritStats(), world_id=world.id, location_id=region.id)
        await make_entity(
            session,
            f"{world.name} Cult",
            EntityType.CULT,
            CultStats(followers=300, zeal=90, influence=40),
            world_id=world.id,
            location_id=region.id,
            flags=[EntityFlag.OUTER_CULT],
        )
        await make_entity(
            session, f"{world.name} Ore", EntityType.RESOURCE, ResourceStats(abundance=60, value=50, might=40), world_id=world.id, location_id=region.id
        )
    await make_route(session, cosmos.home.id, living.id, TravelMethod.ANCIENT_GATE, duration=1, danger=40)
    await make_route(session, cosmos.home.id, mirror.id, TravelMethod.SLINGSHOT_ORBIT, duration=2, danger=30, known=False)
    son = await make_son(session, "Velan", cosmos.home.id, rarity=Rarity.MYTHIC, domains=(Domain.MADNESS, Domain.WAR))
    rival = await make_son(session, "Morak", living.id)
    await BondRepository(session).connect(BondDraft(son.id, rival.id, BondKind.RIVAL, 1))
    god = await add_foreign_god(session, Rules(), tick(session, Rules()).rng("seed"), 1, NewForeignGod("Vesmorn", living.id, (Domain.GLASS, None), stance=-80))
    god.contacted = True
    await session.flush()


@pytest.mark.parametrize("certainty", [False, True])
async def test_cosmos_runs_for_many_epochs(session: AsyncSession, cosmos: Cosmos, rules: Rules, certainty: bool) -> None:
    await populate(session, cosmos)
    active = certain(rules) if certainty else rules
    before = int(await session.scalar(select(func.count()).select_from(EntityRow)) or 0)
    for epoch in range(5, 11):
        (await CosmosRepository(session).require_cosmos()).epoch = epoch
        for group in ORDER:
            for phase in group:
                await phase.run(tick(session, active, epoch=epoch, phase=phase.name))
        await session.flush()
    after = int(await session.scalar(select(func.count()).select_from(EntityRow)) or 0)
    lines = int(await session.scalar(select(func.count()).select_from(ChronicleRow)) or 0)
    assert after > before and lines > 0
    if certainty:
        kinds = set(await session.scalars(select(EntityRow.entity_type)))
        assert {EntityType.OUTER_BEING, EntityType.PROPHECY} & kinds


async def test_manual_phase_runs(session: AsyncSession, cosmos: Cosmos, rules: Rules) -> None:
    await populate(session, cosmos)
    for runner in (
        travel.run_travel_phase,
        exploration.run_exploration_phase,
        horror.run_horror_phase,
        creatures.run_creature_phase,
        pantheon.run_pantheon_phase,
        civilization.run_civilization_phase,
        sky.run_sky_phase,
        afterlife.run_beyond_phase,
    ):
        await runner(session, rules)
    assert int(await session.scalar(select(func.count()).select_from(ChronicleRow)) or 0) > 0
