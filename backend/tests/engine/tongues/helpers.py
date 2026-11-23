from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import LexemeRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.tongues import WordRegister
from aerona.domain.models.entity_stats import LanguageStats
from aerona.engine.context import TickContext
from aerona.engine.primitives.language_profile import language_profile
from aerona.engine.primitives.manual import manual_context
from tests.engine.core.factories import CoreWorld, entity, tuned_rules


async def tongue(session: AsyncSession, world: CoreWorld, name: str = "Ostra", *, parent_id: int | None = None) -> EntityRow:
    language = await entity(session, name, EntityType.LANGUAGE, LanguageStats(spread=20, complexity=40, sacredness=0), world_id=world.world.id)
    await language_profile(session, language, parent_id)
    return language


def words(session: AsyncSession, language: EntityRow, *pairs: tuple[str, str], register: WordRegister = WordRegister.COMMON) -> None:
    for word, meaning in pairs:
        session.add(LexemeRow(language_entity_id=language.id, word=word, meaning=meaning, added_by_kind=ActorKind.ENGINE, epoch=1, register=register))


async def tuned(session: AsyncSession, **namespaces: dict[str, int]) -> TickContext:
    return await manual_context(session, "tongues", rules=tuned_rules(**namespaces))
