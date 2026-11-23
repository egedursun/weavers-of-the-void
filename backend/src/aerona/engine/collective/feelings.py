from collections.abc import Mapping

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.collective import CROWD_FEELINGS
from aerona.constants.units import PERCENT
from aerona.db.tables.collective import CrowdFeelingRow
from aerona.domain.enums.collective import CrowdFeeling
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.recording.record import record


async def feeling_rows(session: AsyncSession, town_id: int) -> dict[CrowdFeeling, CrowdFeelingRow]:
    found = {row.feeling: row for row in await session.scalars(select(CrowdFeelingRow).where(CrowdFeelingRow.settlement_entity_id == town_id))}
    for feeling in CrowdFeeling:
        if feeling not in found:
            row = CrowdFeelingRow(settlement_entity_id=town_id, feeling=feeling, level=0, locked=False)
            session.add(row)
            found[feeling] = row
    return found


async def feelings_of(session: AsyncSession, town_id: int) -> dict[CrowdFeeling, int]:
    rows = await session.scalars(select(CrowdFeelingRow).where(CrowdFeelingRow.settlement_entity_id == town_id))
    known = {row.feeling: row.level for row in rows}
    return {feeling: known.get(feeling, 0) for feeling in CrowdFeeling}


def strongest(feelings: Mapping[CrowdFeeling, int]) -> int:
    return max(feelings.values(), default=0)


ROSE_AT = PERCENT // 2


async def stir_feelings(ctx: TickContext, town_id: int, amounts: Mapping[CrowdFeeling, float]) -> dict[CrowdFeeling, CrowdFeelingRow]:
    rows = await feeling_rows(ctx.session, town_id)
    for feeling, amount in sorted(amounts.items()):
        row = rows[feeling]
        if row.locked or not amount:
            continue
        before = row.level
        row.level = clamp_int(row.level + amount, 0, PERCENT)
        if before < ROSE_AT <= row.level:
            await record(ctx, "crowd.feeling_rose", roles={IncidentRole.PLACE: town_id}, facts={"feeling": feeling, "level": row.level}, place=town_id)
    return rows


async def fade_feelings(ctx: TickContext, town_id: int) -> None:
    rows = await feeling_rows(ctx.session, town_id)
    for feeling, row in sorted(rows.items()):
        if not row.locked:
            row.level = clamp_int(row.level - CROWD_FEELINGS[feeling].decay(ctx.rules), 0, PERCENT)


async def set_feeling(session: AsyncSession, town_id: int, feeling: CrowdFeeling, level: int, *, hold: bool | None) -> CrowdFeelingRow:
    row = (await feeling_rows(session, town_id))[feeling]
    row.level = clamp_int(level, 0, PERCENT)
    if hold is not None:
        row.locked = hold
    return row


def told_feelings(feelings: Mapping[CrowdFeeling, int]) -> str:
    return ", ".join(f"{CROWD_FEELINGS[feeling].label.lower()} {level}" for feeling, level in feelings.items())


async def feeling_view_rows(session: AsyncSession, town_id: int) -> dict[CrowdFeeling, CrowdFeelingRow]:
    rows = {row.feeling: row for row in await session.scalars(select(CrowdFeelingRow).where(CrowdFeelingRow.settlement_entity_id == town_id))}
    return {feeling: rows.get(feeling) or CrowdFeelingRow(settlement_entity_id=town_id, feeling=feeling, level=0, locked=False) for feeling in CrowdFeeling}
