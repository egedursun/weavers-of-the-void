from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from types import MappingProxyType

from sqlalchemy import select

from aerona.catalog.commodities import COMMODITIES
from aerona.constants.units import PERCENT
from aerona.db.tables.ecology import BeastProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow, WorldSeasonRow
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.ecology import BeastTemper
from aerona.domain.enums.economy import CommodityKind, TradeLoss, TradeMode
from aerona.domain.enums.entity import EngineKind, EntityType
from aerona.domain.enums.environment import TerrainKind, WeatherEffect
from aerona.engine.context import TickContext
from aerona.engine.economy.book import EconomyBook
from aerona.engine.environment.weather import Weather
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules

BANDIT_KINDS = frozenset({EngineKind.REBELS, EngineKind.VOID_PIRATES})
CARAVAN_TERRAIN = frozenset({TerrainKind.DESERT, TerrainKind.STEPPE})
PASS_TERRAIN = frozenset({TerrainKind.MOUNTAINS, TerrainKind.HIGH_PASS})
DANGER_KEYS: MappingProxyType[TradeLoss, str] = MappingProxyType(
    {TradeLoss.BANDITS: "danger_bandits", TradeLoss.BEASTS: "danger_beasts", TradeLoss.WEATHER: "danger_weather", TradeLoss.SEA: "danger_sea"}
)
TEMPER_WEIGHT: MappingProxyType[BeastTemper, Callable[[Rules], int]] = MappingProxyType(
    {
        BeastTemper.HUNGRY: lambda rules: rules.route_dangers.beast_hungry_pct,
        BeastTemper.TERRITORIAL: lambda rules: rules.route_dangers.beast_territorial_pct,
        BeastTemper.ENRAGED: lambda rules: rules.route_dangers.beast_enraged_pct,
        BeastTemper.SLEEPING: lambda rules: rules.route_dangers.beast_sleeping_pct,
        BeastTemper.BOUND: lambda rules: rules.route_dangers.beast_bound_pct,
        BeastTemper.TAMED: lambda rules: rules.route_dangers.beast_tamed_pct,
    }
)
EFFECT_WEIGHT: MappingProxyType[WeatherEffect, Callable[[Rules], int]] = MappingProxyType(
    {
        WeatherEffect.FOOTING: lambda rules: rules.route_dangers.weather_footing_pct,
        WeatherEffect.COLD: lambda rules: rules.route_dangers.weather_cold_pct,
        WeatherEffect.HEAT: lambda rules: rules.route_dangers.weather_heat_pct,
        WeatherEffect.WET: lambda rules: rules.route_dangers.weather_wet_pct,
        WeatherEffect.WIND: lambda rules: rules.route_dangers.weather_wind_pct,
        WeatherEffect.VISIBILITY: lambda rules: rules.route_dangers.weather_visibility_pct,
    }
)
FALLING_EFFECTS = frozenset({WeatherEffect.FOOTING, WeatherEffect.VISIBILITY})
MODE_EXPOSURE: MappingProxyType[TradeMode, tuple[WeatherEffect, ...]] = MappingProxyType(
    {
        TradeMode.ROAD: (WeatherEffect.FOOTING, WeatherEffect.COLD, WeatherEffect.HEAT, WeatherEffect.WET),
        TradeMode.CARAVAN: (WeatherEffect.FOOTING, WeatherEffect.HEAT, WeatherEffect.WIND, WeatherEffect.VISIBILITY),
        TradeMode.RIVER: (WeatherEffect.WET, WeatherEffect.COLD, WeatherEffect.WIND),
        TradeMode.SKY: (WeatherEffect.WIND, WeatherEffect.VISIBILITY, WeatherEffect.COLD),
        TradeMode.SEA: (WeatherEffect.WIND, WeatherEffect.VISIBILITY, WeatherEffect.WET),
    }
)
MODE_WEATHER: MappingProxyType[TradeMode, Callable[[Rules], int]] = MappingProxyType(
    {
        TradeMode.ROAD: lambda rules: rules.route_dangers.road_weather_pct,
        TradeMode.CARAVAN: lambda rules: rules.route_dangers.caravan_weather_pct,
        TradeMode.RIVER: lambda rules: rules.route_dangers.river_weather_pct,
        TradeMode.SKY: lambda rules: rules.route_dangers.sky_weather_pct,
        TradeMode.SEA: lambda rules: rules.route_dangers.sea_weather_pct,
    }
)


@dataclass
class Dangers:
    bandits: int = 0
    beasts: int = 0
    weather: int = 0
    sea: int = 0
    bandit_id: int | None = None
    beast_id: int | None = None

    @property
    def total(self) -> int:
        return clamp_int(self.bandits + self.beasts + self.weather + self.sea, 0, PERCENT)

    def parts(self) -> dict[TradeLoss, int]:
        return {TradeLoss.BANDITS: self.bandits, TradeLoss.BEASTS: self.beasts, TradeLoss.WEATHER: self.weather, TradeLoss.SEA: self.sea}

    def culprit(self, cause: TradeLoss) -> int | None:
        return self.bandit_id if cause is TradeLoss.BANDITS else self.beast_id if cause is TradeLoss.BEASTS else None


@dataclass
class Lairs:
    beasts: dict[int, list[tuple[EntityRow, BeastProfileRow]]] = field(default_factory=dict)

    @classmethod
    async def load(cls, ctx: TickContext, book: EconomyBook) -> "Lairs":
        found: dict[int, list[tuple[EntityRow, BeastProfileRow]]] = defaultdict(list)
        for profile in await ctx.session.scalars(select(BeastProfileRow).order_by(BeastProfileRow.beast_entity_id)):
            beast = book.entities.get(profile.beast_entity_id)
            if beast is None or beast.entity_type is not EntityType.BEAST:
                continue
            regions = {book.ground.atlas.top_region(beast.id)}
            if profile.lair_place_id is not None:
                regions.add(book.ground.atlas.top_region(profile.lair_place_id))
            for region in regions - {None}:
                if region is not None:
                    found[region].append((beast, profile))
        return cls(dict(found))


def split(lost: int, parts: dict[TradeLoss, int], mode: TradeMode) -> dict[TradeLoss, int]:
    weights = {cause: value for cause, value in parts.items() if value > 0}
    if lost <= 0:
        return {}
    if not weights:
        return {TradeLoss.SEA if mode is TradeMode.SEA else TradeLoss.BANDITS: lost}
    total = sum(weights.values())
    shares = {cause: lost * value // total for cause, value in weights.items()}
    rest = lost - sum(shares.values())
    for cause in sorted(weights, key=lambda item: (-(lost * weights[item] % total), item.value))[:rest]:
        shares[cause] += 1
    return {cause: units for cause, units in shares.items() if units > 0}


def bandits_on(book: EconomyBook, path: list[int]) -> EntityRow | None:
    halfway = set(path)
    found = [
        entity
        for entity in book.entities.values()
        if entity.entity_type is EntityType.FACTION
        and (entity.engine_kind in BANDIT_KINDS or entity.id in book.robbers)
        and book.ground.atlas.top_region(entity.id) in halfway
    ]
    return min(found, key=lambda entity: entity.id) if found else None


def bandit_danger(rules: Rules, book: EconomyBook, path: list[int]) -> tuple[int, int | None]:
    table = rules.route_dangers
    dangers = [stat(book.entities[region], "danger") or 0 for region in path if region in book.entities]
    wild = sum(dangers) / len(dangers) if dangers else 0.0
    band = bandits_on(book, path)
    value = wild * table.bandit_region_pct / PERCENT + (table.bandit_band_danger if band is not None else 0)
    return clamp_int(round_half_up(value), 0, PERCENT), band.id if band is not None else None


def beast_danger(rules: Rules, path: list[int], lairs: Lairs) -> tuple[int, int | None]:
    table = rules.route_dangers
    total = 0.0
    worst: tuple[float, int] | None = None
    seen: set[int] = set()
    for region in path:
        for beast, profile in lairs.beasts.get(region, []):
            if beast.id in seen:
                continue
            seen.add(beast.id)
            threat = (stat(beast, "danger") or 0) * table.beast_danger_pct / PERCENT * TEMPER_WEIGHT[profile.temper](rules) / PERCENT
            total += threat
            if threat > 0 and (worst is None or threat > worst[0]):
                worst = (threat, beast.id)
    return clamp_int(round_half_up(total), 0, PERCENT), worst[1] if worst is not None else None


def harm(weather: Weather, effect: WeatherEffect) -> int:
    value = weather.effect(effect)
    return max(0, -value) if effect in FALLING_EFFECTS else max(0, value)


def weather_danger(ctx: TickContext, book: EconomyBook, mode: TradeMode, path: list[int], *, route_id: int, world_id: int | None) -> int:
    regions = [row for row in (book.ground.regions.get(region) for region in path) if row is not None]
    if not regions or world_id is None:
        return 0
    season = book.ground.season_at(world_id, ctx.epoch)
    scores: list[float] = []
    for region in regions:
        weather = book.ground.weather(ctx.environment.world_seed, ctx.epoch, region, season, f"route.{route_id}")
        scores.append(sum(harm(weather, effect) * EFFECT_WEIGHT[effect](ctx.rules) / PERCENT for effect in MODE_EXPOSURE[mode]))
    return clamp_int(round_half_up(sum(scores) / len(scores) * MODE_WEATHER[mode](ctx.rules) / PERCENT), 0, PERCENT)


def dangers_of(ctx: TickContext, book: EconomyBook, mode: TradeMode, path: list[int], lairs: Lairs, *, route_id: int, world_id: int | None) -> Dangers:
    bandits, band = bandit_danger(ctx.rules, book, path)
    beasts, beast = beast_danger(ctx.rules, path, lairs)
    weather = weather_danger(ctx, book, mode, path, route_id=route_id, world_id=world_id)
    if mode is TradeMode.SEA:
        sea = clamp_int(ctx.rules.route_dangers.sea_danger_base + weather, 0, PERCENT)
        return Dangers(bandits=bandits, beasts=beasts, sea=sea, bandit_id=band, beast_id=beast)
    return Dangers(bandits=bandits, beasts=beasts, weather=weather, bandit_id=band, beast_id=beast)


def season_heat(region: RegionEnvironmentRow, season: WorldSeasonRow) -> int:
    return region.temperature + round_half_up(season.temperature_shift * region.seasonality / PERCENT)


def season_rain(region: RegionEnvironmentRow, season: WorldSeasonRow) -> int:
    return round_half_up(season.rain_shift * region.seasonality / PERCENT)


def high(rules: Rules, region: RegionEnvironmentRow) -> bool:
    return region.dominant_terrain in PASS_TERRAIN or region.elevation_mean >= rules.route_seasons.pass_elevation


def season_loss(rules: Rules, mode: TradeMode, regions: list[RegionEnvironmentRow], season: WorldSeasonRow) -> float:
    table = rules.route_seasons
    hardship = (PERCENT - season.travel) / PERCENT
    frozen = any(season_heat(region, season) < table.freeze_temperature for region in regions)
    if mode is TradeMode.SEA:
        return rules.trade_routes.sea_season_pct * hardship
    if mode is TradeMode.RIVER:
        flooded = any(season_rain(region, season) >= table.flood_rain_shift for region in regions)
        return table.river_ice_pct * frozen + table.river_flood_pct * flooded
    if mode is TradeMode.SKY:
        stormy = max(hardship, max((season_rain(region, season) for region in regions), default=0) / PERCENT)
        return table.sky_season_pct * stormy
    snowed = any(high(rules, region) and season_heat(region, season) < table.freeze_temperature for region in regions)
    loss = table.land_season_pct * hardship + table.pass_snow_pct * snowed
    if mode is TradeMode.CARAVAN:
        burning = any(region.dominant_terrain in CARAVAN_TERRAIN and season_heat(region, season) > table.burning_temperature for region in regions)
        loss += table.caravan_heat_pct * burning
    return loss


def season_pct_of(rules: Rules, book: EconomyBook, mode: TradeMode, path: list[int], world_id: int | None) -> int:
    if world_id is None:
        return PERCENT
    seasons = book.ground.seasons_of(world_id)
    regions = [row for row in (book.ground.regions.get(region) for region in path) if row is not None]
    if not seasons:
        return PERCENT
    worst = max(season_loss(rules, mode, regions, season) for season in seasons)
    return clamp_int(round_half_up(PERCENT - worst), 0, PERCENT)


async def feed_beast(ctx: TickContext, book: EconomyBook, route: EntityRow, commodity: CommodityKind, *, units: int, beast_id: int | None) -> None:
    table = ctx.rules.route_dangers
    beast = book.entities.get(beast_id) if beast_id is not None else None
    profile = await ctx.session.get(BeastProfileRow, beast_id) if beast_id is not None else None
    if beast is None or profile is None:
        return
    taken = round_half_up(units * table.beast_hoard_pct / PERCENT)
    if taken > 0:
        hoard = dict(profile.hoard or {})
        hoard[commodity.value] = hoard.get(commodity.value, 0) + taken
        profile.hoard = hoard
    if units >= table.beast_note_units:
        await ctx.chronicle(
            ChronicleKind.DISASTER,
            f"{beast.name} fell on the caravans of {route.name} and dragged {units} loads of {COMMODITIES[commodity].label.lower()} to its lair.",
            template_key="trade_route.beast_raid",
            entity_ids=[route.id, beast.id],
        )


async def spoil(ctx: TickContext, route: EntityRow, commodity: CommodityKind, *, units: int, mode: TradeMode) -> None:
    if units < ctx.rules.route_dangers.weather_note_units:
        return
    await ctx.chronicle(
        ChronicleKind.DISASTER,
        f"Foul weather on {route.name} ruined {units} loads of {COMMODITIES[commodity].label.lower()} carried by {mode.value}.",
        template_key="trade_route.weather_loss",
        entity_ids=[route.id],
    )
