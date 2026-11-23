from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import LanguageProfileRow
from aerona.db.tables.lore import LexemeRow
from aerona.db.tables.tongues import LanguageGrammarRow, LanguagePolicyRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityFlag
from aerona.domain.enums.tongues import LanguagePolicy, LanguageStage, MorphologyType
from aerona.engine.context import TickContext
from aerona.engine.primitives.queries import add_flag
from aerona.engine.tongues.policy import PolicyTally, revive, set_policy
from aerona.engine.tongues.stages import made_tongue
from tests.engine.core.factories import CoreWorld, bond, settlement
from tests.engine.tongues.helpers import tongue, tuned, words


async def test_a_made_tongue_has_a_regular_grammar_and_no_ancestor(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    language = await tongue(session, world, "Ordal", parent_id=world.language.id)
    profile = await made_tongue(ctx, language, None)
    grammar = await session.get(LanguageGrammarRow, language.id)
    assert profile.stage is LanguageStage.CONSTRUCTED and profile.parent_language_id is None
    assert grammar is not None and grammar.morphology is MorphologyType.AGGLUTINATIVE and grammar.cases == 0


async def test_a_revival_brings_a_dead_tongue_back_as_a_revived_daughter_with_its_old_words(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await tuned(session, language_policy={"revival_pct": 100})
    town = await settlement(session, "Harrowmere", world, world.regions[0])
    dead = await tongue(session, world, "Old Ostra")
    words(session, dead, ("keta", "stone"))
    await add_flag(session, dead.id, EntityFlag.DEAD_LANGUAGE, 1)
    await bond(session, town.id, dead.id, BondKind.SPEAKS)
    row = await set_policy(ctx, town.id, dead.id, LanguagePolicy.REVIVAL, 100)
    assert await revive(ctx, row, PolicyTally())
    restored = await session.scalar(select(LanguageProfileRow).where(LanguageProfileRow.parent_language_id == dead.id))
    assert restored is not None and restored.stage is LanguageStage.REVIVED
    kept = await session.scalar(select(LexemeRow.word).where(LexemeRow.language_entity_id == restored.entity_id))
    assert kept == "keta"
    speaking = await session.scalar(
        select(BondRow.id).where(BondRow.source_node_id == town.id, BondRow.target_node_id == restored.entity_id, BondRow.state == BondState.ACTIVE)
    )
    assert speaking is not None
    moved = await session.get(LanguagePolicyRow, (town.id, restored.entity_id, LanguagePolicy.REVIVAL))
    assert moved is not None
