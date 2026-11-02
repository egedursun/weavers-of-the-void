from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityType
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.queries import canon
from aerona.engine.primitives.stats import set_stats, stat
from aerona.rules.registry import Rules


@dataclass(frozen=True)
class Overflow:
    budget: int
    given: int
    regions: tuple[int, ...]


async def overflow_to_land(session: AsyncSession, rules: Rules, overflow: int) -> Overflow:
    essence = rules.essence
    ceiling = essence.overflow_fertility_cap
    regions: list[EntityRow] = [
        region for region in await canon(session, [EntityType.REGION]) if (value := stat(region, "fertility")) is not None and value < ceiling
    ]
    budget = max(1, round_half_up(overflow / essence.overflow_per_fertility))
    given = 0
    touched: list[int] = []
    while given < budget and regions:
        barren = min(regions, key=lambda region: stat(region, "fertility") or 0)
        fertility = (stat(barren, "fertility") or 0) + 1
        set_stats(barren, fertility=fertility)
        if barren.id not in touched:
            touched.append(barren.id)
        if fertility >= ceiling:
            regions.remove(barren)
        given += 1
    await session.flush()
    return Overflow(budget=budget, given=given, regions=tuple(touched))
