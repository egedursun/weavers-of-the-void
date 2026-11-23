from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.life_traits import TECHNIQUE_TRAITS, having
from aerona.catalog.rocks import ROCKS
from aerona.catalog.strata import STRATA
from aerona.constants.units import PERCENT
from aerona.db.tables.geology import RegionGeologyRow
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.geology import BuildingGrade, RockKind, UndergroundStratum
from aerona.domain.enums.life_traits import TechniqueTrait
from aerona.rules.registry import Rules

POROUS = 40
TOOL_TECHNIQUES = having(TECHNIQUE_TRAITS, TechniqueTrait.TOOL_METALS)
GRADE_ORDER = (BuildingGrade.PLAIN, BuildingGrade.FINE, BuildingGrade.SPLENDID)


def column_depth(rows: list[RegionGeologyRow]) -> int:
    return sum(row.thickness for row in rows)


def stratum_depth(rules: Rules, rows: list[RegionGeologyRow], stratum: UndergroundStratum) -> int:
    if STRATA[stratum].depth == 0:
        return next(
            (sum(row.thickness for row in rows[: i + 1]) for i, row in enumerate(rows) if ROCKS[row.rock].porosity(rules) >= POROUS), column_depth(rows)
        )
    return column_depth(rows) + STRATA[stratum].depth * rules.underground.cavern_depth_step


async def columns_by_region(session: AsyncSession, region_ids: list[int] | None = None) -> dict[int, list[RegionGeologyRow]]:
    statement = select(RegionGeologyRow).order_by(RegionGeologyRow.region_entity_id, RegionGeologyRow.depth_order)
    if region_ids is not None:
        statement = statement.where(RegionGeologyRow.region_entity_id.in_(region_ids))
    found: dict[int, list[RegionGeologyRow]] = defaultdict(list)
    for row in await session.scalars(statement):
        found[row.region_entity_id].append(row)
    return found


def deepest_reached(rows: list[RegionGeologyRow]) -> RegionGeologyRow | None:
    reached = [row for row in rows if row.reached_epoch is not None]
    return reached[-1] if reached else None


def rock_cut(rules: Rules, rows: list[RegionGeologyRow], techniques: set[Technique]) -> float:
    deepest = deepest_reached(rows)
    if deepest is None:
        return 0.0
    spec = ROCKS[deepest.rock]
    overcome = sum(1 for technique in TOOL_TECHNIQUES if technique in techniques) * rules.rocks.tool_tier_step
    hard = max(0, spec.hardness(rules) - overcome) / PERCENT * rules.rocks.hard_rock_cut_pct / PERCENT
    wet = spec.porosity(rules) / PERCENT * rules.rocks.porous_flood_pct / PERCENT
    return min(1.0, hard + wet)


def quarry_grade(rows: list[RegionGeologyRow]) -> BuildingGrade:
    near = [ROCKS[row.rock].grade for row in rows if row.reached_epoch is not None] or [ROCKS[row.rock].grade for row in rows[:3]]
    return max(near, key=GRADE_ORDER.index, default=BuildingGrade.PLAIN)


def carvable(rules: Rules, rows: list[RegionGeologyRow]) -> bool:
    bedrock = next((row for row in rows if row.rock is not RockKind.SOIL), None)
    return bedrock is not None and ROCKS[bedrock.rock].workability(rules) >= rules.rocks.carve_workability
