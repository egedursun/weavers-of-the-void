from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from aerona.db.fixups import BORN_CURRENT, fixup_due, mark_born_current, marker, settle
from aerona.db.migrations import upgrade_to_head
from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.domain.enums.entity import EntityType
from aerona.engine.military.vessels import BACKFILL_FIXUP, backfill_vessels
from tests.engine.warfare.factories import make, make_ctx


async def test_a_universe_made_before_the_fixup_still_runs_it(session: AsyncSession, world_id: int) -> None:
    hull = await make(session, "Old Hull", EntityType.VESSEL, world_id)
    assert await fixup_due(session, BACKFILL_FIXUP)
    assert await backfill_vessels(make_ctx(session)) == 1
    assert await session.get(VesselProfileRow, hull.id) is not None
    assert not await fixup_due(session, BACKFILL_FIXUP)


async def test_a_universe_born_current_never_runs_a_legacy_fixup_over_what_was_made_in_it(session: AsyncSession, world_id: int) -> None:
    await settle(session, BORN_CURRENT, {})
    hull = await make(session, "New Hull", EntityType.VESSEL, world_id)
    assert not await fixup_due(session, BACKFILL_FIXUP)
    assert await backfill_vessels(make_ctx(session)) == 0
    assert await session.get(VesselProfileRow, hull.id) is None
    assert await session.get(AppliedFixupRow, BACKFILL_FIXUP) is None


async def test_a_state_marker_outside_the_listed_families_is_refused(session: AsyncSession) -> None:
    try:
        await marker(session, "military.vessel_profiles")
    except ValueError:
        return
    raise AssertionError("an unlisted key passed as a state marker")


async def test_a_created_universe_database_is_marked_born_current(tmp_path: Path) -> None:
    database = tmp_path / "born.db"
    url = f"sqlite+aiosqlite:///{database}"
    await upgrade_to_head(url)
    await mark_born_current(url)
    await mark_born_current(url)
    engine = create_async_engine(url)
    try:
        async with AsyncSession(engine) as session:
            assert not await fixup_due(session, BACKFILL_FIXUP)
    finally:
        await engine.dispose()
