from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.calendar_slots import SLOTS
from aerona.core.total import total
from aerona.db.tables.affairs import CourtRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import SkyEventRow
from aerona.db.tables.culture import TraditionParticipationRow, TraditionProfileRow
from aerona.db.tables.ecology import SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import SeasonOnsetRow, WorldSeasonRow
from aerona.db.tables.gatherings import GatheringRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import CalendarSlot, SlotOpening
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.environment import SeasonOnset, SeasonWarmth
from aerona.domain.enums.gathering import GatheringKind
from aerona.engine.body.customs import people_id_of
from aerona.engine.collective.dating import known_calendar
from aerona.engine.context import TickContext
from aerona.engine.environment.season_shape import season_of_warmth, season_phase, wettest
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.recording.moments import epoch_span

CLOSED = total(
    SlotOpening,
    {
        SlotOpening.WARMING_GROWTH: "no warming season of that world grows enough",
        SlotOpening.AFTER_GREENEST: "the season after the greenest does not grow enough",
        SlotOpening.DEAD_OF_WINTER: "no season of that world is cold and barren enough",
        SlotOpening.HEIGHT_OF_SUMMER: "the warmest season of that world is not warm enough",
        SlotOpening.WAR_SEASON: "no season of that world is fit for war",
        SlotOpening.HOLY: "no sign shows over that world this epoch and no calendar kept there marks holy days",
        SlotOpening.YEAR: "that world has no year to begin",
        SlotOpening.REMEMBERED: "the custom names no remembered year or death of its people",
        SlotOpening.FAIR: "no market or fair is held there, or no season is easy enough to travel to one",
        SlotOpening.WILD_PLENTY: "the wild game, fish and plants of that land are too few",
        SlotOpening.RAINS_COME: "the wettest season failed this epoch, or that world has no wet season",
        SlotOpening.COUNCIL: "no council, court or assembly sits for that people",
        SlotOpening.DUES: "no dues are gathered there",
        SlotOpening.SACRED_ROAD: "no pilgrimage goes out from there and no season is easy enough to travel",
    },
)


@dataclass(frozen=True)
class SlotState:
    open: bool
    reason: str | None


@dataclass(frozen=True)
class SlotScene:
    world_id: int | None
    holder_id: int | None
    seasons: list[WorldSeasonRow]
    tradition: TraditionProfileRow | None


Opener = Callable[[TickContext, SlotScene], Awaitable[bool]]


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


async def region_of_holder(ctx: TickContext, holder_id: int | None) -> int | None:
    return (await RegionAtlas.load(ctx.session)).top_region(holder_id) if holder_id is not None else None


async def warming_growth(ctx: TickContext, scene: SlotScene) -> bool:
    phases = season_phase(scene.seasons)
    return any(phases[season.position].warmth is SeasonWarmth.WARMING and season.growth >= ctx.rules.traditions.season_growth for season in scene.seasons)


async def after_greenest(ctx: TickContext, scene: SlotScene) -> bool:
    if not scene.seasons:
        return False
    greenest = max(scene.seasons, key=lambda season: (season.growth, -season.position))
    after = next((season for season in scene.seasons if season.position == (greenest.position + 1) % len(scene.seasons)), greenest)
    return after.growth >= ctx.rules.traditions.season_growth


async def dead_of_winter(ctx: TickContext, scene: SlotScene) -> bool:
    table = ctx.rules.traditions
    coldest = season_of_warmth(scene.seasons, SeasonWarmth.COLDEST)
    return coldest is not None and coldest.temperature_shift <= -table.midwinter_cold and coldest.growth <= table.dead_growth


async def height_of_summer(ctx: TickContext, scene: SlotScene) -> bool:
    warmest = season_of_warmth(scene.seasons, SeasonWarmth.WARMEST)
    return warmest is not None and warmest.temperature_shift >= ctx.rules.traditions.midsummer_warm


async def war_season(ctx: TickContext, scene: SlotScene) -> bool:
    return any(season.campaign >= ctx.rules.traditions.season_campaign for season in scene.seasons)


async def holy(ctx: TickContext, scene: SlotScene) -> bool:
    return await sky_over(ctx, scene.world_id) or await keeps_holy_days(ctx, scene.holder_id)


async def year(ctx: TickContext, scene: SlotScene) -> bool:
    return scene.world_id is not None and bool(scene.seasons)


async def remembered(ctx: TickContext, scene: SlotScene) -> bool:
    return scene.tradition is not None and (scene.tradition.notable_year_id is not None or scene.tradition.origin_entity_id is not None)


async def fair(ctx: TickContext, scene: SlotScene) -> bool:
    if not any(season.travel >= ctx.rules.traditions.market_travel for season in scene.seasons) or scene.holder_id is None:
        return False
    region_id = await region_of_holder(ctx, scene.holder_id)
    places = [place for place in (scene.holder_id, region_id) if place is not None]
    found = await ctx.session.scalar(
        select(GatheringRow.id)
        .where(GatheringRow.kind == GatheringKind.FAIR, (GatheringRow.place_entity_id.in_(places)) | (GatheringRow.host_node_id.in_(places)))
        .limit(1)
    )
    return found is not None


async def wild_plenty(ctx: TickContext, scene: SlotScene) -> bool:
    region_id = await region_of_holder(ctx, scene.holder_id)
    if region_id is None:
        return False
    best = await ctx.session.scalar(select(func.max(SpeciesRangeRow.abundance)).where(SpeciesRangeRow.region_entity_id == region_id))
    return int(best or 0) >= ctx.rules.traditions.wild_stock_min


async def rains_come(ctx: TickContext, scene: SlotScene) -> bool:
    wet = wettest(scene.seasons)
    if wet is None or wet.rain_shift <= 0 or scene.world_id is None:
        return False
    start, span = epoch_span(ctx)
    failed = await ctx.session.scalar(
        select(SeasonOnsetRow.id)
        .where(
            SeasonOnsetRow.world_id == scene.world_id,
            SeasonOnsetRow.season_position == wet.position,
            SeasonOnsetRow.onset == SeasonOnset.FAILED,
            SeasonOnsetRow.year.between(start, start + span),
        )
        .limit(1)
    )
    return failed is None


async def council(ctx: TickContext, scene: SlotScene) -> bool:
    if scene.holder_id is None:
        return False
    people = await people_id_of(ctx.session, await ctx.session.get(EntityRow, scene.holder_id)) if scene.holder_id is not None else None
    sits = await ctx.session.scalar(
        select(GatheringRow.id)
        .where(GatheringRow.kind == GatheringKind.COUNCIL, GatheringRow.host_node_id.in_([scene.holder_id, *([people] if people else [])]))
        .limit(1)
    )
    court = await ctx.session.scalar(
        select(CourtRow.polity_entity_id).where(CourtRow.polity_entity_id.in_([scene.holder_id, *([people] if people else [])])).limit(1)
    )
    return sits is not None or court is not None


async def dues(ctx: TickContext, scene: SlotScene) -> bool:
    town = await ctx.session.get(SettlementProfileRow, scene.holder_id) if scene.holder_id is not None else None
    return town is not None and town.tax_rate > 0


async def sacred_road(ctx: TickContext, scene: SlotScene) -> bool:
    if scene.holder_id is None or not any(season.travel >= ctx.rules.traditions.market_travel for season in scene.seasons):
        return False
    found = await ctx.session.scalar(
        select(GatheringRow.id).where(GatheringRow.kind == GatheringKind.PILGRIMAGE, GatheringRow.host_node_id == scene.holder_id).limit(1)
    )
    return found is not None or await keeps_holy_days(ctx, scene.holder_id)


OPENERS: dict[SlotOpening, Opener] = dict(
    total(
        SlotOpening,
        {
            SlotOpening.WARMING_GROWTH: warming_growth,
            SlotOpening.AFTER_GREENEST: after_greenest,
            SlotOpening.DEAD_OF_WINTER: dead_of_winter,
            SlotOpening.HEIGHT_OF_SUMMER: height_of_summer,
            SlotOpening.WAR_SEASON: war_season,
            SlotOpening.HOLY: holy,
            SlotOpening.YEAR: year,
            SlotOpening.REMEMBERED: remembered,
            SlotOpening.FAIR: fair,
            SlotOpening.WILD_PLENTY: wild_plenty,
            SlotOpening.RAINS_COME: rains_come,
            SlotOpening.COUNCIL: council,
            SlotOpening.DUES: dues,
            SlotOpening.SACRED_ROAD: sacred_road,
        },
    )
)


async def slot_open(
    ctx: TickContext, world_id: int | None, slot: CalendarSlot, holder_id: int | None, tradition: TraditionProfileRow | None = None
) -> SlotState:
    opening = SLOTS[slot].opening
    seasons = list(await ctx.session.scalars(select(WorldSeasonRow).where(WorldSeasonRow.world_id == world_id).order_by(WorldSeasonRow.position)))
    if await OPENERS[opening](ctx, SlotScene(world_id, holder_id, seasons, tradition)):
        return SlotState(True, None)
    return SlotState(False, CLOSED[opening])


async def festivals_of(session: AsyncSession, people_id: int) -> list[tuple[EntityRow, TraditionProfileRow]]:
    kept = select(TraditionParticipationRow.tradition_entity_id).where(TraditionParticipationRow.community_entity_id == people_id)
    celebrated = select(BondRow.target_node_id).where(
        BondRow.source_node_id == people_id, BondRow.kind == BondKind.CELEBRATES, BondRow.state == BondState.ACTIVE
    )
    rows = await session.execute(
        select(EntityRow, TraditionProfileRow)
        .join(TraditionProfileRow, TraditionProfileRow.tradition_entity_id == EntityRow.id)
        .where(EntityRow.status == EntityStatus.CANON, or_(EntityRow.id.in_(kept), EntityRow.id.in_(celebrated)))
        .order_by(EntityRow.name, EntityRow.id)
    )
    return [(entity, profile) for entity, profile in rows]
