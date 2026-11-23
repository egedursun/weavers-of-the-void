import importlib

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.knowledge import DYING_KNOWLEDGE, KNOWLEDGE
from aerona.db.tables.couplings import TeachingRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.intrigue import HookRow, SecretRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.intrigue import HookSource, HookStrength, IntrigueSecret
from aerona.domain.enums.knowledge import KnowledgeKind
from aerona.domain.models.entity_stats import BeastStats, PlaceStats
from aerona.engine.context import TickContext
from aerona.engine.couplings.beast_memory import knowledge_dies
from aerona.engine.couplings.teachers import GIVERS, Lesson, give_secret, hand_over_hook
from aerona.engine.primitives.manual import manual_context
from tests.engine.core.factories import CoreWorld, bond, entity, mortal, tuned_rules


def test_the_old_lore_and_teaching_kinds_are_one_knowledge_kind_with_a_giver_for_each() -> None:
    assert not hasattr(importlib.import_module("aerona.domain.enums.couplings"), "TeachingKind")
    assert not hasattr(importlib.import_module("aerona.domain.enums.renown"), "LoreKind")
    assert set(GIVERS) == set(KnowledgeKind) == set(KNOWLEDGE)
    assert KnowledgeKind.SECRET in DYING_KNOWLEDGE and KnowledgeKind.SONG not in DYING_KNOWLEDGE


async def test_a_taught_secret_gives_a_hook_and_selling_it_hands_the_hook_over(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "test", tuned_rules(knowledge={"secret_hook_strength": 80}))
    keeper = await mortal(session, "Ysolde", world, world.regions[0].id)
    buyer = await mortal(session, "Ramon", world, world.regions[0].id)
    shamed = await mortal(session, "Lord Tavar", world, world.regions[0].id)
    secret = SecretRow(holder_node_id=keeper.id, kind=IntrigueSecret.AFFAIR, about_node_id=shamed.id, known_by=[], locked=[])
    session.add(secret)
    session.add(HookRow(holder_node_id=keeper.id, target_node_id=shamed.id, strength=HookStrength.WEAK, source=HookSource.SECRET, locked=False))
    await session.flush()
    target = await give_secret(ctx, Lesson(keeper, buyer, [], 80, KnowledgeKind.SECRET))
    assert target == shamed.id and buyer.id in secret.known_by
    hook = await session.scalar(select(HookRow).where(HookRow.holder_node_id == buyer.id))
    assert hook is not None and hook.target_node_id == shamed.id and hook.strength is HookStrength.STRONG and hook.secret_id == secret.id
    assert await give_secret(ctx, Lesson(keeper, buyer, [], 80, KnowledgeKind.SECRET)) is None
    await hand_over_hook(ctx, keeper.id, shamed.id)
    await session.flush()
    assert await session.scalar(select(HookRow).where(HookRow.holder_node_id == keeper.id)) is None


async def test_what_a_beast_never_taught_dies_with_it(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    region = world.regions[0]
    elder = await entity(session, "Deep Elder", EntityType.BEAST, BeastStats(hp=200), world_id=world.world.id, location_id=region.id)
    hidden = await entity(session, "The Drowned Hall", EntityType.PLACE, PlaceStats(), world_id=world.world.id, location_id=region.id)
    await bond(session, elder.id, hidden.id, BondKind.KNOWS)
    assert await knowledge_dies(ctx, elder) == 1
    await session.flush()
    assert "knowledge.lost_with_holder" in set(await session.scalars(select(IncidentRow.kind)))
    pupil = await mortal(session, "Tamsin", world, region.id)
    session.add(TeachingRow(teacher_node_id=elder.id, learner_entity_id=pupil.id, kind=KnowledgeKind.SITE, locked=[]))
    await session.flush()
    assert await knowledge_dies(ctx, elder) == 0
