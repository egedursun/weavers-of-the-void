from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.cosmos import CosmosDraft, CosmosRepository
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.world import LoreLanguage
from aerona.rules.registry import Rules
from aerona.services.narrative import backfill_endings
from tests.db.factories import make_entity, seed_world

BIO = "Dimem is a guard captain of Domar."
DEATH = "Died in epoch 9, at age 136."
FATE = "Epoch 9, world year 444: died at age 136."


async def dead_captain(session: AsyncSession, description: str) -> None:
    await CosmosRepository(session).create(
        CosmosDraft(name="Orvael", rng_seed=7, lore_language=LoreLanguage.ENGLISH, seed_idea="", cosmology="", tone="", rules=Rules())
    )
    world = await seed_world(session)
    entity = await make_entity(session, "Dimem", EntityType.MORTAL, world_id=world.id)
    entity.status, entity.end_epoch, entity.fate_note, entity.description = EntityStatus.DEAD, 9, FATE, description
    await session.flush()


async def test_a_death_the_description_already_tells_is_not_told_again(session: AsyncSession) -> None:
    await dead_captain(session, f"{BIO} {DEATH}")
    assert await backfill_endings(session) == 0


async def test_a_death_told_twice_keeps_one_telling(session: AsyncSession) -> None:
    await dead_captain(session, f"{BIO} {DEATH} {FATE}")
    assert await backfill_endings(session) == 1
    entity = await session.scalar(select(EntityRow).where(EntityRow.name == "Dimem"))
    assert entity is not None
    assert entity.description == f"{BIO} {DEATH}"
