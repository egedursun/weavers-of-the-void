from sqlalchemy.ext.asyncio import AsyncSession

from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.models.entity_stats import KnowledgeStats
from aerona.engine.phases.knowledge_levels import DevelopmentKind, development_for, set_knowledge_level, shift_level
from aerona.engine.primitives.knowledge import KnowledgeMap, level_multiplier, ratio_of, times_of
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, bond, knowledge, tuned_rules


def test_level_scales_branch_effects_with_caps() -> None:
    table = Rules().knowledge
    assert level_multiplier(table, 0) == 0
    assert level_multiplier(table, 1) == 1
    assert level_multiplier(table, 3) == 1 + 2 * table.level_step_pct / 100
    assert level_multiplier(table, table.level_cap) == table.level_multiplier_cap_pct / 100
    assert ratio_of(table, 0, 50) == 1
    assert ratio_of(table, 1, 50) == 0.5
    assert ratio_of(table, table.level_cap, 10) == table.ratio_floor_pct / 100
    assert times_of(table, 1, 2) == 2
    assert times_of(table, 0, 2) == 1


async def test_same_branch_deepens_or_is_found_instead_of_duplicating(session: AsyncSession, world: CoreWorld) -> None:
    rules = tuned_rules(knowledge={"branch_record_cap": 1})
    farming = await knowledge(session, world, "Furrow Lore", KnowledgeBranch.AGRICULTURE)
    await bond(session, world.people.id, farming.id, BondKind.KNOWS)
    held = await development_for(session, rules, world.people, KnowledgeBranch.AGRICULTURE)
    assert held.kind is DevelopmentKind.DEEPEN and held.knowledge is not None and held.knowledge.id == farming.id
    stranger = world.species
    found = await development_for(session, rules, stranger, KnowledgeBranch.AGRICULTURE)
    assert found.kind is DevelopmentKind.LEARN
    fresh = await development_for(session, rules, world.people, KnowledgeBranch.WARFARE)
    assert fresh.kind is DevelopmentKind.NEW
    assert shift_level(rules, farming, 1) == 3
    assert isinstance(farming.stats, KnowledgeStats) and farming.stats.spread == 30 + rules.knowledge.level_up_spread
    session.add(farming)
    await session.flush()
    levels = await KnowledgeMap.load(session)
    assert levels.level(world.people.id, KnowledgeBranch.AGRICULTURE) == 3


async def test_creator_deepens_and_blunts_a_knowledge(session: AsyncSession, world: CoreWorld) -> None:
    rules = Rules()
    lore = await knowledge(session, world, "Star Charts", KnowledgeBranch.ASTRONOMY)
    deepened = await set_knowledge_level(session, rules, lore.id, 1)
    assert deepened.level == 3
    blunted = await set_knowledge_level(session, rules, lore.id, -1)
    assert blunted.level == 2
