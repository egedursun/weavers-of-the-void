from sqlalchemy import or_, select

from aerona.catalog.creature_anatomy import MONSTER_SIZES
from aerona.constants.units import PERCENT
from aerona.db.tables.anatomy import CreatureAnatomyRow
from aerona.db.tables.ecology import BeastProfileRow
from aerona.db.tables.economy import ResourceProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.routes import RouteRow
from aerona.db.write_guard import held
from aerona.domain.enums.ecology import AwakeningTrigger, BeastTemper, Habitat
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.models.entity_stats import BeastStats
from aerona.engine.context import TickContext
from aerona.engine.ecology.anatomy import beast_anatomy
from aerona.engine.ecology.beasts import lair_in, profile_beast
from aerona.engine.notes import note
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.records import RecordSpec, create_record


async def emerge_from_deep(ctx: TickContext, atlas: RegionAtlas) -> int:
    table = ctx.rules.monsters
    emerged = 0
    resources = await ctx.session.execute(
        select(ResourceProfileRow.resource_entity_id, ResourceProfileRow.reserve, ResourceProfileRow.initial_reserve)
        .where(ResourceProfileRow.initial_reserve > 0)
        .order_by(ResourceProfileRow.resource_entity_id)
    )
    for resource_id, reserve, initial in list(resources):
        if emerged >= table.emerge_cap or (initial - reserve) * PERCENT < table.emerge_depth_pct * initial:
            continue
        region_id = atlas.top_region(resource_id)
        region = await ctx.session.get(EntityRow, region_id) if region_id is not None else None
        if region is None or held(region.id) or not ctx.rng(f"emerge.{resource_id}.{ctx.epoch}").chance(table.emerge_pct):
            continue
        beast = await create_record(
            ctx,
            RecordSpec(
                name=f"The Thing beneath {region.name}",
                entity_type=EntityType.BEAST,
                stats=BeastStats(
                    hp=table.emerge_hp, danger=table.emerge_danger, strength=table.emerge_danger, agility=PERCENT // 2, terror=PERCENT // 4, renown=0
                ),
                body=f"Something of a kind of its own that climbed out when the mines beneath {region.name} were dug too deep.",
                power=table.emerge_power,
                world_id=region.world_id,
                location_id=region.id,
                subtype="monster of the deep",
            ),
        )
        row = await profile_beast(ctx, beast, None, size=ctx.rng(f"emerge_size.{resource_id}.{ctx.epoch}").pick(list(MONSTER_SIZES)))
        row.temper, row.woke_epoch = BeastTemper.HUNGRY, ctx.epoch
        anatomy = await beast_anatomy(ctx, beast, row, deep=True)
        anatomy.awakening = AwakeningTrigger.DEEP_MINING
        emerged += 1
        await note(ctx, f"{beast.name} climbed out of the deep mines of {region.name}.", key="monsters.emerged", ids=[beast.id, region.id])
    return emerged


async def roam_void(ctx: TickContext, atlas: RegionAtlas) -> int:
    table = ctx.rules.monsters
    roamed = 0
    beasts = await ctx.session.execute(
        select(EntityRow, BeastProfileRow)
        .join(BeastProfileRow, BeastProfileRow.beast_entity_id == EntityRow.id)
        .join(CreatureAnatomyRow, CreatureAnatomyRow.node_id == EntityRow.id)
        .where(CreatureAnatomyRow.habitat == Habitat.VOID, EntityRow.status == EntityStatus.CANON, BeastProfileRow.bound_to_node_id.is_(None))
        .order_by(EntityRow.id)
    )
    for beast, row in list(beasts):
        if beast.world_id is None or held(beast.id) or "lair_place_id" in row.locked:
            continue
        if not ctx.rng(f"void_roam.{beast.id}.{ctx.epoch}").chance(table.void_roam_pct):
            continue
        roads = list(
            await ctx.session.scalars(
                select(RouteRow)
                .where(RouteRow.active.is_(True), or_(RouteRow.world_a_id == beast.world_id, RouteRow.world_b_id == beast.world_id))
                .order_by(RouteRow.id)
            )
        )
        if not roads:
            continue
        road = ctx.rng(f"void_road.{beast.id}.{ctx.epoch}").pick(roads)
        target = road.world_b_id if road.world_a_id == beast.world_id else road.world_a_id
        regions = select(EntityRow).where(EntityRow.world_id == target, EntityRow.entity_type == EntityType.REGION, EntityRow.status == EntityStatus.CANON)
        lands = list(await ctx.session.scalars(regions.order_by(EntityRow.id)))
        if not lands:
            continue
        beast.world_id, beast.location_id = target, lands[0].id
        row.lair_place_id = await lair_in(ctx, lands[0].id)
        road.danger = clamp_int(road.danger + table.void_route_danger, 0, PERCENT)
        roamed += 1
        await note(ctx, f"{beast.name} crossed the road between worlds.", key="monsters.void_roamed", ids=[beast.id])
    return roamed
