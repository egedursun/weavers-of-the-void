import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.cosmos import CosmosDraft, CosmosRepository
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.world import LoreLanguage
from aerona.rules.registry import Rules
from aerona.services.narrative import backfill_endings, sweep_narratives
from tests.db.factories import make_entity, seed_world

ORIGINAL = "Original lore text."


async def seed_dead_mortal(session: AsyncSession, language: LoreLanguage) -> None:
    await CosmosRepository(session).create(CosmosDraft(name="Orvael", rng_seed=7, lore_language=language, seed_idea="", cosmology="", tone="", rules=Rules()))
    world = await seed_world(session)
    entity = await make_entity(session, "Varr", EntityType.MORTAL, world_id=world.id)
    entity.status = EntityStatus.DEAD
    entity.end_epoch = 3
    entity.description = ORIGINAL
    await session.flush()


@pytest.mark.parametrize("language", [LoreLanguage.TURKISH])
async def test_english_only_repairs_leave_non_english_lore_untouched(session: AsyncSession, language: LoreLanguage) -> None:
    await seed_dead_mortal(session, language)
    assert await backfill_endings(session) == 0
    assert await sweep_narratives(session) == 0


async def test_english_lore_still_receives_an_ending(session: AsyncSession) -> None:
    await seed_dead_mortal(session, LoreLanguage.ENGLISH)
    assert await backfill_endings(session) == 1
