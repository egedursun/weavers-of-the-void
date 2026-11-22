from collections.abc import Sequence

from aerona.catalog.life_traits import STANCE_TRAITS, having
from aerona.constants.units import PERCENT
from aerona.db.tables.environment import RegionEnvironmentRow, WorldSeasonRow
from aerona.db.tables.military import ArmyProfileRow, ArmyUnitRow
from aerona.domain.enums.environment import RiverClass, ScarKind
from aerona.domain.enums.life_traits import StanceTrait
from aerona.domain.enums.military import Stance, UnitKind
from aerona.engine.environment.book import add_scar
from aerona.engine.military.campaign import bridged, on_road, plundered_share
from aerona.engine.primitives.numbers import round_half_up
from aerona.rules.registry import Rules

LAYING = having(STANCE_TRAITS, StanceTrait.LAYING)
RIVERS = frozenset({RiverClass.RIVER, RiverClass.GREAT_RIVER})


def sappers(rows: Sequence[ArmyUnitRow]) -> int:
    return sum(row.count for row in rows if row.kind is UnitKind.SAPPERS)


def engineers(rules: Rules, rows: Sequence[ArmyUnitRow]) -> bool:
    return sappers(rows) >= max(1, rules.army_depth.sappers_needed)


def supply_limit(rules: Rules, region: RegionEnvironmentRow | None, season: WorldSeasonRow | None) -> int:
    floor = rules.army_depth.supply_floor
    if region is None:
        return floor
    growth = (season.growth if season is not None else PERCENT // 2) * rules.campaign_depth.forage_season_pct / PERCENT / (PERCENT // 2)
    harvest = region.harvest_pct / PERCENT
    roads = rules.army_depth.road_supply_pct / PERCENT if on_road(region, rules) else 1.0
    fed = region.farmed * rules.logistics.supply_per_farmed * harvest * (1 - plundered_share(region)) * min(2.0, growth) * roads
    return max(floor, round_half_up(fed))


def earthworks_of(region: RegionEnvironmentRow | None) -> int:
    return region.scars.get(ScarKind.EARTHWORKS.value, 0) if region is not None else 0


def leave_earthworks(rules: Rules, profile: ArmyProfileRow, region: RegionEnvironmentRow | None) -> int:
    if region is None or profile.entrenchment < rules.army_depth.earthworks_at:
        return 0
    gap = profile.entrenchment - earthworks_of(region)
    return add_scar(region, ScarKind.EARTHWORKS, gap) if gap > 0 else 0


def engineer(rules: Rules, profile: ArmyProfileRow, rows: Sequence[ArmyUnitRow], region: RegionEnvironmentRow | None) -> str | None:
    if region is None or not engineers(rules, rows):
        return None
    if profile.stance is Stance.RETREAT and region.river_class in RIVERS and bridged(rules, region):
        add_scar(region, ScarKind.BRIDGE_DOWN, PERCENT)
        return "bridge blown"
    if profile.stance in LAYING and region.scars.get(ScarKind.MILITARY_ROAD.value, 0) < PERCENT:
        add_scar(region, ScarKind.MILITARY_ROAD, rules.army_depth.sapper_road_gain)
        return "road laid"
    return None
