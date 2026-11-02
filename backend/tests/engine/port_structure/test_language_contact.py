from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.lore import LexemeRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.models.entity_stats import LanguageStats
from aerona.engine.phases.language_contact import language_contact, order_creole, speaks
from aerona.engine.primitives.manual import manual_context
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, bond, entity, settlement, tuned_rules


async def test_ruled_communities_learn_their_rulers_tongue(session: AsyncSession, world: CoreWorld) -> None:
    rules = tuned_rules(language_contact={"conquest_bilingual_chance": 100})
    ruled = await settlement(session, "Hollowmere", world, world.regions[1])
    own = await entity(session, "Hollish", EntityType.LANGUAGE, LanguageStats(spread=10, complexity=20, sacredness=5), world_id=world.world.id)
    await bond(session, ruled.id, own.id, BondKind.SPEAKS)
    await bond(session, world.people.id, ruled.id, BondKind.RULES)
    await language_contact(await manual_context(session, "test", rules))
    assert await speaks(session, ruled.id, world.language.id)
    borrowed = await session.scalar(select(func.count()).select_from(LexemeRow).where(LexemeRow.language_entity_id == own.id))
    assert borrowed


async def test_creator_fuses_two_tongues_into_a_creole(session: AsyncSession, world: CoreWorld) -> None:
    second = await entity(session, "Marrow Speech", EntityType.LANGUAGE, LanguageStats(spread=20, complexity=30, sacredness=5), world_id=world.world.id)
    await bond(session, world.people.id, second.id, BondKind.SPEAKS)
    creole = await order_creole(session, Rules(), world.people.id)
    assert creole.subtype == "creole"
    assert await speaks(session, world.people.id, creole.id)
    assert not await speaks(session, world.people.id, second.id)
