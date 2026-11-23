from itertools import groupby

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.calendar_slots import SLOTS
from aerona.catalog.long_seasons import CAUSES
from aerona.constants.calendar import SHARE_TOTAL
from aerona.db.tables.ages import IrregularSeasonRow, WinterForecastRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.culture import TraditionProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import WorldSeasonRow
from aerona.db.tables.physics import ImpactEventRow
from aerona.domain.enums.ages import LongSeasonReach, SeasonCause, SeasonSpell, SeasonSpellShape
from aerona.domain.enums.culture import CalendarSlot, SlotOpening
from aerona.domain.enums.physics import ImpactOutcome
from aerona.engine.environment.season_names import name_for_season
from aerona.engine.environment.season_shape import rebalanced
from aerona.rules.registry import Rules

SHARES_FIXUP = "seasons.w52_shares"
SOURCES_FIXUP = "long_seasons.w52_sources"
REMEMBRANCE_FIXUP = "named_years.w52_remembrance"
FIXED_NAMES = frozenset(
    {
        "Endless Day",
        "Wet Season",
        "Dry Season",
        "Inundation",
        "Growing",
        "Harvest",
        "Spring",
        "Summer",
        "Autumn",
        "Winter",
        "Monsoon",
        "Early Winter",
        "Deep Winter",
        "Long Winter",
        "Short Thaw",
    }
)


def even_shares(seasons: list[WorldSeasonRow]) -> dict[int, int]:
    base, left = divmod(SHARE_TOTAL, len(seasons))
    warmest = max(seasons, key=lambda season: (season.temperature_shift, -season.position)).position
    return {season.position: base + (left if season.position == warmest else 0) for season in seasons}


async def share_the_year(session: AsyncSession, rules: Rules) -> int:
    if await session.get(AppliedFixupRow, SHARES_FIXUP) is not None:
        return 0
    rows = list(await session.scalars(select(WorldSeasonRow).order_by(WorldSeasonRow.world_id, WorldSeasonRow.position)))
    shared = renamed = 0
    for world_id, group in groupby(rows, key=lambda row: row.world_id):
        seasons = list(group)
        world = await session.get(WorldRow, world_id)
        if sum(season.share_pct for season in seasons) != SHARE_TOTAL:
            shares = even_shares(seasons)
            for season in seasons:
                season.share_pct = shares[season.position]
            shared += 1
        for season in seasons:
            if world is not None and not season.edited and season.name in FIXED_NAMES:
                season.name = await name_for_season(session, rules, world, season.position)
                renamed += 1
    session.add(AppliedFixupRow(key=SHARES_FIXUP, result={"worlds": shared, "renamed": renamed}))
    await session.flush()
    return shared + renamed


async def uneven_years(session: AsyncSession) -> list[int]:
    rows = list(await session.scalars(select(WorldSeasonRow).order_by(WorldSeasonRow.world_id, WorldSeasonRow.position)))
    return [world_id for world_id, group in groupby(rows, key=lambda row: row.world_id) if sum(row.share_pct for row in group) != SHARE_TOTAL]


async def even_year(session: AsyncSession, world_id: int) -> None:
    seasons = list(await session.scalars(select(WorldSeasonRow).where(WorldSeasonRow.world_id == world_id).order_by(WorldSeasonRow.position)))
    if not seasons:
        return
    shares = rebalanced({season.position: season.share_pct for season in seasons}, {})
    for season in seasons:
        season.share_pct = shares[season.position]


async def strayed_spells(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for row in await session.scalars(select(IrregularSeasonRow).order_by(IrregularSeasonRow.id)):
        if "shape" not in row.locked and row.shape not in CAUSES[row.cause].shapes:
            found.append(row.id)
            continue
        region = await session.get(EntityRow, row.source_region_id) if row.source_region_id is not None else None
        impact = await session.get(ImpactEventRow, row.source_impact_id) if row.source_impact_id is not None else None
        if (region is not None and region.world_id != row.world_id) or (impact is not None and impact.world_id != row.world_id):
            found.append(row.id)
    return found


async def mend_spell(session: AsyncSession, key: int) -> None:
    row = await session.get(IrregularSeasonRow, key)
    if row is None:
        return
    if row.shape not in CAUSES[row.cause].shapes:
        row.shape = min(CAUSES[row.cause].shapes)
    region = await session.get(EntityRow, row.source_region_id) if row.source_region_id is not None else None
    if region is not None and region.world_id != row.world_id:
        row.source_region_id = None
    impact = await session.get(ImpactEventRow, row.source_impact_id) if row.source_impact_id is not None else None
    if impact is not None and impact.world_id != row.world_id:
        row.source_impact_id = None


async def strayed_forecasts(session: AsyncSession) -> list[int]:
    joined = select(WinterForecastRow.id).join(IrregularSeasonRow, IrregularSeasonRow.id == WinterForecastRow.long_season_id)
    return list(await session.scalars(joined.where(IrregularSeasonRow.world_id != WinterForecastRow.world_id).order_by(WinterForecastRow.id)))


async def follow_forecast(session: AsyncSession, key: int) -> None:
    row = await session.get(WinterForecastRow, key)
    spell = await session.get(IrregularSeasonRow, row.long_season_id) if row is not None else None
    if row is not None and spell is not None:
        row.world_id = spell.world_id


async def impact_winters(session: AsyncSession) -> int:
    if await session.get(AppliedFixupRow, SOURCES_FIXUP) is not None:
        return 0
    known = set(await session.scalars(select(IrregularSeasonRow.source_impact_id).where(IrregularSeasonRow.source_impact_id.is_not(None))))
    made = 0
    struck = select(ImpactEventRow).where(ImpactEventRow.outcome == ImpactOutcome.STRUCK, ImpactEventRow.winter_epochs > 0).order_by(ImpactEventRow.id)
    for impact in list(await session.scalars(struck)):
        if impact.id in known:
            continue
        session.add(
            IrregularSeasonRow(
                world_id=impact.world_id,
                cause=SeasonCause.IMPACT,
                shape=SeasonSpellShape.SINGLE,
                spell=SeasonSpell.WINTER,
                spell_started_epoch=impact.due_epoch,
                spell_length=impact.winter_epochs,
                severity=min(SHARE_TOTAL, impact.size),
                reach=LongSeasonReach.WORLD,
                source_impact_id=impact.id,
                locked=[],
            )
        )
        impact.winter_epochs = 0
        made += 1
    session.add(AppliedFixupRow(key=SOURCES_FIXUP, result={"spells": made}))
    await session.flush()
    return made


async def remembrance_slots(session: AsyncSession) -> int:
    if await session.get(AppliedFixupRow, REMEMBRANCE_FIXUP) is not None:
        return 0
    rows = await session.scalars(
        select(TraditionProfileRow).where(TraditionProfileRow.notable_year_id.is_not(None)).order_by(TraditionProfileRow.tradition_entity_id)
    )
    changed = 0
    for row in rows:
        loose = row.calendar_slot is None or SLOTS[row.calendar_slot].opening is SlotOpening.HOLY
        if loose and "calendar_slot" not in row.locked:
            row.calendar_slot = CalendarSlot.REMEMBRANCE
            changed += 1
    session.add(AppliedFixupRow(key=REMEMBRANCE_FIXUP, result={"traditions": changed}))
    await session.flush()
    return changed
