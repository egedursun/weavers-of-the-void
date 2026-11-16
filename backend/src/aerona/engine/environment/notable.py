from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.discovery import EraDeedRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import NotableYearRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.discovery import EraDeed
from aerona.domain.enums.entity import EngineKind, EntityStatus, EntityType
from aerona.domain.enums.environment import NotableYearKind
from aerona.domain.models.calendar import epoch_start_year
from aerona.engine.context import TickContext
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.stats import stat

BACKFILL_FIXUP = "environment.notable_years_backfill"
DISASTER_YEAR = (NotableYearKind.DISASTER, "the Year of Ruin in {place}")
OMEN_YEAR = (NotableYearKind.OMEN, "the Year of the Sign over {place}")
EVENT_YEARS: dict[EngineKind, tuple[NotableYearKind, str]] = {
    EngineKind.FAMINE: (NotableYearKind.HUNGER, "the Hungry Year in {place}"),
    EngineKind.PLAGUE: (NotableYearKind.PESTILENCE, "the Year of Pestilence in {place}"),
    **dict.fromkeys((EngineKind.EARTHQUAKE, EngineKind.FLOOD, EngineKind.STORM, EngineKind.MAGIC_STORM, EngineKind.FIRE, EngineKind.ERUPTION), DISASTER_YEAR),
    **dict.fromkeys((EngineKind.COMET, EngineKind.ECLIPSE_PROPHECY, EngineKind.ECLIPSE_WATCH), OMEN_YEAR),
}
DISCOVERY_YEAR = "the Year of Finding in {place}"
CONTACT_YEAR = "the Year of Meeting in {place}"


def year_in(ctx: TickContext, epoch: int, stream: str) -> int:
    years = ctx.rules.time.years_per_epoch
    return epoch_start_year(epoch, years) + ctx.rng(stream).die(years) - 1


async def remember_event_year(ctx: TickContext, event: EntityRow, atlas: RegionAtlas, *, epoch: int, incident_id: int | None = None) -> NotableYearRow | None:
    found = EVENT_YEARS.get(event.engine_kind) if event.engine_kind is not None else None
    if found is None:
        return None
    kind, template = found
    region_id = atlas.top_region(event.location_id or event.id)
    region = await ctx.session.get(EntityRow, region_id) if region_id is not None else None
    place = region.name if region is not None else "the world"
    row = NotableYearRow(
        world_id=event.world_id,
        region_entity_id=region.id if region is not None else None,
        epoch=max(1, epoch),
        year=year_in(ctx, epoch, f"notable.{event.id}"),
        kind=kind,
        weather=None,
        name=template.format(place=place),
        magnitude=clamp_int(stat(event, "severity") or 0, 0, PERCENT),
        incident_id=incident_id,
    )
    ctx.session.add(row)
    return row


async def place_year(ctx: TickContext, place_id: int | None, kind: NotableYearKind, template: str, atlas: RegionAtlas) -> bool:
    place = await ctx.session.get(EntityRow, place_id) if place_id is not None else None
    if place is None:
        return False
    region_id = atlas.top_region(place.id)
    known = await ctx.session.scalar(
        select(NotableYearRow.id).where(NotableYearRow.region_entity_id == region_id, NotableYearRow.epoch == ctx.epoch, NotableYearRow.kind == kind).limit(1)
    )
    region = await ctx.session.get(EntityRow, region_id) if region_id is not None else None
    if known is not None or region is None:
        return False
    ctx.session.add(
        NotableYearRow(
            world_id=place.world_id,
            region_entity_id=region.id,
            epoch=max(1, ctx.epoch),
            year=year_in(ctx, ctx.epoch, f"notable.{kind.value}.{region.id}"),
            kind=kind,
            weather=None,
            name=template.format(place=region.name),
            magnitude=PERCENT // 2,
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
        kind, template = EVENT_YEARS[event.engine_kind] if event.engine_kind is not None else DISASTER_YEAR
        made += await place_year(ctx, event.location_id or event.id, kind, template, atlas)
    for deed in list(await ctx.session.scalars(select(EraDeedRow).where(EraDeedRow.deed == EraDeed.FIRST_TECHNIQUE, EraDeedRow.epoch == ctx.epoch))):
        realm = await ctx.session.get(PolityProfileRow, deed.polity_entity_id)
        made += await place_year(ctx, realm.capital_entity_id if realm is not None else None, NotableYearKind.DISCOVERY, DISCOVERY_YEAR, atlas)
    for bond in list(await ctx.session.scalars(select(BondRow).where(BondRow.kind == BondKind.TRADES_WITH, BondRow.epoch == ctx.epoch).order_by(BondRow.id))):
        first, second = await ctx.session.get(EntityRow, bond.source_node_id), await ctx.session.get(EntityRow, bond.target_node_id)
        if first is not None and second is not None and first.world_id != second.world_id:
            made += await place_year(ctx, first.id, NotableYearKind.CONTACT, CONTACT_YEAR, atlas)
    await ctx.session.flush()
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
        kind = EVENT_YEARS[event.engine_kind][0] if event.engine_kind is not None else None
        if (event.world_id, atlas.top_region(event.location_id or event.id), max(1, event.birth_epoch), kind) in known:
            continue
        if await remember_event_year(ctx, event, atlas, epoch=event.birth_epoch) is not None:
            made += 1
    ctx.session.add(AppliedFixupRow(key=BACKFILL_FIXUP, result={"years": made}))
    await ctx.session.flush()
    return made
