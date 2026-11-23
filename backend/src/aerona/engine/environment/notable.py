from sqlalchemy import select

from aerona.catalog.life_traits import WAR_ENDING_TRAITS, having
from aerona.catalog.named_years import year_name
from aerona.constants.units import PERCENT
from aerona.db.tables.ages import IrregularSeasonRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.discovery import EraDeedRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import NotableYearRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.db.tables.warfare import WarRow
from aerona.db.write_guard import held
from aerona.domain.enums.ages import SeasonCause, SeasonSpellShape
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.discovery import EraDeed
from aerona.domain.enums.entity import EngineKind, EntityStatus, EntityType
from aerona.domain.enums.environment import NotableYearKind
from aerona.domain.enums.life_traits import WarEndingTrait
from aerona.domain.models.calendar import epoch_start_year
from aerona.engine.context import TickContext
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.stats import stat, stat_or

BACKFILL_FIXUP = "environment.notable_years_backfill"
EVENT_YEARS: dict[EngineKind, NotableYearKind] = {
    EngineKind.FAMINE: NotableYearKind.HUNGER,
    EngineKind.PLAGUE: NotableYearKind.PESTILENCE,
    **dict.fromkeys(
        (EngineKind.EARTHQUAKE, EngineKind.FLOOD, EngineKind.STORM, EngineKind.MAGIC_STORM, EngineKind.FIRE, EngineKind.ERUPTION), NotableYearKind.DISASTER
    ),
    **dict.fromkeys((EngineKind.COMET, EngineKind.ECLIPSE_PROPHECY, EngineKind.ECLIPSE_WATCH), NotableYearKind.OMEN),
}
FOUNDING_MAGNITUDE = 50
FOUNDED_KINDS = frozenset({EntityType.POLITY, EntityType.SETTLEMENT, EntityType.CULT})
SIGNED_ENDINGS = having(WAR_ENDING_TRAITS, WarEndingTrait.SIGNED_ENDINGS)
SPELL_YEARS: dict[SeasonCause, NotableYearKind] = {
    SeasonCause.IMPACT: NotableYearKind.DISASTER,
    SeasonCause.ERUPTION: NotableYearKind.DISASTER,
    SeasonCause.STELLAR: NotableYearKind.OMEN,
}


def year_in(ctx: TickContext, epoch: int, stream: str) -> int:
    years = ctx.rules.time.years_per_epoch
    return epoch_start_year(epoch, years) + ctx.rng(stream).die(years) - 1


async def remember_event_year(ctx: TickContext, event: EntityRow, atlas: RegionAtlas, *, epoch: int, incident_id: int | None = None) -> NotableYearRow | None:
    found = EVENT_YEARS.get(event.engine_kind) if event.engine_kind is not None else None
    if found is None:
        return None
    kind = found
    region_id = atlas.top_region(event.location_id or event.id)
    region = await ctx.session.get(EntityRow, region_id) if region_id is not None else None
    if held(event.id, region_id):
        return None
    place = region.name if region is not None else "the world"
    row = NotableYearRow(
        world_id=event.world_id,
        region_entity_id=region.id if region is not None else None,
        epoch=max(1, epoch),
        year=year_in(ctx, epoch, f"notable.{event.id}"),
        kind=kind,
        weather=None,
        name=year_name(kind, place),
        magnitude=clamp_int(stat(event, "severity") or 0, 0, PERCENT),
        incident_id=incident_id,
    )
    ctx.session.add(row)
    return row


async def place_year(ctx: TickContext, place_id: int | None, kind: NotableYearKind, atlas: RegionAtlas, magnitude: int = PERCENT // 2) -> bool:
    place = await ctx.session.get(EntityRow, place_id) if place_id is not None else None
    if place is None:
        return False
    region_id = atlas.top_region(place.id)
    known = await ctx.session.scalar(
        select(NotableYearRow.id).where(NotableYearRow.region_entity_id == region_id, NotableYearRow.epoch == ctx.epoch, NotableYearRow.kind == kind).limit(1)
    )
    region = await ctx.session.get(EntityRow, region_id) if region_id is not None else None
    if known is not None or region is None or held(region.id, place.id):
        return False
    ctx.session.add(
        NotableYearRow(
            world_id=place.world_id,
            region_entity_id=region.id,
            epoch=max(1, ctx.epoch),
            year=year_in(ctx, ctx.epoch, f"notable.{kind.value}.{region.id}"),
            kind=kind,
            weather=None,
            name=year_name(kind, region.name),
            magnitude=clamp_int(magnitude, 0, PERCENT),
            incident_id=None,
        )
    )
    return True


async def remember_years(ctx: TickContext) -> int:
    atlas = await RegionAtlas.load(ctx.session)
    made = 0
    events = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.entity_type == EntityType.EVENT, EntityRow.birth_epoch == ctx.epoch, EntityRow.engine_kind.in_(list(EVENT_YEARS)))
        .order_by(EntityRow.id)
    )
    for event in list(events):
        kind = EVENT_YEARS[event.engine_kind] if event.engine_kind is not None else NotableYearKind.DISASTER
        made += await place_year(ctx, event.location_id or event.id, kind, atlas, clamp_int(stat_or(event, "severity", PERCENT // 2), 0, PERCENT))
    for deed in list(await ctx.session.scalars(select(EraDeedRow).where(EraDeedRow.deed == EraDeed.FIRST_TECHNIQUE, EraDeedRow.epoch == ctx.epoch))):
        realm = await ctx.session.get(PolityProfileRow, deed.polity_entity_id)
        made += await place_year(ctx, realm.capital_entity_id if realm is not None else None, NotableYearKind.DISCOVERY, atlas)
    for bond in list(await ctx.session.scalars(select(BondRow).where(BondRow.kind == BondKind.TRADES_WITH, BondRow.epoch == ctx.epoch).order_by(BondRow.id))):
        first, second = await ctx.session.get(EntityRow, bond.source_node_id), await ctx.session.get(EntityRow, bond.target_node_id)
        if first is not None and second is not None and first.world_id != second.world_id:
            made += await place_year(ctx, first.id, NotableYearKind.CONTACT, atlas)
    made += await spell_years(ctx, atlas)
    made += await peace_years(ctx, atlas)
    made += await founding_years(ctx, atlas)
    await ctx.session.flush()
    return made


async def spell_years(ctx: TickContext, atlas: RegionAtlas) -> int:
    made = 0
    fresh = select(IrregularSeasonRow).where(IrregularSeasonRow.spell_started_epoch == ctx.epoch, IrregularSeasonRow.shape == SeasonSpellShape.SINGLE)
    for spell in list(await ctx.session.scalars(fresh.order_by(IrregularSeasonRow.id))):
        kind = SPELL_YEARS.get(spell.cause)
        if kind is None:
            continue
        place = spell.source_region_id or await ctx.session.scalar(
            select(EntityRow.id).where(EntityRow.world_id == spell.world_id, EntityRow.entity_type == EntityType.REGION).order_by(EntityRow.id).limit(1)
        )
        made += await place_year(ctx, place, kind, atlas, spell.severity)
    return made


async def peace_years(ctx: TickContext, atlas: RegionAtlas) -> int:
    turns = ctx.rules.named_years.epochs(ctx.rules.named_years.peace_war_years)
    ended = select(WarRow).where(WarRow.ended_epoch == ctx.epoch, WarRow.ended_epoch - WarRow.started_epoch >= turns, WarRow.ending.in_(sorted(SIGNED_ENDINGS)))
    made = 0
    for war in list(await ctx.session.scalars(ended.order_by(WarRow.id))):
        length = (war.ended_epoch or ctx.epoch) - war.started_epoch
        made += await place_year(ctx, war.event_entity_id, NotableYearKind.PEACE, atlas, min(PERCENT, length * PERCENT // max(1, turns * 2)))
    return made


async def founding_years(ctx: TickContext, atlas: RegionAtlas) -> int:
    born = select(EntityRow).where(EntityRow.birth_epoch == ctx.epoch, EntityRow.entity_type.in_(list(FOUNDED_KINDS)), EntityRow.status == EntityStatus.CANON)
    made = 0
    for founded in list(await ctx.session.scalars(born.order_by(EntityRow.id))):
        made += await place_year(ctx, founded.location_id or founded.id, NotableYearKind.FOUNDING, atlas, FOUNDING_MAGNITUDE)
    return made


async def backfill_notable_years(ctx: TickContext) -> int:
    if await ctx.session.get(AppliedFixupRow, BACKFILL_FIXUP) is not None:
        return 0
    atlas = await RegionAtlas.load(ctx.session)
    known = {(row.world_id, row.region_entity_id, row.epoch, row.kind) for row in await ctx.session.scalars(select(NotableYearRow))}
    events = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.entity_type == EntityType.EVENT, EntityRow.engine_kind.in_(list(EVENT_YEARS)), EntityRow.status != EntityStatus.REJECTED)
        .order_by(EntityRow.id)
    )
    made = 0
    for event in events:
        kind = EVENT_YEARS[event.engine_kind] if event.engine_kind is not None else None
        if (event.world_id, atlas.top_region(event.location_id or event.id), max(1, event.birth_epoch), kind) in known:
            continue
        if await remember_event_year(ctx, event, atlas, epoch=event.birth_epoch) is not None:
            made += 1
    ctx.session.add(AppliedFixupRow(key=BACKFILL_FIXUP, result={"years": made}))
    await ctx.session.flush()
    return made
