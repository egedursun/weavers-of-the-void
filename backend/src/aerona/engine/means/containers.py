from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.means import CONTAINERS
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.means import ContainerStockRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.routes import RouteRow
from aerona.db.write_guard import held
from aerona.domain.enums.economy import GoodsFlow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.means import ContainerKind
from aerona.domain.enums.mind import SkillKind
from aerona.engine.context import TickContext
from aerona.engine.cosmos.routes import reveal_hidden_route
from aerona.engine.economy.stocks import goods_of
from aerona.engine.primitives.folk import present_in
from aerona.engine.primitives.numbers import round_half_up

MAKER_SKILLS = frozenset(spec.maker for spec in CONTAINERS.values())


@dataclass
class ContainerTally:
    made: int = 0
    broken: int = 0


async def makers_in(ctx: TickContext, town: EntityRow) -> dict[SkillKind, int]:
    rows = await ctx.session.execute(
        select(SkillRow.skill, SkillRow.level)
        .join(EntityRow, EntityRow.id == SkillRow.holder_node_id)
        .where(
            await present_in(ctx.session, town),
            EntityRow.entity_type == EntityType.MORTAL,
            EntityRow.status == EntityStatus.CANON,
            SkillRow.skill.in_(sorted(MAKER_SKILLS)),
            SkillRow.level >= ctx.rules.containers.skill_floor,
        )
    )
    found: dict[SkillKind, int] = {}
    for skill, level in rows:
        found[skill] = found.get(skill, 0) + int(level)
    return found


async def stock_of(ctx: TickContext, town_id: int, kind: ContainerKind) -> ContainerStockRow:
    row = await ctx.session.get(ContainerStockRow, (town_id, kind))
    if row is None:
        row = ContainerStockRow(community_entity_id=town_id, kind=kind, count=0, broken=0, locked=[])
        ctx.session.add(row)
    return row


async def make_containers(ctx: TickContext, town: EntityRow, tally: ContainerTally) -> None:
    table = ctx.rules.containers
    ledger = goods_of(ctx.session, ctx.epoch)
    for skill, levels in sorted((await makers_in(ctx, town)).items()):
        kinds = sorted(kind for kind, spec in CONTAINERS.items() if spec.maker is skill)
        share = levels * table.made_per_skill // max(1, len(kinds))
        for kind in kinds:
            row = await stock_of(ctx, town.id, kind)
            if "count" in row.locked or share <= 0:
                continue
            made = await ledger.take_units(town.id, CONTAINERS[kind].raw, share, GoodsFlow.PRODUCTION)
            row.count += made
            tally.made += made


async def break_containers(ctx: TickContext, town: EntityRow, tally: ContainerTally) -> None:
    table = ctx.rules.containers
    for row in list(await ctx.session.scalars(select(ContainerStockRow).where(ContainerStockRow.community_entity_id == town.id))):
        if "count" in row.locked or row.count <= 0:
            continue
        lost = min(row.count, round_half_up(row.count * CONTAINERS[row.kind].breakage * table.breakage_pct / PERCENT / PERCENT))
        row.count -= lost
        if "broken" not in row.locked:
            row.broken += lost
        tally.broken += lost


async def capacity_held(ctx: TickContext, town_id: int) -> int:
    rows = await ctx.session.scalars(select(ContainerStockRow).where(ContainerStockRow.community_entity_id == town_id))
    return sum(row.count * CONTAINERS[row.kind].capacity for row in rows) * ctx.rules.containers.per_capacity


async def packed_capacity(ctx: TickContext, ends: tuple[int, int], capacity: int) -> int:
    held_capacity = max([await capacity_held(ctx, end) for end in ends])
    if held_capacity >= capacity:
        return capacity
    short = round_half_up(capacity * ctx.rules.containers.shortage_pct / PERCENT)
    return max(short, min(capacity, held_capacity))


async def sealed_share(ctx: TickContext, town_id: int, units: int) -> float:
    rows = await ctx.session.scalars(select(ContainerStockRow).where(ContainerStockRow.community_entity_id == town_id))
    sealed = sum(row.count * CONTAINERS[row.kind].capacity for row in rows if CONTAINERS[row.kind].sealed) * ctx.rules.containers.per_capacity
    covered = min(1.0, sealed / units) if units > 0 else 0.0
    return 1 - covered * ctx.rules.containers.sealed_pct / PERCENT


async def read_marks(ctx: TickContext, site: EntityRow) -> bool:
    places = [place for place in (site.id, site.location_id) if place is not None]
    marked = await ctx.session.scalar(
        select(ContainerStockRow.community_entity_id).where(ContainerStockRow.community_entity_id.in_(places), ContainerStockRow.broken > 0).limit(1)
    )
    if marked is None:
        return False
    hidden = await ctx.session.scalar(
        select(RouteRow.id).where(RouteRow.known.is_(False), (RouteRow.world_a_id == site.world_id) | (RouteRow.world_b_id == site.world_id)).limit(1)
    )
    if hidden is not None:
        await reveal_hidden_route(ctx, int(hidden), site.id)
    return True


async def keep_containers(ctx: TickContext, tally: ContainerTally) -> None:
    towns = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    for town in list(towns):
        if held(town.id):
            continue
        await break_containers(ctx, town, tally)
        await make_containers(ctx, town, tally)
    await ctx.session.flush()
