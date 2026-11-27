from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from types import MappingProxyType

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.environment import WorldSeasonRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.made import MadeRealmRow
from aerona.domain.enums.records import ProcessClock
from aerona.domain.models.calendar import YearWindow, epoch_start_year
from aerona.domain.models.moment import Moment, latest
from aerona.engine.context import TickContext
from aerona.engine.environment.season_shape import position_at_fraction
from aerona.engine.recording.births import birth_moments, born_floor
from aerona.engine.recording.deaths import death_floor, ended_floor, mortal_floor
from aerona.rules.registry.records import RecordsRules

CALENDARS = "record_calendars"
DRAWS = "record_moment_draws"


@dataclass(frozen=True)
class Calendar:
    year_days: int | None
    seasons: int | None
    day_hours: int | None
    shares: tuple[int, ...] = ()

    def season_at(self, fraction: float) -> int | None:
        if not self.seasons:
            return None
        if len(self.shares) == self.seasons:
            return position_at_fraction(self.shares, fraction)
        return min(self.seasons - 1, int(min(max(fraction, 0.0), 1.0 - 1e-9) * self.seasons))

    def place(self, year: int, fraction: float) -> Moment:
        share = min(max(fraction, 0.0), 1.0 - 1e-9)
        season = self.season_at(share)
        if not self.year_days:
            return Moment(year, season)
        position = share * self.year_days
        day = int(position)
        hour = int((position - day) * self.day_hours) if self.day_hours else None
        return Moment(year, season, day, hour)

    def advance(self, moment: Moment, *, years: int = 0, days: int = 0, hours: int = 0) -> Moment:
        year, day, hour = moment.year + years, (moment.day or 0) + days, (moment.hour or 0) + hours
        if self.day_hours and hour >= self.day_hours:
            day, hour = day + hour // self.day_hours, hour % self.day_hours
        if self.year_days and day >= self.year_days:
            year, day = year + day // self.year_days, day % self.year_days
        if not self.year_days:
            return Moment(year, moment.season)
        season = self.season_at(day / self.year_days)
        return Moment(year, season, day, hour if self.day_hours else None)


NO_CALENDAR = Calendar(None, None, None)
STEP_UNITS: MappingProxyType[ProcessClock, tuple[int, int, int]] = total(
    ProcessClock,
    {
        ProcessClock.INSTANT: (0, 0, 1),
        ProcessClock.PHASE: (0, 0, 0),
        ProcessClock.MARCH: (0, 1, 0),
        ProcessClock.VOYAGE: (0, 1, 0),
        ProcessClock.COURSE: (0, 1, 0),
        ProcessClock.BUILDING: (0, 30, 0),
        ProcessClock.ROUNDS: (0, 0, 1),
        ProcessClock.SEASON: (0, 7, 0),
        ProcessClock.YEAR: (1, 0, 0),
        ProcessClock.LIFE: (1, 0, 0),
    },
)


SPREADS: MappingProxyType[ProcessClock, Callable[[RecordsRules], int]] = total(
    ProcessClock,
    {
        ProcessClock.INSTANT: lambda table: table.moment_spread_instant_pct,
        ProcessClock.PHASE: lambda table: table.moment_spread_phase_pct,
        ProcessClock.MARCH: lambda table: table.moment_spread_march_pct,
        ProcessClock.VOYAGE: lambda table: table.moment_spread_voyage_pct,
        ProcessClock.COURSE: lambda table: table.moment_spread_course_pct,
        ProcessClock.BUILDING: lambda table: table.moment_spread_building_pct,
        ProcessClock.ROUNDS: lambda table: table.moment_spread_rounds_pct,
        ProcessClock.SEASON: lambda table: table.moment_spread_season_pct,
        ProcessClock.YEAR: lambda table: table.moment_spread_year_pct,
        ProcessClock.LIFE: lambda table: table.moment_spread_life_pct,
    },
)


def spread_of(ctx: TickContext, clock: ProcessClock) -> int:
    return SPREADS[clock](ctx.rules.records)


async def calendar_of(session: AsyncSession, world_id: int | None) -> Calendar:
    if world_id is None:
        return NO_CALENDAR
    known: dict[int, Calendar] = session.sync_session.info.setdefault(CALENDARS, {})
    found = known.get(world_id)
    if found is None:
        row = (
            await session.execute(select(WorldRow.year_length_days, WorldRow.season_count, WorldRow.day_length_hours).where(WorldRow.id == world_id))
        ).first()
        shares = tuple(await session.scalars(select(WorldSeasonRow.share_pct).where(WorldSeasonRow.world_id == world_id).order_by(WorldSeasonRow.position)))
        found = known[world_id] = Calendar(row[0], row[1], row[2], shares) if row is not None else NO_CALENDAR
    return found


def epoch_span(ctx: TickContext) -> tuple[int, int]:
    years = ctx.rules.time.years_per_epoch
    window = ctx.environment.window or YearWindow(start=0, end=years)
    start = epoch_start_year(ctx.epoch, years) + window.start
    return start, max(1, window.end - window.start)


def stream_of(key: str, participants: Iterable[int]) -> str:
    return ".".join(["records", "moment", key, *(str(node) for node in sorted(set(participants)))])


def drawn_stream(ctx: TickContext, stream: str) -> str:
    drawn: dict[tuple[int, str], int] = ctx.session.sync_session.info.setdefault(DRAWS, {})
    count = drawn.get((ctx.epoch, stream), 0)
    drawn[(ctx.epoch, stream)] = count + 1
    return stream if count == 0 else f"{stream}.{count}"


async def moment_for(
    ctx: TickContext,
    clock: ProcessClock,
    *,
    key: str,
    participants: Iterable[int] = (),
    cause_moment: Moment | None = None,
    progress: float | None = None,
    world_id: int | None = None,
) -> Moment:
    participants = tuple(participants)
    start, span = epoch_span(ctx)
    calendar = await calendar_of(ctx.session, world_id)
    progress = progress if progress is not None else ctx.environment.progress
    if progress is not None:
        position = min(max(progress, 0.0), 1.0) * span
    elif clock is ProcessClock.PHASE and ctx.environment.step is not None:
        position = min(max(ctx.environment.step, 0.0), 1.0) * span
    else:
        position = ctx.environment.rng(drawn_stream(ctx, stream_of(key, participants))).random() * span * spread_of(ctx, clock) / PERCENT
    year = start + min(span - 1, int(position))
    moment = calendar.place(year, position - int(position))
    after_this = latest(cause_moment, await ended_floor(ctx.session, participants))
    if after_this is not None and moment.before(after_this) and after_this.year < start + span - 1:
        rest = start + span - after_this.year
        after = after_this.year + 1 + int(ctx.environment.rng(drawn_stream(ctx, f"{stream_of(key, participants)}.after")).random() * (rest - 1))
        moment = calendar.place(min(start + span - 1, after), position - int(position))
    for floor in (after_this, await born_floor(ctx.session, participants), await mortal_floor(ctx.session, participants)):
        if floor is not None and moment.before(floor):
            years, days, hours = STEP_UNITS[clock]
            moment = calendar.advance(floor, years=years, days=days, hours=hours if (years or days or hours) else 0).at_least(floor)
    return moment


async def next_after(ctx: TickContext, clock: ProcessClock, after: Moment, *, participants: Iterable[int] = (), world_id: int | None = None) -> Moment:
    calendar = await calendar_of(ctx.session, world_id)
    years, days, hours = STEP_UNITS[clock]
    moment = calendar.advance(after, years=years, days=days, hours=hours if (years or days or hours) else 1).at_least(after)
    present = tuple(participants)
    for floor in (await born_floor(ctx.session, present), await death_floor(ctx.session, present)):
        if floor is not None and moment.before(floor):
            moment = calendar.advance(floor, years=years, days=days, hours=hours if (years or days or hours) else 1).at_least(floor)
    return moment


async def step_moments(
    ctx: TickContext,
    start: Moment,
    clock: ProcessClock,
    count: int,
    *,
    world_id: int | None = None,
    days: Sequence[int] = (),
    hours: Sequence[int] = (),
    realm_id: int | None = None,
) -> list[Moment]:
    calendar = await calendar_of(ctx.session, world_id)
    ratio = await realm_ratio(ctx.session, realm_id)
    years, unit_days, unit_hours = STEP_UNITS[clock]
    found: list[Moment] = []
    current = start
    for index in range(count):
        if index:
            current = calendar.advance(
                current,
                years=years,
                days=to_main_time(days[index - 1] if index - 1 < len(days) else unit_days, ratio),
                hours=to_main_time(hours[index - 1] if index - 1 < len(hours) else unit_hours, ratio),
            )
        found.append(current)
    return found


async def incident_moment(session: AsyncSession, incident_id: int | None) -> Moment | None:
    if incident_id is None:
        return None
    row = (await session.execute(select(IncidentRow.year, IncidentRow.season, IncidentRow.day, IncidentRow.hour).where(IncidentRow.id == incident_id))).first()
    return Moment(row[0], row[1], row[2], row[3]) if row is not None and row[0] is not None else None


async def realm_ratio(session: AsyncSession, realm_id: int | None) -> int:
    if realm_id is None:
        return PERCENT
    found = await session.scalar(select(MadeRealmRow.time_ratio_pct).where(MadeRealmRow.dimension_id == realm_id))
    return int(found) if found else PERCENT


def to_main_time(amount: int, time_ratio_pct: int) -> int:
    return round(amount * PERCENT / max(1, time_ratio_pct))


async def told_no_earlier(session: AsyncSession, year: int, nodes: list[int | None]) -> int:
    known = [node for node in nodes if node is not None]
    if not known:
        return year
    first = (
        select(func.min(IncidentRow.year))
        .join(IncidentParticipantRow, IncidentParticipantRow.incident_id == IncidentRow.id)
        .where(IncidentParticipantRow.node_id.in_(known), IncidentRow.year.is_not(None))
        .group_by(IncidentParticipantRow.node_id)
    )
    years = [found for found in await session.scalars(first) if found is not None]
    born = [moment.year for moment in (await birth_moments(session, known)).values() if moment is not None]
    return max([year, *years, *born])
