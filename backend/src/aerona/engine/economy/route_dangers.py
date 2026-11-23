from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.kinds.trade_modes import TRADE_LOSS_CULPRITS, TRADE_LOSSES, TRADE_MODES
from aerona.catalog.life.economy import EFFECT_WEIGHT
from aerona.catalog.life_traits import STANCE_TRAITS, TRADE_MODE_TRAITS, WEATHER_EFFECT_TRAITS, having
from aerona.catalog.terrain import terrains
from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.ecology import BeastProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow, WorldSeasonRow
from aerona.db.tables.military import ArmyProfileRow
from aerona.db.tables.warfare import ArmyRow
from aerona.domain.enums.ecology import BeastTemper
from aerona.domain.enums.economy import CommodityKind, TradeLoss, TradeMode
from aerona.domain.enums.entity import EngineKind, EntityType
from aerona.domain.enums.environment import TerrainTrait, WeatherEffect
from aerona.domain.enums.life_traits import StanceTrait, TradeModeTrait, WeatherEffectTrait
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.operations import CarrierKind
from aerona.domain.enums.records import FactUnit, StepAction, StepLocus
from aerona.engine.context import TickContext
from aerona.engine.creature_groups.groups import group_danger
from aerona.engine.economy.book import EconomyBook
from aerona.engine.environment.weather import Weather
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import stat
from aerona.engine.recording.record import StepDraft, record
from aerona.rules.registry import Rules

PATROLS = having(STANCE_TRAITS, StanceTrait.PATROLS)
BANDIT_KINDS = frozenset({EngineKind.REBELS, EngineKind.ROUTE_RAIDERS})
CARAVAN_TERRAIN = terrains(TerrainTrait.ARID)
PASS_TERRAIN = terrains(every=(TerrainTrait.HIGH, TerrainTrait.COLD))
TEMPER_WEIGHT: MappingProxyType[BeastTemper, Callable[[Rules], int]] = total(
    BeastTemper,
    {
        BeastTemper.HUNGRY: lambda rules: rules.route_dangers.beast_hungry_pct,
        BeastTemper.TERRITORIAL: lambda rules: rules.route_dangers.beast_territorial_pct,
        BeastTemper.ENRAGED: lambda rules: rules.route_dangers.beast_enraged_pct,
        BeastTemper.SLEEPING: lambda rules: rules.route_dangers.beast_sleeping_pct,
        BeastTemper.BOUND: lambda rules: rules.route_dangers.beast_bound_pct,
        BeastTemper.TAMED: lambda rules: rules.route_dangers.beast_tamed_pct,
        BeastTemper.COMPANION: lambda rules: rules.route_dangers.beast_tamed_pct,
        BeastTemper.WOUNDED: lambda rules: rules.route_dangers.beast_enraged_pct,
        BeastTemper.BROODING: lambda rules: rules.route_dangers.beast_territorial_pct,
        BeastTemper.COWED: lambda rules: rules.route_dangers.beast_sleeping_pct,
    },
)
FALLING_EFFECTS = having(WEATHER_EFFECT_TRAITS, WeatherEffectTrait.FALLING_EFFECTS)


SPOIL_SPAN = 10


@dataclass
class Dangers:
    bandits: int = 0
    beasts: int = 0
    weather: int = 0
    sea: int = 0
    officials: int = 0
    spoilage: int = 0
    pilferage: int = 0
    bandit_id: int | None = None
    beast_id: int | None = None
    official_id: int | None = None

    @property
    def total(self) -> int:
        return clamp_int(sum(int(getattr(self, cause.value)) for cause in TradeLoss), 0, PERCENT)

    def parts(self) -> dict[TradeLoss, int]:
        return {cause: int(getattr(self, cause.value)) for cause in TradeLoss}

    def reckon(self, rules: Rules) -> "Dangers":
        for cause, spec in TRADE_LOSSES.items():
            if spec.reckoned:
                setattr(self, cause.value, clamp_int(int(getattr(self, cause.value)) * int(getattr(rules.route_dangers, spec.rule)) // PERCENT, 0, PERCENT))
        return self

    def culprit(self, cause: TradeLoss) -> int | None:
        attribute = TRADE_LOSS_CULPRITS[cause]
        found: int | None = getattr(self, attribute) if attribute is not None else None
        return found


@dataclass
class Lairs:
    beasts: dict[int, list[tuple[EntityRow, BeastProfileRow]]] = field(default_factory=dict)
    patrolled: frozenset[int] = frozenset()
    groups: dict[int, float] = field(default_factory=dict)

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
        return cls(dict(found), await patrolled_regions(ctx), await group_danger(ctx.session, ctx.rules))


async def patrolled_regions(ctx: TickContext) -> frozenset[int]:
    return await patrolled_regions_of(ctx.session)


async def patrolled_regions_of(session: AsyncSession) -> frozenset[int]:
    standing = select(ArmyRow.entity_id).where(ArmyRow.disbanded_epoch.is_(None))
    rows = await session.scalars(
        select(ArmyProfileRow.region_entity_id).where(
            ArmyProfileRow.army_entity_id.in_(standing), ArmyProfileRow.stance.in_(list(PATROLS)), ArmyProfileRow.region_entity_id.is_not(None)
        )
    )
    return frozenset(region for region in rows if region is not None)


def split(lost: int, parts: dict[TradeLoss, int], mode: TradeMode) -> dict[TradeLoss, int]:
    weights = {cause: value for cause, value in parts.items() if value > 0}
    if lost <= 0:
        return {}
    if not weights:
        return {TradeLoss.SEA if TRADE_MODES[mode].seagoing else TradeLoss.BANDITS: lost}
    summed = sum(weights.values())
    shares = {cause: lost * value // summed for cause, value in weights.items()}
    rest = lost - sum(shares.values())
    for cause in sorted(weights, key=lambda item: (-(lost * weights[item] % summed), item.value))[:rest]:
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


def patrol_share(rules: Rules, path: list[int], patrolled: frozenset[int]) -> float:
    if not path or not patrolled:
        return 0.0
    return rules.army_depth.patrol_pct / PERCENT * sum(1 for region in path if region in patrolled) / len(path)


def bandit_danger(rules: Rules, book: EconomyBook, path: list[int], patrolled: frozenset[int] = frozenset()) -> tuple[int, int | None]:
    table = rules.route_dangers
    dangers = [stat(book.entities[region], "danger") or 0 for region in path if region in book.entities]
    wild = sum(dangers) / len(dangers) if dangers else 0.0
    band = bandits_on(book, path)
    value = wild * table.bandit_region_pct / PERCENT + (table.bandit_band_danger if band is not None else 0)
    value *= 1 - patrol_share(rules, path, patrolled)
    return clamp_int(round_half_up(value), 0, PERCENT), band.id if band is not None else None


def beast_danger(rules: Rules, path: list[int], lairs: Lairs) -> tuple[int, int | None]:
    table = rules.route_dangers
    summed = 0.0
    worst: tuple[float, int] | None = None
    seen: set[int] = set()
    for region in path:
        for beast, profile in lairs.beasts.get(region, []):
            if beast.id in seen:
                continue
            seen.add(beast.id)
            threat = (stat(beast, "danger") or 0) * table.beast_danger_pct / PERCENT * TEMPER_WEIGHT[profile.temper](rules) / PERCENT
            summed += threat
            if threat > 0 and (worst is None or threat > worst[0]):
                worst = (threat, beast.id)
    summed += sum(lairs.groups.get(region, 0.0) for region in set(path))
    return clamp_int(round_half_up(summed), 0, PERCENT), worst[1] if worst is not None else None


def harm(weather: Weather, effect: WeatherEffect) -> int:
    value = weather.effect(effect)
    return max(0, -value) if effect in FALLING_EFFECTS else max(0, value)


def weather_weight(rules: Rules, mode: TradeMode, carrier: CarrierKind | None, regions: Sequence[RegionEnvironmentRow]) -> int:
    if carrier is CarrierKind.PACK_ANIMALS and any(region.dominant_terrain in CARAVAN_TERRAIN for region in regions):
        return rules.route_dangers.caravan_weather_pct
    return int(getattr(rules.route_dangers, TRADE_MODES[mode].weather_rule))


def weather_danger(
    ctx: TickContext, book: EconomyBook, mode: TradeMode, path: list[int], *, route_id: int, world_id: int | None, carrier: CarrierKind | None = None
) -> int:
    regions = [row for row in (book.ground.regions.get(region) for region in path) if row is not None]
    if not regions or world_id is None:
        return 0
    season = book.ground.season_at(world_id, ctx.epoch)
    scores: list[float] = []
    for region in regions:
        weather = book.ground.weather(ctx.environment.world_seed, ctx.epoch, region, season, f"route.{route_id}")
        scores.append(sum(harm(weather, effect) * EFFECT_WEIGHT[effect](ctx.rules) / PERCENT for effect in TRADE_MODES[mode].exposure))
    weight = weather_weight(ctx.rules, mode, carrier, regions)
    return clamp_int(round_half_up(sum(scores) / len(scores) * weight / PERCENT), 0, PERCENT)


def dangers_of(
    ctx: TickContext,
    book: EconomyBook,
    mode: TradeMode,
    path: list[int],
    lairs: Lairs,
    *,
    route_id: int,
    world_id: int | None,
    carrier: CarrierKind | None = None,
) -> Dangers:
    bandits, band = bandit_danger(ctx.rules, book, path, lairs.patrolled)
    beasts, beast = beast_danger(ctx.rules, path, lairs)
    weather = weather_danger(ctx, book, mode, path, route_id=route_id, world_id=world_id, carrier=carrier)
    table = ctx.rules.route_dangers
    spoilage = clamp_int(table.spoilage_pct * len(path) // max(1, SPOIL_SPAN), 0, PERCENT)
    pilferage = 0 if any(region in lairs.patrolled for region in path) else table.pilferage_pct
    if TRADE_MODES[mode].seagoing:
        sea = clamp_int(ctx.rules.route_dangers.sea_danger_base + weather, 0, PERCENT)
        return Dangers(bandits=bandits, beasts=beasts, sea=sea, spoilage=spoilage, pilferage=pilferage, bandit_id=band, beast_id=beast).reckon(ctx.rules)
    return Dangers(bandits=bandits, beasts=beasts, weather=weather, spoilage=spoilage, pilferage=pilferage, bandit_id=band, beast_id=beast).reckon(ctx.rules)


ICE_MODES = having(TRADE_MODE_TRAITS, TradeModeTrait.ICE_MODES)


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
    if any(region.dominant_terrain in CARAVAN_TERRAIN for region in regions):
        burning = any(region.dominant_terrain in CARAVAN_TERRAIN and season_heat(region, season) > table.burning_temperature for region in regions)
        loss += table.caravan_heat_pct * burning
    return loss


def froze(rules: Rules, book: EconomyBook, mode: TradeMode, path: list[int], world_id: int | None) -> bool:
    if world_id is None or mode not in ICE_MODES:
        return False
    seasons = book.ground.seasons_of(world_id)
    regions = [row for row in (book.ground.regions.get(region) for region in path) if row is not None]
    cold = [region for region in regions if any(season_heat(region, season) < rules.route_seasons.freeze_temperature for season in seasons)]
    return bool(cold) if mode is TradeMode.RIVER else any(high(rules, region) for region in cold)


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
    if units > 0:
        await record(
            ctx,
            "trade_route.beast_raid",
            roles={IncidentRole.ACTOR: beast.id, IncidentRole.SUBJECT: route.id},
            facts={"good": commodity, "units": units, "hoarded": taken},
            steps=(StepDraft(StepAction.SEIZE_GOODS, actor=beast.id, target=route.id, amount=units, unit=FactUnit.COUNT),),
        )


async def spoil(ctx: TickContext, route: EntityRow, commodity: CommodityKind, *, units: int, mode: TradeMode, frozen: bool = False) -> None:
    if units <= 0:
        return
    await record(
        ctx,
        "trade_route.weather_loss",
        roles={IncidentRole.SUBJECT: route.id},
        facts={"good": commodity, "units": units, "mode": mode},
        steps=(StepDraft(StepAction.FREEZE, target=route.id, locus_kind=StepLocus.ROUTE, locus_node=route.id, amount=units, unit=FactUnit.COUNT),)
        if frozen
        else (),
    )
