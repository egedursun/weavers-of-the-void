from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.thoughts import FEARFUL_KEYS, WRATHFUL_KEYS
from aerona.constants.units import PERCENT
from aerona.db.tables.feeling_spread import FeelingSpreadRow
from aerona.domain.enums.folkways import BiasedDecision

BD = BiasedDecision
CAUTION = frozenset({BD.PEACE, BD.RETREAT, BD.SURRENDER, BD.MIGRATION})
DARING = frozenset({BD.WAR, BD.RAID, BD.SCHEME})
SWAY = 2


async def mood_lean(session: AsyncSession, community_id: int, decision: BiasedDecision) -> float:
    row = await session.scalar(select(FeelingSpreadRow).where(FeelingSpreadRow.settlement_entity_id == community_id).limit(1))
    if row is None or not row.feelings:
        return 1.0
    fear = sum(value for key, value in row.feelings.items() if key in FEARFUL_KEYS) / (PERCENT * SWAY)
    wrath = sum(value for key, value in row.feelings.items() if key in WRATHFUL_KEYS) / (PERCENT * SWAY)
    if decision in CAUTION:
        return 1 + fear - wrath / SWAY
    if decision in DARING:
        return 1 + wrath - fear / SWAY
    return 1.0
