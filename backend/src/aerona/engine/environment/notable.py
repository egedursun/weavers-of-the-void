from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import NotableYearRow
from aerona.domain.enums.entity import EngineKind, EntityStatus, EntityType
from aerona.domain.enums.environment import NotableYearKind
from aerona.domain.models.calendar import epoch_start_year
from aerona.engine.context import TickContext
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.stats import stat

BACKFILL_FIXUP = "environment.notable_years_backfill"
EVENT_YEARS: dict[EngineKind, tuple[NotableYearKind, str]] = {
    EngineKind.FAMINE: (NotableYearKind.HUNGER, "the Hungry Year in {place}"),
    EngineKind.PLAGUE: (NotableYearKind.PESTILENCE, "the Year of Pestilence in {place}"),
}


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
