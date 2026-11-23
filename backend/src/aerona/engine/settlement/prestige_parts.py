from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.gardens import GardenRow
from aerona.db.tables.settlement import DistrictRow
from aerona.domain.enums.garden import GardenKind
from aerona.domain.enums.settlement import DistrictKind
from aerona.rules.registry import Rules

KEPT = 50


async def drawn_prestige(session: AsyncSession, rules: Rules, town_id: int) -> int:
    menageries = await session.scalar(
        select(func.count(GardenRow.id)).where(GardenRow.settlement_entity_id == town_id, GardenRow.kind == GardenKind.MENAGERIE, GardenRow.condition >= KEPT)
    )
    lazarettos = await session.scalar(
        select(func.coalesce(func.sum(DistrictRow.level), 0)).where(DistrictRow.settlement_entity_id == town_id, DistrictRow.kind == DistrictKind.LAZARETTO)
    )
    gained = int(menageries or 0) * rules.gardens.menagerie_prestige
    lost = int(lazarettos or 0) * rules.districts.lazaretto_dread
    return max(-PERCENT, min(PERCENT, gained - lost))
