from collections.abc import Mapping

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.peoples import (
    DIETS,
    FINE_JOBS,
    FOOD_SOURCES,
    HEAVY_JOBS,
    KIN,
    SIZES,
    STAPLE_BY_SOURCE,
    SUN_BY_BAND,
    FoodSource,
    MountFit,
)
from aerona.constants.units import PERCENT
from aerona.db.tables.demography import PeopleBiologyRow, PeopleCultureRow
from aerona.db.tables.disease import DiseaseProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.domain.enums.demography import Job, NaturalTrait
from aerona.domain.enums.ecology import Diet
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.environment import CoastKind, TemperatureBand, TerrainKind, WeatherKind
from aerona.domain.enums.military import UnitKind
from aerona.engine.body.customs import people_of
from aerona.engine.demography.rites import contagion, raises_dead
from aerona.engine.nature.seasons import chilled
from aerona.rules.registry import Rules

FED = 100
BANDS = tuple(TemperatureBand)
WINTER = frozenset({WeatherKind.SNOW, WeatherKind.BLIZZARD})
HOT_WEATHER = frozenset({WeatherKind.HEAT_WAVE, WeatherKind.DROUGHT_WIND, WeatherKind.SANDSTORM})
WARM = frozenset({TemperatureBand.WARM, TemperatureBand.HOT, TemperatureBand.SEARING})
HEIGHTS = frozenset({TerrainKind.HILLS, TerrainKind.MOUNTAINS, TerrainKind.HIGH_PASS, TerrainKind.CANYON})
WATERS = frozenset({TerrainKind.MARSH, TerrainKind.COAST, TerrainKind.ISLAND, TerrainKind.RIVER_VALLEY, TerrainKind.SEA})
NAVAL_UNITS = frozenset({UnitKind.NAVAL_CREW, UnitKind.MARINES})
RIDDEN = frozenset({UnitKind.LIGHT_CAVALRY, UnitKind.HEAVY_CAVALRY, UnitKind.MOUNTED_ARCHERS, UnitKind.CHARIOTS, UnitKind.BEAST_RIDERS})


def scaled(factor: float, pct: int) -> float:
    return max(0.0, 1 + (factor - 1) * pct / PERCENT)


def natures(biology: PeopleBiologyRow | None) -> set[NaturalTrait]:
    if biology is None:
        return set()
    return {NaturalTrait(item) for item in biology.traits if item in NaturalTrait._value2member_map_}


def edible(diet: Diet) -> frozenset[CommodityKind]:
    return DIETS[diet].edible


def food_need(rules: Rules, biology: PeopleBiologyRow | None, band: TemperatureBand | None = None) -> float:
    if biology is None:
        return 1.0
    table = rules.biology
    traits = natures(biology)
    factor = KIN[biology.body_plan].food_pct / PERCENT * SIZES[biology.size_class].food_pct / PERCENT
    if chilled(biology.thermoregulation, band):
        factor *= rules.thermoregulation.endotherm_cold_food_pct / PERCENT
    if NaturalTrait.COLD_BLOODED in traits:
        factor *= table.cold_blooded_food_pct / PERCENT
    if NaturalTrait.REGENERATING in traits:
        factor *= table.regenerating_food_pct / PERCENT
    return max(0.05, scaled(factor, table.food_need_pct))


def footprint(rules: Rules, biology: PeopleBiologyRow | None) -> float:
    if biology is None:
        return 1.0
    table = rules.biology
    traits = natures(biology)
    factor = KIN[biology.body_plan].space_pct / PERCENT * SIZES[biology.size_class].space_pct / PERCENT
    if NaturalTrait.BURROWING in traits:
        factor *= table.burrowing_space_pct / PERCENT
    if NaturalTrait.HIVE_MINDED in traits:
        factor *= table.hive_space_pct / PERCENT
    return max(0.05, scaled(factor, table.footprint_pct))


def source_weights(rules: Rules, region: RegionEnvironmentRow | None) -> dict[FoodSource, float]:
    if region is None:
        return {FoodSource.FIELDS: 1.0}
    sea = rules.biology.sea_food_pct / PERCENT if region.coast_kind is not CoastKind.NONE else 0.0
    farmed, grazed = max(0, region.farmed), max(0, region.grazed)
    land = farmed + grazed
    if land <= 0:
        return {FoodSource.SEA: 1.0} if sea else {FoodSource.FIELDS: 1.0}
    return {FoodSource.FIELDS: (1 - sea) * farmed / land, FoodSource.PASTURE: (1 - sea) * grazed / land, FoodSource.SEA: sea}


def special_food(rules: Rules, diet: Diet, region: RegionEnvironmentRow | None, magic_level: int) -> float:
    table = rules.biology
    sources = DIETS[diet].sources
    total = 0.0
    if FoodSource.STONE in sources:
        total += sources[FoodSource.STONE] / PERCENT * table.stone_food_pct / PERCENT
    if FoodSource.ESSENCE in sources:
        density = (region.magic_density if region is not None else 0) / PERCENT
        total += (
            sources[FoodSource.ESSENCE] / PERCENT * (table.essence_food_pct / PERCENT * (1 + density) + magic_level * table.essence_per_magic_pct / PERCENT)
        )
    if FoodSource.SUN in sources:
        band = region.temperature_band if region is not None else TemperatureBand.TEMPERATE
        total += sources[FoodSource.SUN] / PERCENT * table.sun_food_pct / PERCENT * SUN_BY_BAND[band] / PERCENT
    return total


def diet_share(rules: Rules, diet: Diet, region: RegionEnvironmentRow | None) -> float:
    sources = DIETS[diet].sources
    weights = source_weights(rules, region)
    return sum(weights.get(source, 0.0) * sources.get(source, 0) / PERCENT for source in FOOD_SOURCES)


def nourishment(rules: Rules, diet: Diet, region: RegionEnvironmentRow | None, index: int | None, magic_level: int = 0) -> float:
    fed = (index if index is not None else FED) / FED
    from_food = fed * diet_share(rules, diet, region) if set(DIETS[diet].sources) & FOOD_SOURCES else 0.0
    return from_food + special_food(rules, diet, region, magic_level)


def hunger_level(
    rules: Rules,
    biology: PeopleBiologyRow | None,
    region: RegionEnvironmentRow | None,
    index: int | None,
    magic_level: int = 0,
    *,
    band: TemperatureBand | None = None,
) -> float:
    if biology is None:
        return 0.0 if index is None else max(0.0, min(1.0, 1 - index / FED))
    fed = nourishment(rules, biology.diet, region, index, magic_level)
    return max(0.0, min(1.0, 1 - fed / food_need(rules, biology, band)))


def staple_for(rules: Rules, diet: Diet, region: RegionEnvironmentRow | None) -> CommodityKind:
    sources = DIETS[diet].sources
    weights = source_weights(rules, region)
    food = [(weights.get(source, 0.0) * sources[source], source.value, source) for source in sources if source in FOOD_SOURCES]
    if food and max(food)[0] > 0:
        return STAPLE_BY_SOURCE[max(food)[2]]
    special = [source for source in sources if source not in FOOD_SOURCES]
    if special:
        return STAPLE_BY_SOURCE[special[0]]
    return STAPLE_BY_SOURCE[max(food)[2]] if food else CommodityKind.GRAIN


def job_factors(rules: Rules, biology: PeopleBiologyRow | None) -> dict[Job, float]:
    if biology is None:
        return {}
    table = rules.biology
    traits = natures(biology)
    kin = KIN[biology.body_plan]
    size = SIZES[biology.size_class]
    found: dict[Job, float] = {}
    for job in Job:
        factor = kin.labour.get(job, PERCENT) / PERCENT
        if job in HEAVY_JOBS:
            factor *= size.heavy_labour_pct / PERCENT
        elif job in FINE_JOBS:
            factor *= size.fine_labour_pct / PERCENT
        if job is Job.MINING:
            factor *= (table.dark_sight_mining_pct / PERCENT if NaturalTrait.DARK_SIGHT in traits else 1.0) * (
                table.burrowing_mining_pct / PERCENT if NaturalTrait.BURROWING in traits else 1.0
            )
        if job is Job.FISHING and NaturalTrait.AMPHIBIOUS in traits:
            factor *= table.amphibious_fishing_pct / PERCENT
        if job is Job.HERDING and NaturalTrait.KEEN_SENSES in traits:
            factor *= table.keen_senses_herding_pct / PERCENT
        if job is Job.BUILDING and NaturalTrait.HIVE_MINDED in traits:
            factor *= table.hive_building_pct / PERCENT
        if job is Job.TRADE and NaturalTrait.WINGED in traits:
            factor *= table.winged_trade_pct / PERCENT
        value = scaled(factor, table.labour_pct)
        if value != 1.0:
            found[job] = value
    return found


def trait_edge(
    rules: Rules,
    traits: set[NaturalTrait],
    *,
    terrain: TerrainKind | None,
    weather: WeatherKind | None,
    night: bool,
    river: bool,
    defending: bool,
    band: TemperatureBand | None,
) -> float:
    table = rules.biology
    factor = 1.0
    if NaturalTrait.DARK_SIGHT in traits and night:
        factor *= table.dark_sight_night_pct / PERCENT
    if NaturalTrait.COLD_BLOODED in traits:
        if weather in WINTER:
            factor *= table.cold_blooded_winter_pct / PERCENT
        elif band in WARM or weather in HOT_WEATHER:
            factor *= table.cold_blooded_heat_pct / PERCENT
    if NaturalTrait.WINGED in traits and (terrain in HEIGHTS or river):
        factor *= table.winged_heights_pct / PERCENT
    if NaturalTrait.AMPHIBIOUS in traits and (terrain in WATERS or river):
        factor *= table.amphibious_water_pct / PERCENT
    if NaturalTrait.THICK_HIDE in traits:
        factor *= table.thick_hide_pct / PERCENT
    if NaturalTrait.KEEN_SENSES in traits:
        factor *= scaled(table.keen_senses_pct / PERCENT, 2 * PERCENT if night else PERCENT)
    if NaturalTrait.VENOMOUS in traits:
        factor *= table.venomous_pct / PERCENT
    if NaturalTrait.REGENERATING in traits:
        factor *= table.regenerating_pct / PERCENT
    if NaturalTrait.BURROWING in traits and defending:
        factor *= table.burrowing_defence_pct / PERCENT
    if NaturalTrait.HIVE_MINDED in traits:
        factor *= table.hive_minded_pct / PERCENT
    return factor


def mastery(rules: Rules, culture: PeopleCultureRow | None) -> float:
    if culture is None:
        return 1.0
    wins, losses = record_of(culture, culture.martial_style.value)
    net = max(0, min(rules.biology.martial_mastery_cap, wins - losses))
    return 1 + net * rules.biology.martial_mastery_pct / PERCENT


def record_of(culture: PeopleCultureRow, style: str) -> tuple[int, int]:
    found = (culture.martial_record or {}).get(style) or [0, 0]
    return int(found[0]), int(found[1]) if len(found) > 1 else 0


def battle_edge(
    rules: Rules,
    biology: PeopleBiologyRow | None,
    culture: PeopleCultureRow | None,
    *,
    terrain: TerrainKind | None,
    weather: WeatherKind | None,
    night: bool,
    river: bool,
    defending: bool,
    band: TemperatureBand | None = None,
) -> float:
    if biology is None:
        return mastery(rules, culture)
    size = SIZES[biology.size_class].strength_pct / PERCENT
    ground = KIN[biology.body_plan].terrain.get(terrain, PERCENT) / PERCENT if terrain is not None else 1.0
    traits = trait_edge(rules, natures(biology), terrain=terrain, weather=weather, night=night, river=river, defending=defending, band=band)
    return scaled(size * ground * traits, rules.biology.battle_pct) * mastery(rules, culture)


def mount_fit(biology: PeopleBiologyRow | None) -> MountFit:
    if biology is None:
        return MountFit.RIDES
    fit = KIN[biology.body_plan].mount
    if fit is MountFit.RIDES and not SIZES[biology.size_class].rides:
        return MountFit.CANNOT
    return fit


def kin_army(
    rules: Rules,
    biology: PeopleBiologyRow | None,
    culture: PeopleCultureRow | None,
    plan: Mapping[UnitKind, float],
    *,
    beasts: set[str],
    mount_needs: Mapping[UnitKind, str],
) -> dict[UnitKind, float]:
    fit = mount_fit(biology)
    found: dict[UnitKind, float] = {}
    lifted = 0.0
    for kind, share in plan.items():
        need = mount_needs.get(kind)
        if kind in RIDDEN and fit is MountFit.IS_MOUNT:
            found[kind] = found.get(kind, 0.0) + share
            continue
        if kind in RIDDEN and fit in {MountFit.CANNOT, MountFit.FLIES}:
            lifted += share if fit is MountFit.FLIES else 0.0
            continue
        if need is not None and need not in beasts and not (kind is UnitKind.SKY_RIDERS and fit is MountFit.FLIES):
            continue
        fleet = scaled(KIN[biology.body_plan].naval_pct / PERCENT, rules.biology.naval_pct) if kind in NAVAL_UNITS and biology is not None else 1.0
        found[kind] = found.get(kind, 0.0) + share * fleet
    if lifted > 0:
        found[UnitKind.SKY_RIDERS] = found.get(UnitKind.SKY_RIDERS, 0.0) + lifted
    if culture is not None and raises_dead(culture.funeral_rite):
        found[UnitKind.SUMMONED_HOST] = found.get(UnitKind.SUMMONED_HOST, 0.0) + rules.customs.reanimation_host_pct / PERCENT
    return found


def band_gap(home: TemperatureBand, there: TemperatureBand) -> int:
    return BANDS.index(there) - BANDS.index(home)


def tolerance(rules: Rules, biology: PeopleBiologyRow, gap: int) -> int:
    traits = natures(biology)
    allowed = rules.biology.climate_tolerance_bands
    if gap < 0 and NaturalTrait.COLD_BLOODED in traits:
        allowed -= 1
    if gap < 0 and NaturalTrait.THICK_HIDE in traits:
        allowed += 1
    return max(0, allowed)


def acclimatised(rules: Rules, biology: PeopleBiologyRow | None, there: TemperatureBand | None) -> bool:
    if biology is None or there is None:
        return True
    gap = band_gap(biology.acclimatised, there)
    return abs(gap) <= tolerance(rules, biology, gap)


def climate_fit(rules: Rules, biology: PeopleBiologyRow | None, there: TemperatureBand | None) -> float:
    if biology is None or there is None:
        return 1.0
    gap = band_gap(biology.acclimatised, there)
    beyond = abs(gap) - tolerance(rules, biology, gap)
    if beyond <= 0:
        return 1.0
    table = rules.biology
    return max(table.climate_floor_pct / PERCENT, 1 - beyond * table.climate_penalty_pct / PERCENT)


def immunity_factor(rules: Rules, biology: PeopleBiologyRow | None, culture: PeopleCultureRow | None, disease_id: int, parent_id: int | None = None) -> float:
    factor = contagion(rules, culture.funeral_rite) if culture is not None else 1.0
    if biology is None:
        return factor
    table = rules.biology
    traits = natures(biology)
    if disease_id in biology.immunities or (parent_id is not None and parent_id in biology.immunities):
        factor *= table.homeland_immunity_pct / PERCENT
    factor *= KIN[biology.body_plan].disease_pct / PERCENT
    if NaturalTrait.REGENERATING in traits:
        factor *= table.regenerating_disease_pct / PERCENT
    if NaturalTrait.HIVE_MINDED in traits:
        factor *= table.hive_disease_pct / PERCENT
    return factor


async def profiles_of(session: AsyncSession, community: EntityRow) -> tuple[PeopleBiologyRow | None, PeopleCultureRow | None]:
    people = await people_of(session, community)
    if people is None:
        return None, None
    return await session.get(PeopleBiologyRow, people.id), await session.get(PeopleCultureRow, people.id)


async def kin_lethality(session: AsyncSession, rules: Rules, community: EntityRow, disease_id: int) -> float:
    biology, culture = await profiles_of(session, community)
    if biology is None and culture is None:
        return 1.0
    profile = await session.get(DiseaseProfileRow, disease_id)
    return immunity_factor(rules, biology, culture, disease_id, profile.parent_disease_id if profile is not None else None)
