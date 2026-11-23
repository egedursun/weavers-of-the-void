from sqlalchemy import select

from aerona.catalog.catch import GEAR, GROUNDS
from aerona.catalog.movement import breathes_under_water
from aerona.constants.units import PERCENT
from aerona.db.tables.crafts import CatchGroundRow
from aerona.db.tables.demography import PeopleBiologyRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import DamageType, HarmCause
from aerona.domain.enums.crafts import CatchGround, CatchMedium
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.environment import CoastKind, RiverClass, ScarKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.body.customs import people_of
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.economy.stocks import goods_of, holdings
from aerona.engine.environment.book import add_scar
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.recording.record import record

WORKED_MEDIA = frozenset({CatchMedium.SHORE, CatchMedium.UNDER_WATER, CatchMedium.POND})
DIVING_COASTS = frozenset({CoastKind.REEF})


def stock_of(row: CatchGroundRow) -> int | None:
    return row.stock if GROUNDS[row.ground].medium in WORKED_MEDIA else None


async def open_ground(ctx: TickContext, source_id: int, region_id: int, ground: CatchGround) -> CatchGroundRow | None:
    if await ctx.session.get(CatchGroundRow, (source_id, region_id)) is not None or held(region_id):
        return None
    row = CatchGroundRow(
        source_entity_id=source_id, region_entity_id=region_id, ground=ground, gear=GROUNDS[ground].gear[0], first_stock=PERCENT, stock=PERCENT, locked=[]
    )
    ctx.session.add(row)
    await record(ctx, "catch.ground_opened", roles={IncidentRole.PLACE: region_id}, facts={"ground": ground, "gear": row.gear}, place=region_id)
    return row


async def seed_shores(ctx: TickContext, atlas: RegionAtlas) -> int:
    opened = 0
    for ground in list(
        await ctx.session.scalars(
            select(RegionEnvironmentRow).where(RegionEnvironmentRow.coast_kind != CoastKind.NONE).order_by(RegionEnvironmentRow.entity_id)
        )
    ):
        if not atlas.communities_in(ground.entity_id):
            continue
        opened += int(await open_ground(ctx, ground.entity_id, ground.entity_id, CatchGround.SHORE_GATHERING) is not None)
        if ground.coast_kind in DIVING_COASTS:
            beds = await ctx.session.get(CatchGroundRow, (ground.entity_id, ground.entity_id))
            if beds is not None and beds.ground is CatchGround.SHORE_GATHERING:
                town = next(iter(atlas.communities_in(ground.entity_id)))
                opened += int(await open_ground(ctx, town, ground.entity_id, CatchGround.DIVING) is not None)
    return opened


async def build_ponds(ctx: TickContext, atlas: RegionAtlas) -> int:
    built = 0
    towns = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    for town in list(towns):
        region_id = atlas.top_region(town.id)
        ground = await ctx.session.get(RegionEnvironmentRow, region_id) if region_id is not None else None
        if ground is None or ground.river_class is RiverClass.NONE or held(town.id):
            continue
        grain = (await holdings(ctx.session, town.id)).get(CommodityKind.GRAIN, 0)
        if grain <= ctx.rules.grounds.pond_feed or not ctx.rng(seed_of("ponds", town.id, ctx.epoch)).chance(ctx.rules.grounds.pond_build_pct):
            continue
        built += int(await open_ground(ctx, town.id, ground.entity_id, CatchGround.FISH_PONDS) is not None)
    return built


async def worker_town(ctx: TickContext, row: CatchGroundRow) -> int | None:
    if row.ground is CatchGround.FISH_PONDS:
        return row.source_entity_id
    return next(iter((await RegionAtlas.load(ctx.session)).communities_in(row.region_entity_id)), None)


async def work_shore(ctx: TickContext, row: CatchGroundRow, town: int) -> None:
    table = ctx.rules.grounds
    yielded = round_half_up(table.shore_rate * row.stock / PERCENT * GEAR[row.gear].rate(ctx.rules) / PERCENT)
    await goods_of(ctx.session, ctx.epoch).add(town, CommodityKind.FISH, yielded, GoodsFlow.EXTRACTION)
    row.last_catch = yielded
    worn = round_half_up(table.shore_depletion * row.effort / PERCENT)
    row.stock = clamp_int(row.stock - worn + table.ground_regrow, 0, PERCENT)


async def can_live_below(ctx: TickContext, town: int) -> bool:
    community = await ctx.session.get(EntityRow, town)
    people = await people_of(ctx.session, community) if community is not None else None
    biology = await ctx.session.get(PeopleBiologyRow, people.id) if people is not None else None
    return biology is not None and breathes_under_water(biology.body_plan)


async def work_beds(ctx: TickContext, row: CatchGroundRow, town: int) -> None:
    table = ctx.rules.grounds
    yielded = round_half_up(table.diving_rate * row.stock / PERCENT * GEAR[row.gear].rate(ctx.rules) / PERCENT)
    await goods_of(ctx.session, ctx.epoch).add(town, CommodityKind.LUXURIES, yielded, GoodsFlow.EXTRACTION)
    row.last_catch = yielded
    row.stock = clamp_int(row.stock - round_half_up(table.diving_depletion * row.effort / PERCENT) + table.ground_regrow, 0, PERCENT)
    if await can_live_below(ctx, town) or not ctx.rng(seed_of("diver", row.region_entity_id, ctx.epoch)).chance(table.diving_death_pct):
        return
    divers = [
        diver
        for diver in await ctx.session.scalars(
            select(EntityRow)
            .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, await present_among(ctx.session, [town]))
            .order_by(EntityRow.id)
        )
        if not held(diver.id)
    ]
    if not divers:
        return
    lost = ctx.rng(seed_of("diver.who", row.region_entity_id, ctx.epoch)).pick(divers)
    await apply_hits(ctx, lost, Harm(damage=PERCENT, cause=HarmCause.ACCIDENT, death_cause="drowned diving the beds below", damage_type=DamageType.ASPHYXIA))
    await record(ctx, "catch.diver_lost", roles={IncidentRole.VICTIM: lost.id, IncidentRole.PLACE: row.region_entity_id}, place=row.region_entity_id)


async def work_ponds(ctx: TickContext, row: CatchGroundRow, town: int) -> None:
    table = ctx.rules.grounds
    land = await ctx.session.get(RegionEnvironmentRow, row.region_entity_id)
    if land is not None and land.scars.get(ScarKind.FLOODED.value, 0) >= table.pond_flood_scar and row.stock > 0:
        row.stock = 0
        await record(ctx, "catch.ponds_ruined", roles={IncidentRole.SUBJECT: town, IncidentRole.PLACE: row.region_entity_id}, place=row.region_entity_id)
        return
    goods = goods_of(ctx.session, ctx.epoch)
    fed = await goods.take_units(town, CommodityKind.GRAIN, table.pond_feed, GoodsFlow.CONSUMPTION)
    share = fed / max(1, table.pond_feed)
    yielded = round_half_up(table.pond_yield * row.stock / PERCENT * share)
    await goods.add(town, CommodityKind.FISH, yielded, GoodsFlow.EXTRACTION)
    row.last_catch = yielded
    row.stock = clamp_int(row.stock + table.ground_regrow, 0, PERCENT)


async def harm_by_gear(ctx: TickContext, row: CatchGroundRow) -> None:
    spec = GEAR[row.gear]
    land = await ctx.session.get(RegionEnvironmentRow, row.region_entity_id)
    if land is None or held(land.entity_id) or row.collapsed:
        return
    if spec.harms_bed and "scar.eroded" not in land.locked:
        add_scar(land, ScarKind.ERODED, ctx.rules.grounds.trawl_bed_harm)
        await record(
            ctx,
            "catch.bed_harmed",
            roles={IncidentRole.PLACE: land.entity_id},
            facts={"gear": row.gear, "harm": ctx.rules.grounds.trawl_bed_harm},
            place=land.entity_id,
        )
    if spec.sickens and "disease_load" not in land.locked:
        land.disease_load = clamp_int(land.disease_load + ctx.rules.grounds.poison_sickness_pct, 0, PERCENT)
        await record(
            ctx,
            "catch.poisoned_catch",
            roles={IncidentRole.PLACE: land.entity_id},
            facts={"gear": row.gear, "sickness": ctx.rules.grounds.poison_sickness_pct},
            place=land.entity_id,
        )


WORKERS = {CatchGround.SHORE_GATHERING: work_shore, CatchGround.DIVING: work_beds, CatchGround.FISH_PONDS: work_ponds}


async def keep_worked_grounds(ctx: TickContext) -> int:
    atlas = await RegionAtlas.load(ctx.session)
    opened = await seed_shores(ctx, atlas) + await build_ponds(ctx, atlas)
    await ctx.session.flush()
    for row in list(await ctx.session.scalars(select(CatchGroundRow).order_by(CatchGroundRow.source_entity_id, CatchGroundRow.region_entity_id))):
        if held(row.region_entity_id) or held(row.source_entity_id):
            continue
        await harm_by_gear(ctx, row)
        work = WORKERS.get(row.ground)
        town = await worker_town(ctx, row) if work is not None else None
        if work is not None and town is not None and not held(town) and not row.collapsed and "stock" not in row.locked:
            await work(ctx, row, town)
    return opened
