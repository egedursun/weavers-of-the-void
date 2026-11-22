from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.calendar_slots import SLOTS
from aerona.db.tables.celestial import SkyEventRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import WorldSeasonRow
from aerona.domain.enums.culture import CalendarSlot, SlotOpening
from aerona.engine.body.customs import people_id_of
from aerona.engine.collective.dating import known_calendar
from aerona.engine.context import TickContext

CLOSED = {
    SlotOpening.GROWING: "no season of that world grows enough",
    SlotOpening.DEAD_OF_WINTER: "no season of that world is cold and barren enough",
    SlotOpening.WAR_SEASON: "no season of that world is fit for war",
    SlotOpening.HOLY: "no sign shows over that world this epoch and no calendar kept there marks holy days",
}


@dataclass(frozen=True)
class SlotState:
    open: bool
    reason: str | None


async def keeps_holy_days(ctx: TickContext, holder_id: int | None) -> bool:
    holder = await ctx.session.get(EntityRow, holder_id) if holder_id is not None else None
    if holder is None:
        return False
    keepers = {holder.id, *([people] if (people := await people_id_of(ctx.session, holder)) is not None else [])}
    for keeper in sorted(keepers):
        calendar = await known_calendar(ctx, keeper)
        if calendar is not None and calendar.holy_days:
            return True
    return False


async def sky_over(ctx: TickContext, world_id: int | None) -> bool:
    found = await ctx.session.scalar(
        select(SkyEventRow.id).where((SkyEventRow.world_id == world_id) | SkyEventRow.world_id.is_(None), SkyEventRow.epoch == ctx.epoch).limit(1)
    )
    return found is not None


async def opens(ctx: TickContext, world_id: int | None, opening: SlotOpening, holder_id: int | None) -> bool:
    table = ctx.rules.traditions
    if opening is SlotOpening.HOLY:
        return await sky_over(ctx, world_id) or await keeps_holy_days(ctx, holder_id)
    seasons = list(await ctx.session.scalars(select(WorldSeasonRow).where(WorldSeasonRow.world_id == world_id).order_by(WorldSeasonRow.position)))
    if opening is SlotOpening.GROWING:
        return any(season.growth >= table.season_growth for season in seasons)
    if opening is SlotOpening.DEAD_OF_WINTER:
        coldest = min(seasons, key=lambda season: (season.temperature_shift, season.position), default=None)
        return coldest is not None and coldest.temperature_shift <= -table.midwinter_cold and coldest.growth <= table.dead_growth
    return any(season.campaign >= table.season_campaign for season in seasons)


async def slot_open(ctx: TickContext, world_id: int | None, slot: CalendarSlot, holder_id: int | None) -> SlotState:
    opening = SLOTS[slot].opening
    if await opens(ctx, world_id, opening, holder_id):
        return SlotState(True, None)
    return SlotState(False, CLOSED[opening])
