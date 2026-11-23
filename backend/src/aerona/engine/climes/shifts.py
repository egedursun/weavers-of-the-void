from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.life.climes import PHASE_SIGN, SKY_READING
from aerona.catalog.wind_belts import BELTS, CURRENTS
from aerona.constants.units import PERCENT
from aerona.db.tables.climes import ClimateOscillationRow, MonsoonSeasonRow, RegionWindRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.domain.enums.cosmography import OceanCurrent
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.environment import CoastKind
from aerona.engine.body.customs import people_of
from aerona.engine.lore.research import has_technique
from aerona.rules.registry import Rules


def oscillation_shift(rules: Rules, row: ClimateOscillationRow | None, env: RegionEnvironmentRow) -> tuple[int, int]:
    if row is None or PHASE_SIGN[row.phase] == 0 or abs(env.latitude) > rules.oscillations.latitude_reach:
        return 0, 0
    sign = PHASE_SIGN[row.phase]
    coastal = env.coast_kind is not CoastKind.NONE
    rain = -sign * row.strength if coastal else sign * row.strength // 2
    return rain, sign * row.strength // 2


async def clime_shifts(session: AsyncSession, rules: Rules, epoch: int) -> dict[int, tuple[int, int]]:
    oscillations = {row.world_id: row for row in await session.scalars(select(ClimateOscillationRow))}
    seasons = {row.world_id: row for row in await session.scalars(select(MonsoonSeasonRow).where(MonsoonSeasonRow.epoch == epoch))}
    winds = {row.region_entity_id: row for row in await session.scalars(select(RegionWindRow))}
    found: dict[int, tuple[int, int]] = {}
    for env in await session.scalars(select(RegionEnvironmentRow)):
        wind = winds.get(env.entity_id)
        rain, heat = oscillation_shift(rules, oscillations.get(env.world_id), env)
        if wind is not None:
            rain += BELTS[wind.band].rain_pct(rules) * rules.winds.band_rain_points // PERCENT
            rain -= rain * rules.currents.upwelling_rain_cut_pct // PERCENT if env.current is OceanCurrent.UPWELLING and rain > 0 else 0
            rain += rules.winds.windward_rain if wind.windward else 0
            rain -= wind.shadow
            if wind.monsoon:
                season = seasons.get(env.world_id)
                strength = season.strength if season is not None else PERCENT
                rain += round(wind.monsoon * strength / PERCENT * rules.monsoons.rain_pct / PERCENT)
        if rain or heat:
            found[env.entity_id] = (rain, heat)
    return found


async def prevailing(session: AsyncSession, region_id: int | None) -> int | None:
    row = await session.get(RegionWindRow, region_id) if region_id is not None else None
    return row.wind_from if row is not None and row.strength > 0 else None


async def upwelling(session: AsyncSession, rules: Rules, region_id: int) -> float:
    row = await session.get(RegionWindRow, region_id)
    if row is None or not row.upwelling:
        return 1.0
    env = await session.get(RegionEnvironmentRow, region_id)
    oscillation = await session.get(ClimateOscillationRow, env.world_id) if env is not None else None
    warm = oscillation is not None and PHASE_SIGN[oscillation.phase] > 0
    gain = (rules.currents.upwelling_catch_pct + rules.currents.upwelling_fish_pct) / PERCENT
    return 1 + gain * (1 - rules.currents.warm_phase_upwelling_cut_pct / PERCENT if warm else 1.0)


async def monsoon_sailing(session: AsyncSession, rules: Rules, env: RegionEnvironmentRow, epoch: int) -> float | None:
    wind = await session.get(RegionWindRow, env.entity_id)
    season = await session.get(MonsoonSeasonRow, (env.world_id, epoch)) if wind is not None and wind.monsoon > 0 else None
    if season is None:
        return None
    if season.failed:
        return 1 + rules.monsoons.sea_danger_pct / PERCENT
    return 1 - rules.monsoons.sea_danger_pct / PERCENT if season.strength > PERCENT else 1.0


async def sea_navigation(session: AsyncSession, rules: Rules, ends: tuple[int, int], epoch: int) -> float:
    seasons: list[float] = []
    belts: list[float] = []
    warm = False
    for end in ends:
        town = await session.get(EntityRow, end)
        env = await session.get(RegionEnvironmentRow, town.location_id) if town is not None and town.location_id is not None else None
        if env is None:
            continue
        warm = warm or env.current is OceanCurrent.WARM
        season = await monsoon_sailing(session, rules, env, epoch)
        if season is not None:
            seasons.append(season)
        wind = await session.get(RegionWindRow, env.entity_id)
        belts.append(1 - BELTS[wind.band].sailing_pct(rules) / PERCENT if wind is not None else 1.0)
        belts.append(1 - CURRENTS[env.current].sailing_pct(rules) / PERCENT)
    sailing = max(belts, default=1.0)
    return max(seasons, default=1.0) * sailing * (1 - rules.currents.current_speed_pct / PERCENT if warm else 1.0)


async def fire_wind(session: AsyncSession, rules: Rules, region_id: int) -> float:
    row = await session.get(RegionWindRow, region_id)
    return 1 + row.strength / PERCENT * rules.winds.fire_wind_pct / PERCENT if row is not None else 1.0


async def oscillation_sight(session: AsyncSession, rules: Rules, seer_id: int, world_id: int | None) -> int:
    if world_id is None or await session.get(ClimateOscillationRow, world_id) is None:
        return 0
    seer = await session.get(EntityRow, seer_id)
    people = await people_of(session, seer) if seer is not None else None
    holders = [seer_id, *([people.id] if people is not None else [])]
    for technique in SKY_READING:
        for holder in holders:
            if await has_technique(session, holder, technique):
                return rules.oscillations.sight_bonus
    return 0


async def current_coasts(session: AsyncSession) -> list[tuple[int, int]]:
    rows = await session.execute(
        select(EntityRow.world_id, EntityRow.id)
        .join(RegionEnvironmentRow, RegionEnvironmentRow.entity_id == EntityRow.location_id)
        .where(
            EntityRow.entity_type == EntityType.SETTLEMENT,
            EntityRow.status == EntityStatus.CANON,
            RegionEnvironmentRow.current != OceanCurrent.NONE,
            RegionEnvironmentRow.coast_kind != CoastKind.NONE,
        )
        .order_by(EntityRow.world_id, RegionEnvironmentRow.entity_id, EntityRow.id)
    )
    coasts: dict[int | None, list[int]] = {}
    for world_id, town in rows.all():
        coasts.setdefault(world_id, []).append(town)
    return [(towns[index], towns[(index + 1) % len(towns)]) for towns in coasts.values() if len(towns) > 1 for index in range(len(towns))]
