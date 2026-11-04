from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.culture import TraditionProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import CalendarRow, NotableYearRow, RegionEnvironmentRow, WorldSeasonRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import TraditionKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus, EntityType
from aerona.domain.enums.environment import TemperatureBand
from aerona.domain.models.entity_stats import TraditionStats
from aerona.engine.context import TickContext
from aerona.engine.environment.battleground import ENDLESS_DAY_WORLDS
from aerona.engine.lore.traditions import Keeping, cost_for, profile_of
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.queries import connect
from aerona.engine.primitives.records import RecordSpec, create_record

K = TraditionKind
SEASON_HELD = "season_position"
CALENDAR_HELD = "calendar_entity_id"
HOLY_DAY_FIXUP = "lore.holy_day_traditions"
WARM_BANDS = frozenset({TemperatureBand.WARM, TemperatureBand.HOT, TemperatureBand.SEARING})
SLEEP_CUSTOMS = frozenset({K.SIESTA, K.NIGHT_VIGIL})

SeasonKey = Callable[[WorldSeasonRow], tuple[int, int]]


def _plenty(season: WorldSeasonRow) -> tuple[int, int]:
    return (season.growth, -season.position)


def _lean(season: WorldSeasonRow) -> tuple[int, int]:
    return (-season.growth, -season.position)


def _cold(season: WorldSeasonRow) -> tuple[int, int]:
    return (-season.temperature_shift, -season.position)


def _hot(season: WorldSeasonRow) -> tuple[int, int]:
    return (season.temperature_shift, -season.position)


def _war(season: WorldSeasonRow) -> tuple[int, int]:
    return (season.campaign, -season.position)


def _roads(season: WorldSeasonRow) -> tuple[int, int]:
    return (season.travel, -season.position)


SEASON_OF: dict[TraditionKind, SeasonKey] = {
    K.FESTIVAL: _plenty,
    K.HARVEST_RITE: _plenty,
    K.MARRIAGE_RITE: _plenty,
    K.COMING_OF_AGE: _plenty,
    K.FAST: _lean,
    K.MOURNING: _lean,
    K.ANCESTOR_FEAST: _cold,
    K.NIGHT_VIGIL: _cold,
    K.SIESTA: _hot,
    K.WAR_DANCE: _war,
    K.INITIATION: _war,
    K.PILGRIMAGE: _roads,
    K.OFFERING: _plenty,
}


def preferred_season(kind: TraditionKind, seasons: list[WorldSeasonRow]) -> int | None:
    key = SEASON_OF.get(kind)
    if key is None or len(seasons) < 2:
        return None
    return max(seasons, key=key).position


@dataclass
class RiteCalendar:
    seasons: dict[int, list[WorldSeasonRow]]
    calendars: dict[int, CalendarRow]
    kept_by: dict[int, int] = field(default_factory=dict)

    @classmethod
    async def load(cls, session: AsyncSession) -> "RiteCalendar":
        seasons: dict[int, list[WorldSeasonRow]] = {}
        for row in await session.scalars(select(WorldSeasonRow).order_by(WorldSeasonRow.world_id, WorldSeasonRow.position)):
            seasons.setdefault(row.world_id, []).append(row)
        calendars = {row.knowledge_entity_id: row for row in await session.scalars(select(CalendarRow))}
        kept_by: dict[int, int] = {}
        if calendars:
            statement = select(BondRow.source_node_id, BondRow.target_node_id).where(
                BondRow.kind == BondKind.KNOWS, BondRow.state == BondState.ACTIVE, BondRow.target_node_id.in_(list(calendars))
            )
            for knower, record in await session.execute(statement.order_by(BondRow.id)):
                kept_by.setdefault(knower, record)
        return cls(seasons=seasons, calendars=calendars, kept_by=kept_by)

    def season(self, world_id: int | None, position: int | None) -> WorldSeasonRow | None:
        if world_id is None or position is None:
            return None
        return next((season for season in self.seasons.get(world_id, []) if season.position == position), None)

    def bind(self, row: TraditionProfileRow, tradition: EntityRow, keeper: EntityRow) -> None:
        locked = set(row.locked)
        if SEASON_HELD not in locked and (row.season_position is None or self.season(tradition.world_id, row.season_position) is None):
            row.season_position = preferred_season(row.kind, self.seasons.get(tradition.world_id or 0, []))
        if CALENDAR_HELD not in locked and (row.calendar_entity_id is None or row.calendar_entity_id not in self.calendars):
            row.calendar_entity_id = self.kept_by.get(keeper.id)

    def keeping(self, ctx: TickContext, row: TraditionProfileRow, tradition: EntityRow, keeper: EntityRow) -> Keeping:
        table = ctx.rules.seasonal
        season = self.season(tradition.world_id, row.season_position)
        if season is None:
            return Keeping()
        fixed = row.calendar_entity_id is not None and row.calendar_entity_id in self.calendars
        drifted = not fixed and ctx.rng(f"tradition_drift.{tradition.id}.{keeper.id}").chance(table.drift_chance)
        if drifted:
            return Keeping(weight=table.off_season_pct / PERCENT, relief=0.0, in_season=False)
        relief = season.growth / PERCENT * table.plenty_relief_pct / PERCENT
        return Keeping(weight=table.in_season_pct / PERCENT, relief=relief, in_season=True)


def fast_season(seasons: list[WorldSeasonRow]) -> int | None:
    return preferred_season(K.FAST, seasons)


async def found_fast(ctx: TickContext, calendar: CalendarRow, notable: NotableYearRow, keepers: list[int]) -> TraditionProfileRow:
    seasons = list(await ctx.session.scalars(select(WorldSeasonRow).where(WorldSeasonRow.world_id == calendar.world_id).order_by(WorldSeasonRow.position)))
    tradition = await create_record(
        ctx,
        RecordSpec(
            name=f"The Fast of {notable.name}",
            entity_type=EntityType.TRADITION,
            stats=TraditionStats(spread=PERCENT // 5, rigidity=PERCENT // 3),
            body=f"Kept on the holy day that remembers {notable.name}, the year {notable.year}.",
            power=2,
            world_id=calendar.world_id,
            location_id=notable.region_entity_id,
        ),
    )
    row = await profile_of(ctx, tradition)
    row.kind = K.FAST
    row.cost = cost_for(ctx, K.FAST)
    row.notable_year_id = notable.id
    row.calendar_entity_id = calendar.knowledge_entity_id
    row.season_position = fast_season(seasons)
    row.origin_incident_id = notable.incident_id
    for keeper in sorted(set(keepers)):
        await connect(ctx.session, keeper, tradition.id, BondKind.CELEBRATES, ctx.epoch, description="on the holy day")
    return row


async def keepers_of(session: AsyncSession, record_id: int) -> list[int]:
    statement = select(BondRow.source_node_id).where(BondRow.kind == BondKind.KNOWS, BondRow.state == BondState.ACTIVE, BondRow.target_node_id == record_id)
    ids = sorted(set(await session.scalars(statement)))
    if not ids:
        return []
    rows = await session.scalars(
        select(EntityRow.id).where(EntityRow.id.in_(ids), EntityRow.status == EntityStatus.CANON, EntityRow.entity_type.in_(list(COMMUNITY_TYPES)))
    )
    return sorted(rows)


async def hallow_holy_days(ctx: TickContext, calendar: CalendarRow) -> int:
    founded = 0
    days: list[dict[str, Any]] = []
    keepers: list[int] | None = None
    for day in calendar.holy_days:
        entry = dict(day)
        notable_id = entry.get("notable_year_id")
        if "tradition_entity_id" not in entry and isinstance(notable_id, int):
            notable = await ctx.session.get(NotableYearRow, notable_id)
            if notable is not None:
                keepers = keepers if keepers is not None else await keepers_of(ctx.session, calendar.knowledge_entity_id)
                row = await found_fast(ctx, calendar, notable, keepers)
                entry["tradition_entity_id"] = row.tradition_entity_id
                entry.setdefault("season_position", row.season_position)
                founded += 1
        days.append(entry)
    if founded:
        calendar.holy_days = days
    return founded


async def backfill_holy_days(ctx: TickContext) -> int:
    if await ctx.session.get(AppliedFixupRow, HOLY_DAY_FIXUP) is not None:
        return 0
    founded = 0
    for calendar in list(await ctx.session.scalars(select(CalendarRow).order_by(CalendarRow.knowledge_entity_id))):
        founded += await hallow_holy_days(ctx, calendar)
    ctx.session.add(AppliedFixupRow(key=HOLY_DAY_FIXUP, result={"traditions": founded}))
    await ctx.session.flush()
    return founded


def long_days(rules_hours: int, world: WorldRow | None) -> bool:
    if world is None:
        return False
    return world.world_type in ENDLESS_DAY_WORLDS or (world.day_length_hours or 0) >= rules_hours


async def sleep_custom_kept(session: AsyncSession, community_id: int) -> bool:
    kept = select(BondRow.target_node_id).where(BondRow.source_node_id == community_id, BondRow.kind == BondKind.CELEBRATES, BondRow.state == BondState.ACTIVE)
    found = await session.scalar(
        select(TraditionProfileRow.tradition_entity_id)
        .where(TraditionProfileRow.tradition_entity_id.in_(kept), TraditionProfileRow.kind.in_(list(SLEEP_CUSTOMS)))
        .limit(1)
    )
    return found is not None


SLEEP_NAMES = {K.SIESTA: "The Midday Rest of {name}", K.NIGHT_VIGIL: "The Long Night Vigil of {name}"}
SLEEP_BODIES = {
    K.SIESTA: "Under a day of {hours} hours the work stops while the sun is high, and the folk sleep through the heat.",
    K.NIGHT_VIGIL: "Through a night of {hours} hours some keep watch by fire and lamp while the rest sleep in turns.",
}


async def found_sleep_customs(ctx: TickContext, atlas: RegionAtlas) -> int:
    table = ctx.rules.seasonal
    worlds = {row.id: row for row in await ctx.session.scalars(select(WorldRow))}
    grounds = {row.entity_id: row for row in await ctx.session.scalars(select(RegionEnvironmentRow))}
    founded = 0
    communities = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type.in_(list(COMMUNITY_TYPES)), EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    for community in list(communities):
        world = worlds.get(community.world_id or 0)
        if not long_days(table.long_day_hours, world) or await sleep_custom_kept(ctx.session, community.id):
            continue
        if not ctx.rng(f"sleep_custom.{community.id}").chance(table.sleep_custom_chance):
            continue
        region = atlas.top_region(community.id)
        ground = grounds.get(region) if region is not None else None
        kind = K.SIESTA if ground is not None and ground.temperature_band in WARM_BANDS else K.NIGHT_VIGIL
        hours = world.day_length_hours if world is not None and world.day_length_hours is not None else table.long_day_hours
        tradition = await create_record(
            ctx,
            RecordSpec(
                name=SLEEP_NAMES[kind].format(name=community.name),
                entity_type=EntityType.TRADITION,
                stats=TraditionStats(spread=PERCENT // 4, rigidity=PERCENT // 3),
                body=SLEEP_BODIES[kind].format(hours=hours),
                power=1,
                world_id=community.world_id,
                location_id=community.id,
            ),
        )
        row = await profile_of(ctx, tradition)
        row.kind = kind
        row.cost = cost_for(ctx, kind)
        await connect(ctx.session, community.id, tradition.id, BondKind.CELEBRATES, ctx.epoch, description="through the long day")
        founded += 1
    return founded
