from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.belonging import SatireRow
from aerona.engine.primitives.numbers import round_half_up
from aerona.rules.registry import Rules

RECENT = 1


async def bite_since(session: AsyncSession, epoch: int, *conditions: ColumnElement[bool]) -> int:
    found = await session.scalar(select(func.coalesce(func.sum(SatireRow.bite), 0)).where(SatireRow.epoch >= epoch - RECENT, *conditions))
    return int(found or 0)


async def sting(session: AsyncSession, rules: Rules, ruler_id: int, epoch: int) -> int:
    bite = await bite_since(session, epoch, SatireRow.target_entity_id == ruler_id, SatireRow.tolerated.is_(True))
    return round_half_up(bite * rules.satire.opinion_pct / PERCENT)


async def vent(session: AsyncSession, rules: Rules, polity_id: int | None, epoch: int) -> float:
    if polity_id is None:
        return 0.0
    bite = await bite_since(session, epoch, SatireRow.polity_entity_id == polity_id, SatireRow.tolerated.is_(True))
    return min(PERCENT, bite) * rules.satire.vent / PERCENT


async def suppressed(session: AsyncSession, rules: Rules, polity_id: int, epoch: int) -> int:
    count = await session.scalar(
        select(func.count(SatireRow.id)).where(SatireRow.polity_entity_id == polity_id, SatireRow.punished.is_(True), SatireRow.epoch >= epoch - RECENT)
    )
    return int(count or 0) * rules.satire.suppression
