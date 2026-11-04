from dataclasses import dataclass

from aerona.constants.units import PERCENT
from aerona.core.random import SeededRandom
from aerona.db.tables.environment import PlaceEnvironmentRow, RegionEnvironmentRow, WorldSeasonRow
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.environment import PlaceCover, ScarKind, TerrainKind, WeatherEffect
from aerona.domain.enums.world import WorldType
from aerona.engine.environment.book import EnvironmentBook, add_scar, season_attrition
from aerona.engine.environment.weather import Weather
from aerona.rules.registry import Rules

ENDLESS_DAY_WORLDS = frozenset({WorldType.TIDALLY_LOCKED, WorldType.HOT_GIANT, WorldType.CHTHONIAN, WorldType.HOLLOW})


@dataclass(frozen=True)
class BattleGround:
    region: RegionEnvironmentRow | None = None
    place: PlaceEnvironmentRow | None = None
    season: WorldSeasonRow | None = None
    weather: Weather | None = None
    year: int | None = None
    night: bool = False
    site_id: int | None = None

    @property
    def cover(self) -> PlaceCover | None:
        return self.place.cover if self.place is not None else None

    @property
    def terrain(self) -> TerrainKind | None:
        if self.place is not None and self.place.terrain is not None:
            return self.place.terrain
        return self.region.dominant_terrain if self.region is not None else None

    def describe(self) -> str:
        parts = []
        if self.season is not None and self.year is not None:
            parts.append(f"in the {self.season.name.lower()} of {self.year}")
        if self.weather is not None:
            parts.append(f"under {self.weather.label.lower()}")
        if self.night:
            parts.append("by night")
        terrain = self.terrain
        if terrain is not None:
            parts.append(f"on {terrain.value.replace('_', ' ')} ground")
        return ", ".join(parts)


def night_chance(rules: Rules, world_type: WorldType, day_length_hours: int | None) -> float:
    if world_type in ENDLESS_DAY_WORLDS:
        return 0.0
    settings = rules.campaigns
    hours = day_length_hours if day_length_hours is not None else settings.standard_day_hours
    return min(float(PERCENT), settings.night_battle_pct * hours / max(1, settings.standard_day_hours))


def attack_factor(rules: Rules, ground: BattleGround) -> float:
    settings = rules.campaigns
    if ground.weather is None and not ground.night:
        return 1.0
    footing = ground.weather.effect(WeatherEffect.FOOTING) if ground.weather is not None else 0
    visibility = (ground.weather.effect(WeatherEffect.VISIBILITY) if ground.weather is not None else 0) - (settings.night_visibility if ground.night else 0)
    factor = 1 + footing * settings.footing_attack_pct / PERCENT / PERCENT + visibility * settings.visibility_attack_pct / PERCENT / PERCENT
    return max(settings.attack_floor_pct / PERCENT, factor)


def defend_factor(rules: Rules, ground: BattleGround) -> float:
    settings = rules.campaigns
    factor = 1.0
    if ground.region is not None:
        factor += ground.region.defensibility * settings.defensibility_defender_pct / PERCENT / PERCENT
    if ground.place is not None:
        factor += ground.place.height_advantage * settings.height_defender_pct / PERCENT / PERCENT
        if ground.place.chokepoint:
            factor += settings.chokepoint_defender_pct / PERCENT
        factor += cover_defence(rules, ground.place.cover) / PERCENT
    return factor


def cover_defence(rules: Rules, cover: PlaceCover | None) -> int:
    table = rules.places
    if cover is PlaceCover.HEAVY:
        return table.cover_defender_heavy_pct
    if cover is PlaceCover.LIGHT:
        return table.cover_defender_light_pct
    return 0


def cover_missile_pct(rules: Rules, cover: PlaceCover | None) -> int:
    table = rules.places
    if cover is PlaceCover.HEAVY:
        return table.cover_missile_heavy_pct
    if cover is PlaceCover.LIGHT:
        return table.cover_missile_light_pct
    return PERCENT


def battle_site(rules: Rules, book: EnvironmentBook, region_id: int | None, rng: SeededRandom) -> PlaceEnvironmentRow | None:
    if region_id is None or not rng.chance(rules.places.chokepoint_battle_pct):
        return None
    sites = sorted(
        (place for place in book.places.values() if place.region_entity_id == region_id and place.chokepoint and place.entity_id in book.living_places),
        key=lambda place: (-place.height_advantage, place.entity_id),
    )
    return rng.pick(sites) if sites else None


def omen_morale(rules: Rules, weather: Weather | None, domains: frozenset[Domain], superstition: int) -> int:
    if weather is None:
        return 0
    return round(weather.omen_for(domains) * superstition / PERCENT * rules.campaigns.omen_morale_pct / PERCENT)


def season_losses(rules: Rules, weather: Weather | None, region: RegionEnvironmentRow | None, *, armour_pct: int, acclimatised: bool) -> float:
    if weather is None:
        return 0.0
    exposure = season_attrition(rules, weather, armour_pct=armour_pct, acclimatised=acclimatised)
    disease = region.disease_load if region is not None else 0
    camp = weather.effect(WeatherEffect.WET) * disease / PERCENT * rules.campaigns.camp_disease_pct / PERCENT / PERCENT
    return min(1.0, exposure + camp)


def scar_battlefield(rules: Rules, region: RegionEnvironmentRow, gap: float) -> int:
    settings = rules.scars
    return add_scar(region, ScarKind.BATTLEFIELD, settings.battle_depth_base + round(gap / max(1, settings.battle_depth_gap_divisor)))
