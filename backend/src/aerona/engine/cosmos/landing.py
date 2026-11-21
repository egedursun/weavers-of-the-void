from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityType
from aerona.engine.primitives.queries import canon
from aerona.engine.primitives.stats import stat_or
from aerona.rules.registry import Rules

FERTILITY = "fertility"


async def landing_region(session: AsyncSession, rules: Rules, world_id: int) -> EntityRow | None:
    regions = await canon(session, [EntityType.REGION], world_id)
    if not regions:
        return None
    return max(regions, key=lambda region: (stat_or(region, FERTILITY, rules.travel.default_fertility), -region.id))
