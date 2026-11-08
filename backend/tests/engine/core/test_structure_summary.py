from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.structures import StructureProfileRow
from aerona.domain.enums.structure import ConstructionState, StructureKind
from aerona.engine.primitives.manual import manual_context
from aerona.engine.structures.construction import Commission, begin, finish
from aerona.engine.structures.describe import summary
from tests.engine.core.factories import CoreWorld, settlement


async def test_a_work_is_summed_up_by_its_state(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "summary")
    town = await settlement(session, "Brookhold", world, world.regions[0], population=6000)
    work, row = await begin(ctx, Commission(site=town, kind=StructureKind.SHRINE))
    profile = await session.get(StructureProfileRow, work.id)
    assert profile is not None
    assert "being raised" in await summary(session, work, profile) and f"{profile.progress}% done" in await summary(session, work, profile)
    await finish(ctx, row)
    working = await summary(session, work, profile)
    assert working.startswith(f"{work.name} (") and "working at" in working and "damaged" not in working
    profile.construction_state = ConstructionState.DAMAGED
    assert "damaged, working at" in await summary(session, work, profile)
    profile.construction_state = ConstructionState.RUINED
    assert (await summary(session, work, profile)).endswith(", a ruin)")
