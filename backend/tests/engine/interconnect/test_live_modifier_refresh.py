from sqlalchemy.ext.asyncio import AsyncSession

from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.modifier import ModifierOp, ModifierSource
from aerona.engine.primitives.derivation import replace_derived
from aerona.engine.primitives.modifiers import ModifierDraft, ModifierIndex, add_modifier, forget_live, live_modifiers
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules
from tests.engine.warfare.factories import make

RULES = Rules()


def draft(target: int, source: ModifierSource, magnitude: float) -> ModifierDraft:
    return ModifierDraft(target, "prosperity", ModifierOp.ADD, magnitude, source, f"test.{source.value}", 1)


async def test_rederiving_a_target_drops_its_stale_live_modifiers_and_keeps_the_rest(session: AsyncSession, world_id: int) -> None:
    town = await make(session, "Varn", EntityType.SETTLEMENT, world_id, population=900, defense=30, prosperity=40, piety=20, wealth=30)
    other = await make(session, "Osk", EntityType.SETTLEMENT, world_id, population=500, defense=30, prosperity=40, piety=20, wealth=30)
    await add_modifier(session, draft(town.id, ModifierSource.LAW, 10))
    await add_modifier(session, draft(town.id, ModifierSource.BLESSING, 5))
    await add_modifier(session, draft(other.id, ModifierSource.LAW, 10))
    index = await ModifierIndex.load(session, 1)
    with live_modifiers(index, 1, RULES):
        assert stat(town, "prosperity") == 55 and stat(other, "prosperity") == 50
        await replace_derived(session, [ModifierSource.LAW], [draft(town.id, ModifierSource.LAW, 2)], targets=[town.id])
        assert stat(town, "prosperity") == 47
        assert stat(other, "prosperity") == 50


async def test_forgetting_a_target_with_no_live_index_is_harmless_and_empties_its_key(session: AsyncSession, world_id: int) -> None:
    town = await make(session, "Varn", EntityType.SETTLEMENT, world_id, population=900, defense=30, prosperity=40, piety=20, wealth=30)
    forget_live([town.id], [ModifierSource.LAW])
    await add_modifier(session, draft(town.id, ModifierSource.LAW, 10))
    index = await ModifierIndex.load(session, 1)
    with live_modifiers(index, 1, RULES):
        assert index.has(town.id, "prosperity")
        forget_live([town.id], [ModifierSource.LAW])
        assert not index.has(town.id, "prosperity") and index.keys_of(town.id) == []
        assert stat(town, "prosperity") == 40
