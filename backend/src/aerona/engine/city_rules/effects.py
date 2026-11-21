from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.urban import HOUSING_ORDER
from aerona.constants.units import PERCENT
from aerona.db.read_memo import memoized
from aerona.db.tables.city_rules import LandUseRuleRow, MunicipalServiceRow
from aerona.db.tables.settlement import DistrictRow
from aerona.domain.enums.city_rules import LandUseRule, MunicipalService
from aerona.domain.enums.settlement import BuildMaterial, DistrictKind
from aerona.domain.enums.urban import HousingLevel, UrbanService
from aerona.rules.registry import Rules

SERVICE_COVERS = {
    MunicipalService.REFUSE: UrbanService.SANITATION,
    MunicipalService.STREET_CLEANING: UrbanService.SANITATION,
    MunicipalService.WATER_DISTRIBUTION: UrbanService.WATER,
    MunicipalService.NIGHT_WATCH: UrbanService.WATCH,
    MunicipalService.BURIAL_GROUND: UrbanService.BURIAL,
    MunicipalService.MARKET_INSPECTION: UrbanService.MARKET,
}
FIRE_RULES = frozenset({LandUseRule.FIRE_SPACING, LandUseRule.BUILD_MATERIAL})
ZONING = frozenset({LandUseRule.ALLOWED_USES, LandUseRule.BANNED_USES})
COST_CAP = 300


def effective(row: LandUseRuleRow) -> int:
    return row.strength * row.enforcement * (PERCENT - row.evasion) // (PERCENT * PERCENT)


async def rules_of(session: AsyncSession, settlement_id: int) -> list[LandUseRuleRow]:
    query = select(LandUseRuleRow).where(LandUseRuleRow.settlement_entity_id == settlement_id)
    return list(await session.scalars(query.order_by(LandUseRuleRow.id)))


def applies(row: LandUseRuleRow, district: DistrictRow | None) -> bool:
    return row.district_id is None or (district is not None and row.district_id == district.id)


def number_in(row: LandUseRuleRow, key: str, default: int) -> int:
    value = row.values.get(key, default)
    return value if isinstance(value, int) else default


def kinds_in(row: LandUseRuleRow) -> set[str]:
    listed = row.values.get("kinds", [])
    return {str(item) for item in listed} if isinstance(listed, list) else set()


async def use_barred(session: AsyncSession, settlement_id: int, kind: DistrictKind) -> bool:
    for row in await rules_of(session, settlement_id):
        if row.rule not in ZONING or row.district_id is not None or effective(row) < PERCENT // 4:
            continue
        listed = kinds_in(row)
        if (row.rule is LandUseRule.BANNED_USES and kind.value in listed) or (row.rule is LandUseRule.ALLOWED_USES and listed and kind.value not in listed):
            return True
    return False


async def housing_cap(session: AsyncSession, district: DistrictRow) -> int | None:
    caps = [
        number_in(row, "level", len(HOUSING_ORDER))
        for row in await rules_of(session, district.settlement_entity_id)
        if row.rule is LandUseRule.HEIGHT_LIMIT and applies(row, district) and effective(row) >= PERCENT // 4
    ]
    return min(caps) if caps else None


def above_cap(level: HousingLevel, cap: int | None) -> bool:
    return cap is not None and HOUSING_ORDER.index(level) >= cap


async def level_cap(session: AsyncSession, settlement_id: int) -> int | None:
    caps = [
        number_in(row, "level", PERCENT)
        for row in await rules_of(session, settlement_id)
        if row.rule is LandUseRule.DENSITY_LIMIT and row.district_id is None and effective(row) >= PERCENT // 4
    ]
    return min(caps) if caps else None


async def required_material(session: AsyncSession, settlement_id: int) -> BuildMaterial | None:
    known = {item.value: item for item in BuildMaterial}
    for row in await rules_of(session, settlement_id):
        material = row.values.get("material")
        if row.rule is LandUseRule.BUILD_MATERIAL and isinstance(material, str) and material in known and effective(row) >= PERCENT // 4:
            return known[material]
    return None


async def fire_cut(session: AsyncSession, rules: Rules, settlement_id: int) -> float:
    best = max([effective(row) for row in await rules_of(session, settlement_id) if row.rule in FIRE_RULES], default=0)
    return rules.city_rules.fire_spread_cut_pct * best / (PERCENT * PERCENT)


async def cost_factor(session: AsyncSession, rules: Rules, settlement_id: int) -> float:
    rise = sum(rules.city_rules.build_cost_rise_pct * effective(row) // PERCENT for row in await rules_of(session, settlement_id))
    return 1 + min(COST_CAP, rise) / PERCENT


async def zoning_relief(session: AsyncSession, settlement_id: int) -> float:
    best = max([effective(row) for row in await rules_of(session, settlement_id) if row.rule in ZONING], default=0)
    return best / PERCENT


async def amenity_of(session: AsyncSession, rules: Rules, district: DistrictRow) -> float:
    table = rules.city_rules
    found = 0.0
    for row in await rules_of(session, district.settlement_entity_id):
        if not applies(row, district):
            continue
        if row.rule is LandUseRule.GREEN_SHARE:
            found += table.green_desirability * effective(row) / PERCENT
        elif row.rule is LandUseRule.FRONTAGE_RULE:
            found += table.frontage_desirability * effective(row) / PERCENT
    return found


@memoized(MunicipalServiceRow)
async def running_services(session: AsyncSession) -> dict[int, list[MunicipalServiceRow]]:
    found: dict[int, list[MunicipalServiceRow]] = {}
    query = select(MunicipalServiceRow).where(MunicipalServiceRow.failed_epoch.is_(None))
    for row in await session.scalars(query.order_by(MunicipalServiceRow.settlement_entity_id, MunicipalServiceRow.id)):
        found.setdefault(row.settlement_entity_id, []).append(row)
    return found


async def municipal_cover(session: AsyncSession, district_ids: list[int], settlement_id: int) -> dict[tuple[int, UrbanService], int]:
    found: dict[tuple[int, UrbanService], int] = {}
    for row in (await running_services(session)).get(settlement_id, []):
        service = SERVICE_COVERS.get(row.service)
        if service is None:
            continue
        for district in district_ids:
            share = int((row.coverage or {}).get(str(district), 0)) * row.quality // PERCENT
            found[(district, service)] = max(found.get((district, service), 0), share)
    return found
