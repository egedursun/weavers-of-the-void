from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.read_memo import memo_of, table_names
from aerona.db.tables.dominion import DominionRow, GodDesignRow, GodScaleRow, RegionDominionRow
from aerona.domain.enums.dominion import DivineScale
from aerona.rules.registry import Rules

BOOK_TABLES = table_names((DominionRow, RegionDominionRow, GodScaleRow, GodDesignRow))
HALF = PERCENT // 2


@dataclass
class DominionBook:
    rulers: dict[int, RegionDominionRow] = field(default_factory=dict)
    strengths: dict[tuple[int, int], int] = field(default_factory=dict)
    scales: dict[tuple[int, DivineScale], int] = field(default_factory=dict)
    designs: dict[int, GodDesignRow] = field(default_factory=dict)

    @classmethod
    async def load(cls, session: AsyncSession) -> "DominionBook":
        memo = memo_of(session, "dominion", BOOK_TABLES)
        if memo is not None and "book" in memo:
            found: DominionBook = memo["book"]
            return found
        book = cls()
        for ruler in await session.scalars(select(RegionDominionRow)):
            book.rulers[ruler.region_entity_id] = ruler
        for row in await session.scalars(select(DominionRow)):
            book.strengths[(row.god_node_id, row.region_entity_id)] = row.strength
        for scale in await session.scalars(select(GodScaleRow)):
            book.scales[(scale.god_node_id, scale.scale)] = scale.value
        for design in await session.scalars(select(GodDesignRow)):
            book.designs[design.god_node_id] = design
        if memo is not None:
            memo["book"] = book
        return book

    def ruler(self, rules: Rules, region_id: int | None) -> int | None:
        found = self.rulers.get(region_id) if region_id is not None else None
        return found.god_node_id if found is not None and found.share >= rules.dominion.dominate_share else None

    def share(self, region_id: int | None, god_id: int) -> int:
        if region_id is None:
            return 0
        total = sum(value for (_, region), value in self.strengths.items() if region == region_id)
        return round(self.strengths.get((god_id, region_id), 0) * PERCENT / total) if total else 0

    def scale_at(self, rules: Rules, region_id: int | None, scale: DivineScale) -> int:
        ruler = self.ruler(rules, region_id)
        return self.scales.get((ruler, scale), 0) if ruler is not None else 0

    def cost_factor(self, rules: Rules, god_id: int, region_id: int | None) -> float:
        table = rules.dominion
        mine = self.share(region_id, god_id)
        ruler = self.ruler(rules, region_id)
        rival = self.rulers[region_id].share if ruler is not None and ruler != god_id and region_id is not None else 0
        return max(0.0, 1 - table.cheap_pct * mine / PERCENT / PERCENT + table.dear_pct * rival / PERCENT / PERCENT)

    def ruled_regions(self, rules: Rules, god_id: int) -> list[int]:
        return sorted(region for region in self.rulers if self.ruler(rules, region) == god_id)

    def power_factor(self, rules: Rules, god_id: int | None, region_id: int | None, pct: int) -> float:
        if god_id is None:
            return 1.0
        return 1 + pct * self.share(region_id, god_id) / PERCENT / PERCENT

    def aptitude_factor(self, rules: Rules, god_id: int | None) -> float:
        design = self.designs.get(god_id) if god_id is not None else None
        if design is None:
            return 1.0
        return max(0.0, 1 + (design.magic_aptitude - HALF) / HALF * rules.god_design.aptitude_rite_pct / PERCENT)

    def step_factor(self, rules: Rules, region_id: int | None, scale: DivineScale, pct: int) -> float:
        return max(0.0, 1 + self.scale_at(rules, region_id, scale) * pct / PERCENT)
