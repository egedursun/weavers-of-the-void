from collections import Counter
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import LeyLineRow, RegionEnvironmentRow
from aerona.domain.enums.environment import ScarKind
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.stats import stat_or
from aerona.rules.registry import Rules

CUTTING_SCARS = (ScarKind.SALTED_EARTH, ScarKind.LEAK_WOUND)


@dataclass
class LeyWeb:
    lines: list[LeyLineRow]

    @classmethod
    async def load(cls, session: AsyncSession) -> "LeyWeb":
        return cls(list(await session.scalars(select(LeyLineRow).order_by(LeyLineRow.id))))

    def active(self) -> list[LeyLineRow]:
        return [line for line in self.lines if not line.severed]

    def degree(self) -> Counter[int]:
        counts: Counter[int] = Counter()
        for line in self.active():
            counts[line.region_a_id] += 1
            counts[line.region_b_id] += 1
        return counts

    def on_line(self, region_id: int | None) -> bool:
        return region_id is not None and self.degree()[region_id] > 0

    def partners(self, region_id: int) -> list[int]:
        return [
            line.region_b_id if line.region_a_id == region_id else line.region_a_id
            for line in self.active()
            if region_id in (line.region_a_id, line.region_b_id)
        ]


def pair(first: int, second: int) -> tuple[int, int]:
    return (first, second) if first < second else (second, first)


def cut_by_land(rules: Rules, grounds: dict[int, RegionEnvironmentRow], first: int, second: int) -> bool:
    depth = rules.environment.ley_cut_depth
    return any(grounds[region].scars.get(kind.value, 0) >= depth for region in (first, second) if region in grounds for kind in CUTTING_SCARS)


def candidate_lines(rules: Rules, atlas: RegionAtlas, regions: dict[int, EntityRow]) -> dict[tuple[int, int], int]:
    threshold = rules.environment.ley_threshold
    found: dict[tuple[int, int], int] = {}
    for region_id, region in regions.items():
        magic = stat_or(region, "magic", 0)
        if magic < threshold:
            continue
        for other_id in atlas.neighbour_regions(region_id):
            other = regions.get(other_id)
            if other is None or other.world_id != region.world_id:
                continue
            strength = min(magic, stat_or(other, "magic", 0))
            if strength >= threshold:
                found[pair(region_id, other_id)] = clamp_int(strength, 0, PERCENT)
    return found
