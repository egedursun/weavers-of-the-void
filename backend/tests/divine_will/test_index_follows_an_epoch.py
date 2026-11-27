import asyncio
from pathlib import Path

from aerona.engine.pipeline import simulate
from aerona.rules.registry import Rules
from aerona.services.divine_will.index import LoreIndex
from tests.conftest import OpenDatabase
from tests.divine_will.embedder_fixtures import CountingEmbedder
from tests.divine_will.index_documents import documents, texts
from tests.engine.core.stirring import eager, stir
from tests.engine.integration.factories import seed_rich_cosmos

FOLLOW_PAUSE = 0.05


async def test_an_index_that_follows_an_epoch_matches_one_built_after_it(tmp_path: Path, open_database: OpenDatabase) -> None:
    database = open_database(tmp_path / "world.db")
    async with database.write() as session:
        await stir(session, await seed_rich_cosmos(session))
    followed = LoreIndex(database, Rules, embedder=CountingEmbedder(), folder=tmp_path / "followed")
    await followed.refresh()
    before = documents(followed)
    living = asyncio.create_task(simulate(database, 1, rules=eager(Rules())))
    passes = 0
    while not living.done():
        await followed.follow()
        passes += 1
        await asyncio.sleep(FOLLOW_PAUSE)
    await living
    await followed.refresh()
    after = documents(followed)
    fresh = LoreIndex(database, Rules, embedder=CountingEmbedder(), folder=tmp_path / "fresh")
    await fresh.refresh()
    built = documents(fresh)
    missing = sorted(key for key in built if key not in after)
    extra = sorted(key for key in after if key not in built)
    different = sorted(key for key in built if key in after and built[key] != after[key])
    shown = (different + extra + missing)[:2]
    assert (missing[:10], extra[:10], different[:10]) == ([], [], []), (texts(followed, shown), texts(fresh, shown))
    assert passes > 1 and after != before
    await followed.stop()
    await fresh.stop()
    await database.dispose()
