from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.session import Database
from aerona.db.tables.couplings import CarrionPulseRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.engine.couplings import control
from aerona.engine.couplings.carrion import UNBURIED, carrion
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.stats import stat_or
from tests.engine.core.factories import tuned_rules
from tests.engine.integration.factories import seed_rich_cosmos


async def unburied(session: AsyncSession, region_id: int) -> list[EntityRow]:
    query = select(EntityRow).where(
        EntityRow.entity_type == EntityType.SPIRIT,
        EntityRow.status == EntityStatus.CANON,
        EntityRow.location_id == region_id,
        EntityRow.subtype == UNBURIED,
    )
    return list(await session.scalars(query))


async def test_the_unburied_dead_of_a_region_walk_as_one_spirit_and_calm_once_buried(database: Database) -> None:
    rules = tuned_rules(carrion={"restless_chance": 100, "burial": 0, "restless_dead": 100})
    async with database.write() as session:
        cosmos = await seed_rich_cosmos(session)
        region = cosmos.home.regions[0]
        for epoch in range(3):
            ctx = await manual_context(session, f"unburied_{epoch}", rules)
            row = await control.keep_dead(ctx, region.id, False)
            row.carrion = 1000
            await ctx.session.flush()
            await carrion(ctx)
        walking = await unburied(session, region.id)
        assert len(walking) == 1
        before = stat_or(walking[0], "unrest", 0)
        pulse = await session.get(CarrionPulseRow, region.id)
        assert pulse is not None
        pulse.carrion = 0
        await session.flush()
        ctx = await manual_context(session, "unburied_calm", rules)
        await carrion(ctx)
        assert stat_or(walking[0], "unrest", 0) < before
