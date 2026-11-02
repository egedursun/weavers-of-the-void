from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.cosmos import CosmosDraft, CosmosRepository
from aerona.domain.enums.world import LoreLanguage
from aerona.engine.snapshot import world_snapshot
from aerona.rules.registry import Rules


async def test_live_snapshot_carries_the_doom_clock(session: AsyncSession) -> None:
    cosmos = await CosmosRepository(session).create(
        CosmosDraft(name="Orvael", rng_seed=1, lore_language=LoreLanguage.ENGLISH, seed_idea="", cosmology="", tone="", rules=Rules())
    )
    cosmos.doom_clock = 31
    await session.flush()
    assert (await world_snapshot(session)).doom == 31
