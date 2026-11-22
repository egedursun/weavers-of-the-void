from collections.abc import Mapping
from dataclasses import dataclass

from sqlalchemy import ColumnElement, Table, case, inspect, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import set_committed_value

from aerona.catalog.season_positions import SEASON_POSITIONS, SeasonPosition
from aerona.db.base import Base
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.domain.enums.environment import SeasonDating, WorldLink
from aerona.engine.recording.moments import CALENDARS

Remap = Mapping[int, int | None]


@dataclass(frozen=True)
class Move:
    entry: SeasonPosition
    moved: dict[int, int | None]
    count: int
    year_days: int | None

    def of(self, row: object) -> int | None:
        day = getattr(row, "day", None) if self.entry.dating is SeasonDating.DAY else None
        if day is not None and self.year_days:
            return int(day * self.count // self.year_days)
        old: int | None = getattr(row, self.entry.column)
        return self.moved.get(old, old) if old is not None else None


def of_world(table: Table, entry: SeasonPosition, world_id: int) -> ColumnElement[bool]:
    column = table.c[entry.through]
    if entry.link is WorldLink.WORLD:
        return column == world_id
    if entry.link is WorldLink.ENTITY:
        return column.in_(select(EntityRow.id).where(EntityRow.world_id == world_id))
    return column.in_(select(IncidentRow.id).where(IncidentRow.world_id == world_id))


def settled(entry: SeasonPosition, mapping: Remap, count: int) -> dict[int, int | None]:
    last = max(0, count - 1)
    return {old: new if new is not None or entry.nullable else min(old, last) for old, new in mapping.items()}


def follow_loaded(session: AsyncSession, move: Move, keys: set[tuple[object, ...]]) -> None:
    for row in list(session.sync_session.identity_map.values()):
        table = getattr(type(row), "__table__", None)
        state = inspect(row, raiseerr=False)
        identity = state.identity if state is not None else None
        shown = isinstance(table, Table) and table.name == move.entry.table and identity is not None and tuple(identity) in keys
        if shown and getattr(row, move.entry.column) is not None:
            set_committed_value(row, move.entry.column, move.of(row))


async def remap_positions(session: AsyncSession, world_id: int, mapping: Remap, count: int) -> None:
    await session.flush()
    year_days = await session.scalar(select(WorldRow.year_length_days).where(WorldRow.id == world_id))
    for entry in SEASON_POSITIONS:
        table = Base.metadata.tables[entry.table]
        column = table.c[entry.column]
        move = Move(entry, settled(entry, mapping, count), count, year_days)
        positioned = case(move.moved, value=column, else_=column) if move.moved else column
        if entry.dating is SeasonDating.DAY and year_days:
            day = table.c.day
            positioned = case((day.is_not(None), day * count / year_days), else_=positioned)
        chosen = (of_world(table, entry, world_id), column.is_not(None))
        keys = {tuple(key) for key in await session.execute(select(*table.primary_key.columns).where(*chosen))}
        await session.execute(update(table).where(*chosen).values({entry.column: positioned}).execution_options(synchronize_session=False))
        follow_loaded(session, move, keys)
    session.sync_session.info.setdefault(CALENDARS, {}).pop(world_id, None)
