from collections.abc import Callable
from dataclasses import dataclass

from aerona.constants.units import PERCENT
from aerona.db.tables.disease import DiseaseProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.domain.enums.disease import DiseaseVector, SpreadPath
from aerona.domain.enums.environment import RiverClass, ScarKind
from aerona.engine.disease.book import DiseaseBook
from aerona.engine.disease.emergence import COLD_BANDS, DRY, VOID_SCARS, WET
from aerona.engine.primitives.stats import stat

CONTACT_PATHS = frozenset({SpreadPath.ROUTE, SpreadPath.ARMY, SpreadPath.JOURNEY, SpreadPath.SIEGE})
VOID_EXPOSURE = (ScarKind.LEAK_WOUND.value, *VOID_SCARS)


def pct(value: int) -> float:
    return value / PERCENT


def blend(low: int, high: int, share: float) -> float:
    return pct(low) + (pct(high) - pct(low)) * max(0.0, min(1.0, share))


def void_exposure(ground: RegionEnvironmentRow | None) -> float:
    if ground is None:
        return 0.0
    return min(1.0, max((ground.scars.get(key, 0) for key in VOID_EXPOSURE), default=0) / PERCENT)


def air(book: DiseaseBook, ground: RegionEnvironmentRow | None) -> float:
    huddled = ground is not None and (ground.temperature_band in COLD_BANDS or ground.rainfall <= DRY)
    return pct(book.rules.epidemiology.air_cold_pct) if huddled else 1.0


def water(book: DiseaseBook, ground: RegionEnvironmentRow | None) -> float:
    table = book.rules.epidemiology
    wet = ground is not None and (ground.river_class is not RiverClass.NONE or ground.wetland >= WET)
    return pct(table.water_river_pct if wet else table.water_dry_pct)


def touch(book: DiseaseBook, path: SpreadPath) -> float:
    table = book.rules.epidemiology
    return pct(table.touch_contact_pct if path in CONTACT_PATHS else table.touch_still_pct)


def bite(book: DiseaseBook, disease_id: int, region_id: int | None) -> float:
    table = book.rules.epidemiology
    abundance = book.host_abundance(disease_id, region_id)
    if abundance <= 0:
        return pct(table.bite_hostless_pct)
    return blend(table.bite_hostless_pct, table.bite_host_pct, abundance)


def spirit(book: DiseaseBook, target: EntityRow, ground: RegionEnvironmentRow | None, region_id: int | None) -> float:
    table = book.rules.epidemiology
    magic = ground.magic_density / PERCENT if ground is not None else 0.0
    factor = blend(PERCENT, table.spirit_magic_pct, magic)
    if region_id is not None and region_id in book.ley:
        factor *= pct(table.spirit_ley_pct)
    piety = max(0, min(PERCENT, stat(target, "piety") or 0)) / PERCENT
    return factor * blend(PERCENT, table.spirit_faith_pct, piety)


def void(book: DiseaseBook, ground: RegionEnvironmentRow | None) -> float:
    table = book.rules.epidemiology
    exposure = void_exposure(ground)
    if exposure <= 0:
        return pct(table.void_clean_pct)
    return blend(table.void_clean_pct, table.void_scar_pct, exposure)


def curse(book: DiseaseBook, disease: EntityRow | None) -> float:
    table = book.rules.epidemiology
    bound = disease is not None and disease.creator_son_id is not None and disease.creator_son_id in book.living_sons
    return pct(table.curse_bound_pct if bound else table.curse_unbound_pct)


@dataclass(frozen=True)
class Spot:
    target: EntityRow
    ground: RegionEnvironmentRow | None
    region_id: int | None
    path: SpreadPath


def vector_factor(book: DiseaseBook, profile: DiseaseProfileRow, spot: Spot) -> float:
    readers: dict[DiseaseVector, Callable[[], float]] = {
        DiseaseVector.AIR: lambda: air(book, spot.ground),
        DiseaseVector.WATER: lambda: water(book, spot.ground),
        DiseaseVector.TOUCH: lambda: touch(book, spot.path),
        DiseaseVector.BITE: lambda: bite(book, profile.disease_entity_id, spot.region_id),
        DiseaseVector.SPIRIT: lambda: spirit(book, spot.target, spot.ground, spot.region_id),
        DiseaseVector.VOID: lambda: void(book, spot.ground),
        DiseaseVector.CURSE: lambda: curse(book, book.diseases.get(profile.disease_entity_id)),
    }
    return readers[profile.vector]()


def crowd_weight(book: DiseaseBook, profile: DiseaseProfileRow) -> float:
    table = book.rules.epidemiology
    return pct(table.crowd_spread_pct) * (pct(table.air_crowd_pct) if profile.vector is DiseaseVector.AIR else 1.0)


def sanitation_weight(book: DiseaseBook, profile: DiseaseProfileRow) -> float:
    table = book.rules.epidemiology
    if profile.vector is DiseaseVector.CURSE:
        return 0.0
    return pct(table.sanitation_spread_pct) * (pct(table.water_sanitation_pct) if profile.vector is DiseaseVector.WATER else 1.0)


def host_factor(book: DiseaseBook, profile: DiseaseProfileRow, region_id: int | None) -> float:
    if profile.vector is DiseaseVector.BITE or not book.host_bound(profile.disease_entity_id):
        return 1.0
    return 1 + book.host_abundance(profile.disease_entity_id, region_id) * pct(book.rules.epidemiology.host_spread_pct)
