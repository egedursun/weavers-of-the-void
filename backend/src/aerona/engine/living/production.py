from collections import defaultdict

from sqlalchemy import select

from aerona.catalog.methods import METHODS
from aerona.constants.units import PERCENT
from aerona.db.tables.agrarian import PerennialRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.industry import CommunityMethodRow
from aerona.db.tables.living import LivingLineRow, LivingProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.industry import MethodKind, ProcessKind
from aerona.domain.enums.living import LineTrait
from aerona.engine.context import TickContext
from aerona.engine.living.traits import eased, traits_of
from aerona.engine.notes import note
from aerona.engine.primitives.numbers import clamp_percent

LIVING_METHODS = frozenset({MethodKind.CULTURED_CROPS, MethodKind.GROWN_TIMBER, MethodKind.SPUN_FIBRE, MethodKind.VAT_CULTURE, MethodKind.BIOREACTOR})


def plain_method(process: ProcessKind) -> MethodKind | None:
    return next((spec.kind for spec in METHODS.values() if spec.process is process and spec.technique is None and spec.kind not in LIVING_METHODS), None)


async def works_sick(ctx: TickContext, community_id: int) -> bool:
    floor = ctx.rules.living_production.sick_works_pct
    healths = list(
        await ctx.session.scalars(
            select(LivingProfileRow.health)
            .join(EntityRow, EntityRow.id == LivingProfileRow.thing_node_id)
            .where(EntityRow.location_id == community_id, EntityRow.entity_type == EntityType.STRUCTURE, EntityRow.status == EntityStatus.CANON)
        )
    )
    return bool(healths) and max(healths) < floor


async def keep_living_works(ctx: TickContext) -> int:
    lapsed = 0
    rows = await ctx.session.scalars(select(CommunityMethodRow).where(CommunityMethodRow.method.in_(list(LIVING_METHODS))).order_by(CommunityMethodRow.id))
    for row in list(rows):
        if held(row.community_node_id) or "method" in row.locked or not await works_sick(ctx, row.community_node_id):
            continue
        fallback = plain_method(row.process)
        if fallback is None:
            continue
        old = row.method
        row.method, row.adopted_epoch = fallback, ctx.epoch
        lapsed += 1
        town = await ctx.session.get(EntityRow, row.community_node_id)
        await note(
            ctx,
            f"The living works of {town.name if town else 'a town'} sickened; {old.value.replace('_', ' ')} gave way to the older way.",
            key="living.works_lapsed",
            ids=[row.community_node_id],
        )
    return lapsed


async def blight_monocultures(ctx: TickContext) -> int:
    table = ctx.rules.living
    area: dict[int, int] = defaultdict(int)
    by_line: dict[tuple[int, int], list[PerennialRow]] = defaultdict(list)
    for row in await ctx.session.scalars(select(PerennialRow).order_by(PerennialRow.id)):
        area[row.region_entity_id] += row.area
        if row.line_id is not None:
            by_line[(row.region_entity_id, row.line_id)].append(row)
    struck = 0
    for (region_id, line_id), plantings in sorted(by_line.items()):
        share = sum(row.area for row in plantings) * PERCENT // max(1, area[region_id])
        if share < table.monoculture_share or held(region_id):
            continue
        if not ctx.rng(f"living.blight.{region_id}.{line_id}.{ctx.epoch}").chance(table.blight_chance):
            continue
        harm = eased(table.blight_harm, (await traits_of(ctx.session, line_id)).get(LineTrait.DISEASE_RESISTANCE, 0))
        for row in plantings:
            if "condition" not in row.locked:
                row.condition = clamp_percent(row.condition - harm)
        line = await ctx.session.get(LivingLineRow, line_id)
        region = await ctx.session.get(EntityRow, region_id)
        await note(
            ctx,
            f"A blight struck {line.name if line else 'a line'} across {region.name if region else 'a land'}, where nothing else was grown.",
            key="living.blight",
            ids=[region_id],
        )
        struck += 1
    return struck
