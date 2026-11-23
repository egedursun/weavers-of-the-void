from sqlalchemy import select

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.happenings import RiverShiftRow
from aerona.db.tables.polity import PolityTerritoryRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.agrarian import RebuildCause
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.environment import RiverClass, ScarKind
from aerona.domain.enums.happening import RiverShiftCause
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.structure import StructureKind
from aerona.engine.agrarian.ruin import ruin_towns_in
from aerona.engine.context import TickContext
from aerona.engine.environment.book import add_scar
from aerona.engine.environment.geomorph import shift_river
from aerona.engine.mind.memories import remember
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.recording.record import record


async def ruler_of(ctx: TickContext, region_id: int) -> int | None:
    return await ctx.session.scalar(
        select(PolityTerritoryRow.polity_entity_id)
        .where(PolityTerritoryRow.region_entity_id == region_id)
        .order_by(PolityTerritoryRow.control.desc(), PolityTerritoryRow.polity_entity_id)
        .limit(1)
    )


async def blame_works(ctx: TickContext, shift: RiverShiftRow) -> None:
    upstream, downstream = await ruler_of(ctx, shift.from_region_id), await ruler_of(ctx, shift.to_region_id)
    if upstream is None or downstream is None or upstream == downstream or held(downstream):
        return
    grievance = ctx.rules.rivers.works_grievance
    await remember(ctx.session, ctx.rules, holder_id=downstream, subject_id=upstream, kind=MemoryKind.HARMED_ME, magnitude=-grievance, epoch=ctx.epoch)


async def silt_out(ctx: TickContext, lands: dict[int, RegionEnvironmentRow], inflow: dict[int, int]) -> int:
    table = ctx.rules.rivers
    moved = 0
    for region_id, came in sorted(inflow.items()):
        land = lands.get(region_id)
        if land is None or land.river_class is RiverClass.NONE or came < table.silting_shift_load or held(region_id):
            continue
        if ctx.rng(f"silting.{region_id}.{ctx.epoch}").chance(table.silting_shift_pct):
            moved += int(await shift_river(ctx, region_id, None, RiverShiftCause.SILTING) is not None)
    return moved


async def works_move(ctx: TickContext, lands: dict[int, RegionEnvironmentRow]) -> int:
    atlas = await RegionAtlas.load(ctx.session)
    statement = (
        select(StructureProfileRow)
        .join(EntityRow, EntityRow.id == StructureProfileRow.structure_entity_id)
        .where(StructureProfileRow.kind.in_([StructureKind.CANAL, StructureKind.DAM]), EntityRow.status == EntityStatus.CANON)
        .order_by(StructureProfileRow.structure_entity_id)
    )
    moved = 0
    for works in await ctx.session.scalars(statement):
        fresh = works.kind is StructureKind.CANAL and works.built_epoch == ctx.epoch
        failed = works.kind is StructureKind.DAM and works.condition <= 0
        region_id = atlas.top_region(works.structure_entity_id)
        land = lands.get(region_id) if region_id is not None else None
        if not (fresh or failed) or land is None or land.river_class is RiverClass.NONE or held(land.entity_id):
            continue
        if ctx.rng(f"works_shift.{works.structure_entity_id}.{ctx.epoch}").chance(ctx.rules.rivers.works_shift_pct):
            shift = await shift_river(ctx, land.entity_id, None, RiverShiftCause.WORKS, event_id=works.structure_entity_id)
            if shift is not None:
                await blame_works(ctx, shift)
                moved += 1
    return moved


async def burst_slide_dams(ctx: TickContext, lands: dict[int, RegionEnvironmentRow]) -> int:
    burst = 0
    dams = select(RiverShiftRow).where(RiverShiftRow.cause == RiverShiftCause.LANDSLIDE, RiverShiftRow.epoch == ctx.epoch - 1).order_by(RiverShiftRow.id)
    for shift in await ctx.session.scalars(dams):
        land = lands.get(shift.to_region_id)
        if land is None or held(land.entity_id) or not ctx.rng(f"dam_burst.{shift.id}").chance(ctx.rules.rivers.slide_dam_burst_pct):
            continue
        add_scar(land, ScarKind.FLOODED, ctx.rules.rivers.burst_flood)
        await record(ctx, "river.dam_burst", roles={IncidentRole.PLACE: land.entity_id}, facts={"flood": ctx.rules.rivers.burst_flood}, place=land.entity_id)
        burst += 1
    return burst


async def slide_dam(ctx: TickContext, land: RegionEnvironmentRow) -> bool:
    if (
        land.river_class is RiverClass.NONE
        or held(land.entity_id)
        or not ctx.rng(f"slide_dam.{land.entity_id}.{ctx.epoch}").chance(ctx.rules.rivers.slide_dam_pct)
    ):
        return False
    shift = await shift_river(ctx, land.entity_id, None, RiverShiftCause.LANDSLIDE)
    if shift is None:
        return False
    await record(ctx, "river.dammed_by_slide", roles={IncidentRole.PLACE: land.entity_id}, facts={"river": shift.river_class}, place=land.entity_id)
    await ruin_towns_in(ctx, land.entity_id, RebuildCause.LANDSLIDE)
    return True


async def keep_courses(ctx: TickContext, lands: dict[int, RegionEnvironmentRow], inflow: dict[int, int]) -> int:
    return await silt_out(ctx, lands, inflow) + await works_move(ctx, lands) + await burst_slide_dams(ctx, lands)
