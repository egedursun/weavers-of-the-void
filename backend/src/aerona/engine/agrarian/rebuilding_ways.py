from sqlalchemy import select

from aerona.catalog.rebuilding import REBUILD_CAUSES, REBUILD_PLANS
from aerona.db.tables.agrarian import PreparednessRow, ReconstructionRow
from aerona.db.tables.culture import HolderTechniqueRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.write_guard import held
from aerona.domain.enums.agrarian import RebuildPlan
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.models.entity_stats import StructureStats
from aerona.engine.context import TickContext
from aerona.engine.demography.care import shelter_displaced
from aerona.engine.interconnect.flows import FlowCategory, flowing
from aerona.engine.phases.ruins import abandon
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.queries import add_flag
from aerona.engine.primitives.records import RecordSpec, open_record
from aerona.engine.primitives.stats import set_stats, stat_or
from aerona.engine.recording.record import record

RUIN_POWER = 5


async def safer_site(ctx: TickContext, town: EntityRow) -> int | None:
    if town.location_id is None:
        return None
    atlas = await RegionAtlas.load(ctx.session)
    here = await ctx.session.get(RegionEnvironmentRow, town.location_id)
    best: tuple[int, int] | None = None
    for region_id in atlas.neighbours(town.location_id):
        ground = await ctx.session.get(RegionEnvironmentRow, region_id)
        if ground is None or held(region_id):
            continue
        height = ground.elevation_mean
        if best is None or height > best[0]:
            best = (height, region_id)
    if best is None:
        return None
    floor = here.elevation_mean if here is not None else 0
    return best[1] if best[0] >= floor else None


async def choose_way(ctx: TickContext, row: ReconstructionRow, town: EntityRow) -> None:
    if "plan" in row.locked or REBUILD_PLANS[row.plan].moves or not REBUILD_PLANS[row.plan].builds:
        return
    table = ctx.rules.rebuilding
    roll = ctx.rng(f"rebuild.way.{row.id}")
    if roll.chance(table.abandon_pct):
        row.plan = RebuildPlan.ABANDONED
        return
    if roll.chance(table.relocate_pct):
        site = await safer_site(ctx, town)
        if site is not None:
            row.plan = RebuildPlan.RELOCATED
            row.site_entity_id = site


async def leave_ruin(ctx: TickContext, town: EntityRow, region_id: int | None) -> EntityRow:
    ruin = await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            entity_type=EntityType.STRUCTURE,
            name=f"Old {town.name}",
            body=f"What {town.name} left standing when its people moved on.",
            stats=StructureStats(durability=20),
            power=RUIN_POWER,
            location_id=region_id,
            world_id=town.world_id,
            subtype="ruin",
        ),
    )
    await add_flag(ctx.session, ruin.id, EntityFlag.RUIN, ctx.epoch)
    return ruin


async def nearest_host(ctx: TickContext, town: EntityRow) -> EntityRow | None:
    atlas = await RegionAtlas.load(ctx.session)
    near = [town.location_id, *(atlas.neighbours(town.location_id) if town.location_id is not None else [])]
    found = await ctx.session.scalars(
        select(EntityRow)
        .where(
            EntityRow.entity_type == EntityType.SETTLEMENT,
            EntityRow.status == EntityStatus.CANON,
            EntityRow.location_id.in_([item for item in near if item is not None]),
            EntityRow.id != town.id,
        )
        .order_by(EntityRow.id)
    )
    return next((item for item in found if not held(item.id)), None)


async def relocate(ctx: TickContext, row: ReconstructionRow, town: EntityRow) -> None:
    site = row.site_entity_id
    if site is None or site == town.location_id:
        return
    ruin = await leave_ruin(ctx, town, town.location_id)
    town.location_id = site
    await record(
        ctx,
        "settlement.relocated",
        roles={IncidentRole.SUBJECT: town.id, IncidentRole.DESTINATION: site, IncidentRole.PRODUCT: ruin.id},
        facts={"cause": row.cause},
        place=site,
    )


async def abandon_town(ctx: TickContext, row: ReconstructionRow, town: EntityRow) -> None:
    people = stat_or(town, "population", 0)
    host = await nearest_host(ctx, town)
    sent = 0
    await abandon(ctx, town, tell=False)
    if host is not None and people > 0:
        with flowing(FlowCategory.MIGRATION):
            set_stats(host, population=stat_or(host, "population", 0) + people)
            set_stats(town, population=0)
        sent = await shelter_displaced(ctx, host, people)
    row.finished_epoch = ctx.epoch
    await record(
        ctx,
        "settlement.left_after_ruin",
        roles={IncidentRole.SUBJECT: town.id, IncidentRole.HOST: host.id if host is not None else None},
        facts={"cause": row.cause, "displaced": sent},
        place=town.id,
    )


async def learn(ctx: TickContext, row: ReconstructionRow, town: EntityRow) -> None:
    spec = REBUILD_CAUSES[row.cause]
    chance = int(getattr(ctx.rules.rebuilding, spec.chance))
    if not ctx.rng(f"rebuild.lesson.{row.id}").chance(chance):
        return
    work = await ctx.session.get(PreparednessRow, (town.id, spec.lesson))
    if work is None:
        ctx.session.add(PreparednessRow(settlement_entity_id=town.id, kind=spec.lesson, level=1, built_epoch=ctx.epoch, locked=[]))
    elif "level" not in work.locked:
        work.level += 1
    if spec.technique is not None and await ctx.session.get(HolderTechniqueRow, (town.id, spec.technique)) is None:
        ctx.session.add(HolderTechniqueRow(holder_entity_id=town.id, technique=spec.technique, since_epoch=ctx.epoch))
    await record(
        ctx,
        "settlement.lesson_learned",
        roles={IncidentRole.SUBJECT: town.id},
        facts={"cause": row.cause, "lesson": spec.lesson},
        place=town.id,
    )


async def rebuilt(ctx: TickContext, row: ReconstructionRow, town: EntityRow) -> None:
    if REBUILD_PLANS[row.plan].moves:
        await relocate(ctx, row, town)
    await learn(ctx, row, town)
    await record(ctx, "settlement.rebuilt", roles={IncidentRole.SUBJECT: town.id}, facts={"cause": row.cause}, place=town.id)
