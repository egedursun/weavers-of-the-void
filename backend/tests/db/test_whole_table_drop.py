from sqlalchemy import delete, insert
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.fast_session import WHOLE_KEY
from aerona.db.read_memo import KEEP_KEY
from aerona.db.tables.agency import TurnCounterRow
from aerona.db.tables.cosmos import AppliedFixupRow


def whole(session: AsyncSession, table: str) -> bool | None:
    known: dict[str, bool] = session.sync_session.info.get(WHOLE_KEY, {})
    return known.get(table)


async def test_a_wholly_loaded_table_stays_known_across_writes_elsewhere_and_is_dropped_by_its_own(session: AsyncSession) -> None:
    session.sync_session.info[KEEP_KEY] = []
    session.add(AppliedFixupRow(key="first", result={}))
    await session.flush()
    assert await session.get(AppliedFixupRow, "missing") is None
    assert whole(session, "applied_fixups") is True
    await session.execute(delete(TurnCounterRow).where(TurnCounterRow.epoch < 0))
    assert whole(session, "applied_fixups") is True
    await session.execute(insert(AppliedFixupRow).values(key="second", result={}))
    assert whole(session, "applied_fixups") is None
    assert await session.get(AppliedFixupRow, "second") is not None
