from collections.abc import Mapping

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.thermoregulation import UNTOUCHED, WARM_KEEPING
from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.read_memo import memoized
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow, WorldSeasonRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import TemperatureBand
from aerona.domain.enums.nature import Dormancy, Thermoregulation
from aerona.engine.environment.profile import band_of
from aerona.rules.registry import Rules

COLD = frozenset({TemperatureBand.FROZEN, TemperatureBand.COLD})
HEAT = frozenset({TemperatureBand.HOT, TemperatureBand.SEARING})
SLEEP_BANDS: Mapping[Dormancy, frozenset[TemperatureBand]] = total(
    Dormancy,
    {
        Dormancy.NONE: frozenset(),
        Dormancy.HIBERNATION: COLD,
        Dormancy.AESTIVATION: HEAT,
        Dormancy.TORPOR: frozenset(),
        Dormancy.CRYPTOBIOSIS: frozenset({TemperatureBand.FROZEN, TemperatureBand.SEARING}),
    },
)
CHAIN_DEPTH = 8


@memoized(RegionEnvironmentRow, WorldSeasonRow)
async def season_temperatures(session: AsyncSession, epoch: int) -> dict[int, int]:
    seasons: dict[int, list[WorldSeasonRow]] = {}
    for row in await session.scalars(select(WorldSeasonRow).order_by(WorldSeasonRow.world_id, WorldSeasonRow.position)):
        seasons.setdefault(row.world_id, []).append(row)
    found: dict[int, int] = {}
    for land in await session.scalars(select(RegionEnvironmentRow)):
        cycle = seasons.get(land.world_id, [])
        shift = round(cycle[epoch % len(cycle)].temperature_shift * land.seasonality / PERCENT) if cycle else 0
        found[land.entity_id] = land.temperature + shift
    return found


async def season_bands(session: AsyncSession, rules: Rules, epoch: int) -> dict[int, TemperatureBand]:
    return {region: band_of(rules, value) for region, value in (await season_temperatures(session, epoch)).items()}


async def region_of(session: AsyncSession, node_id: int | None) -> int | None:
    current = await session.get(EntityRow, node_id) if node_id is not None else None
    for _ in range(CHAIN_DEPTH):
        if current is None:
            return None
        if current.entity_type is EntityType.REGION:
            return current.id
        current = await session.get(EntityRow, current.location_id) if current.location_id is not None else None
    return None


async def band_at(session: AsyncSession, rules: Rules, epoch: int, node_id: int | None) -> TemperatureBand | None:
    region = await region_of(session, node_id)
    temperature = (await season_temperatures(session, epoch)).get(region) if region is not None else None
    return band_of(rules, temperature) if temperature is not None else None


def asleep(dormancy: Dormancy, band: TemperatureBand | None) -> bool:
    return band in SLEEP_BANDS[dormancy]


def chilled(thermoregulation: Thermoregulation, band: TemperatureBand | None) -> bool:
    return thermoregulation in WARM_KEEPING and band in COLD


def activity(rules: Rules, thermoregulation: Thermoregulation, band: TemperatureBand | None) -> float:
    if thermoregulation in UNTOUCHED or band is None:
        return 1.0
    if thermoregulation is Thermoregulation.HETEROTHERM:
        return 1.0 if band not in COLD else 1 - (1 - activity(rules, Thermoregulation.ECTOTHERM, band)) * rules.thermoregulation.heterotherm_switch / PERCENT
    table = rules.thermoregulation
    shares = {
        TemperatureBand.FROZEN: table.frozen_pct,
        TemperatureBand.COLD: table.cold_pct,
        TemperatureBand.WARM: table.warm_pct,
        TemperatureBand.HOT: table.hot_pct,
        TemperatureBand.SEARING: table.hot_pct,
    }
    return shares.get(band, PERCENT) / PERCENT


def softened(factor: float, share_pct: int) -> float:
    return 1 + (factor - 1) * share_pct / PERCENT
