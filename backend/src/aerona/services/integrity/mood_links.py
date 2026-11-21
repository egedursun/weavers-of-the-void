from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.feeling_spread import FeelingSpreadRow
from aerona.engine.feeling_spread.moods import emotion_of


def proper(feelings: dict[str, int]) -> dict[str, int]:
    return {key: max(0, min(PERCENT, int(value))) for key, value in feelings.items() if emotion_of(key) is not None}


async def odd_moods(session: AsyncSession) -> list[int]:
    rows = await session.scalars(select(FeelingSpreadRow).order_by(FeelingSpreadRow.id))
    return [
        row.id
        for row in rows
        if proper(dict(row.feelings or {})) != dict(row.feelings or {}) or (row.settlement_entity_id is None) == (row.household_id is None)
    ]


async def mend_mood(session: AsyncSession, key: int) -> None:
    row = await session.get(FeelingSpreadRow, key)
    if row is None:
        return
    if (row.settlement_entity_id is None) == (row.household_id is None):
        await session.delete(row)
        return
    row.feelings = proper(dict(row.feelings or {}))
    top = max(row.feelings.items(), key=lambda item: (item[1], item[0]), default=None)
    row.leading = emotion_of(top[0]) if top is not None else None
