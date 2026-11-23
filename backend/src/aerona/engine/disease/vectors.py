from collections.abc import Callable, Mapping
from dataclasses import dataclass

from aerona.catalog.spread_paths import CONTACT_PATHS
from aerona.catalog.transmission import ROUTES, main_share
from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.disease import DiseaseProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.domain.enums.affliction import Transmission
from aerona.domain.enums.disease import SpreadPath
from aerona.domain.enums.environment import RiverClass, ScarKind
from aerona.domain.enums.evolution import PlagueResponse
from aerona.engine.disease.book import DiseaseBook
from aerona.engine.disease.emergence import COLD_BANDS, DRY, VOID_SCARS, WARM_BANDS, WET
from aerona.engine.primitives.stats import stat

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


def bite(book: DiseaseBook, disease_id: int, region_id: int | None, ground: RegionEnvironmentRow | None) -> float:
    table = book.rules.epidemiology
    abundance = book.host_abundance(disease_id, region_id)
    factor = pct(table.bite_hostless_pct) if abundance <= 0 else blend(table.bite_hostless_pct, table.bite_host_pct, abundance)
    return factor * climate_of_bites(book, ground)


def climate_of_bites(book: DiseaseBook, ground: RegionEnvironmentRow | None) -> float:
    table = book.rules.vectors
    if ground is None:
        return 1.0
    if ground.temperature_band in WARM_BANDS:
        return pct(table.warm_bite_pct)
    if ground.temperature_band in COLD_BANDS:
        return pct(table.cold_bite_pct)
    return 1.0


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


def constant(book: DiseaseBook) -> float:
    return 1.0


def ingestion(book: DiseaseBook, spot: Spot) -> float:
    return (1 + touch(book, spot.path)) / 2


def blood(book: DiseaseBook, profile: DiseaseProfileRow, spot: Spot) -> float:
    return bite(book, profile.disease_entity_id, spot.region_id, spot.ground)


def objects(book: DiseaseBook, spot: Spot) -> float:
    return touch(book, spot.path)


Reader = Callable[[DiseaseBook, DiseaseProfileRow, Spot], float]
READERS: Mapping[Transmission, Reader] = total(
    Transmission,
    {
        Transmission.INHALATION: lambda book, profile, spot: air(book, spot.ground),
        Transmission.WATER: lambda book, profile, spot: water(book, spot.ground),
        Transmission.CONTACT: lambda book, profile, spot: touch(book, spot.path),
        Transmission.BITE: lambda book, profile, spot: bite(book, profile.disease_entity_id, spot.region_id, spot.ground),
        Transmission.SPIRIT: lambda book, profile, spot: spirit(book, spot.target, spot.ground, spot.region_id),
        Transmission.VOID: lambda book, profile, spot: void(book, spot.ground),
        Transmission.CURSE: lambda book, profile, spot: curse(book, book.diseases.get(profile.disease_entity_id)),
        Transmission.INGESTION: lambda book, profile, spot: ingestion(book, spot),
        Transmission.BLOOD: blood,
        Transmission.BIRTH: lambda book, profile, spot: constant(book),
        Transmission.RITE: lambda book, profile, spot: constant(book),
        Transmission.GAZE: lambda book, profile, spot: constant(book),
        Transmission.EXPERIENCE: lambda book, profile, spot: constant(book),
        Transmission.INTIMATE: lambda book, profile, spot: constant(book),
        Transmission.OBJECTS: lambda book, profile, spot: objects(book, spot),
    },
)
DRINK_ROUTES = frozenset({Transmission.WATER, Transmission.INGESTION})
RATE_BASE = 50


def blocked(book: DiseaseBook, route: Transmission, profile: DiseaseProfileRow, spot: Spot) -> float:
    guarded = 1 - book.drink_guard(spot.target.id) if route in DRINK_ROUTES else 0.0
    taken = book.responses.get((spot.target.id, profile.disease_entity_id), set())
    cuts = [
        book.rules.plague_responses.sanitation_cut_pct / PERCENT if response is PlagueResponse.SANITATION else 1.0
        for response in taken & ROUTES[route].blocked_by
    ]
    answered = max(cuts, default=0.0)
    return max(guarded, answered)


def routes_of(book: DiseaseBook, profile: DiseaseProfileRow) -> list[tuple[Transmission, int]]:
    extra = [(route, share) for route, share in book.routes.get(profile.disease_entity_id, []) if route is not profile.primary_route]
    return [(profile.primary_route, main_share(share for _route, share in extra)), *extra]


def vector_factor(book: DiseaseBook, profile: DiseaseProfileRow, spot: Spot) -> float:
    found = 0.0
    for route, share in routes_of(book, profile):
        spec = ROUTES[route]
        cut = 1 - spec.block(book.rules) / PERCENT * blocked(book, route, profile, spot)
        found += share / PERCENT * READERS[route](book, profile, spot) * spec.rate(book.rules) / RATE_BASE * cut
    return found


def crowd_weight(book: DiseaseBook, profile: DiseaseProfileRow) -> float:
    table = book.rules.epidemiology
    return pct(table.crowd_spread_pct) * (pct(table.air_crowd_pct) if profile.primary_route is Transmission.INHALATION else 1.0)


def sanitation_weight(book: DiseaseBook, profile: DiseaseProfileRow) -> float:
    table = book.rules.epidemiology
    if profile.primary_route is Transmission.CURSE:
        return 0.0
    return pct(table.sanitation_spread_pct) * (pct(table.water_sanitation_pct) if profile.primary_route is Transmission.WATER else 1.0)


def host_factor(book: DiseaseBook, profile: DiseaseProfileRow, region_id: int | None) -> float:
    if profile.primary_route is Transmission.BITE or not book.host_bound(profile.disease_entity_id):
        return 1.0
    return 1 + book.host_abundance(profile.disease_entity_id, region_id) * pct(book.rules.epidemiology.host_spread_pct)
