from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.means import AIDS
from aerona.constants.units import PERCENT
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.economy import TradeRouteProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.means import NavigationKitRow
from aerona.db.tables.mind import SkillRow
from aerona.db.write_guard import held
from aerona.domain.enums.economy import TradeMode
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import SkillKind
from aerona.engine.context import TickContext
from aerona.engine.eras.effects import era_techniques
from aerona.engine.notes import note
from aerona.engine.primitives.folk import present_in
from aerona.engine.primitives.numbers import clamp_int
from aerona.rules.registry import Rules


@dataclass
class NavigationTally:
    equipped: int = 0
    refined: int = 0


async def ports(ctx: TickContext) -> list[EntityRow]:
    ends = (
        select(TradeRouteProfileRow.first_market_id)
        .where(TradeRouteProfileRow.mode == TradeMode.SEA)
        .union(select(TradeRouteProfileRow.second_market_id).where(TradeRouteProfileRow.mode == TradeMode.SEA))
    )
    found = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.id.in_(ends), EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    return list(found)


async def equip_ports(ctx: TickContext, tally: NavigationTally) -> None:
    table = ctx.rules.navigation_instruments
    for town in await ports(ctx):
        if held(town.id):
            continue
        known = await era_techniques(ctx.session, town.id)
        for aid, spec in AIDS.items():
            if spec.needs not in known or await ctx.session.get(NavigationKitRow, (town.id, aid)) is not None:
                continue
            ctx.session.add(NavigationKitRow(holder_entity_id=town.id, aid=aid, quality=table.seed_quality, since_epoch=ctx.epoch, locked=[]))
            tally.equipped += 1
            await note(ctx, f"The pilots of {town.name} took up the {spec.label.lower()}.", key="navigation.aid", ids=[town.id])
    await ctx.session.flush()


async def best_navigator(ctx: TickContext, town: EntityRow) -> int:
    level = await ctx.session.scalar(
        select(SkillRow.level)
        .join(EntityRow, EntityRow.id == SkillRow.holder_node_id)
        .where(await present_in(ctx.session, town), EntityRow.status == EntityStatus.CANON, SkillRow.skill == SkillKind.NAVIGATION)
        .order_by(SkillRow.level.desc())
        .limit(1)
    )
    return int(level or 0)


async def refine(ctx: TickContext, tally: NavigationTally) -> None:
    table = ctx.rules.navigation_instruments
    for row in list(await ctx.session.scalars(select(NavigationKitRow).order_by(NavigationKitRow.holder_entity_id, NavigationKitRow.aid))):
        town = await ctx.session.get(EntityRow, row.holder_entity_id)
        if town is None or held(town.id) or "quality" in row.locked:
            continue
        if await best_navigator(ctx, town) >= table.refine_skill:
            row.quality = clamp_int(row.quality + table.refine_gain, 0, PERCENT)
            tally.refined += 1


def aid_works(rules: Rules, kit: NavigationKitRow, world: WorldRow | None) -> bool:
    return not AIDS[kit.aid].magnetic or (world is not None and world.magnetism >= rules.navigation_instruments.magnetism_from)


async def accuracy_of(ctx: TickContext, town_id: int) -> int:
    table = ctx.rules.navigation_instruments
    town = await ctx.session.get(EntityRow, town_id)
    if town is None:
        return 0
    world = await ctx.session.get(WorldRow, town.world_id)
    kits = await ctx.session.scalars(select(NavigationKitRow).where(NavigationKitRow.holder_entity_id == town_id))
    instruments = sum(kit.quality * table.aid_pct // PERCENT for kit in kits if aid_works(ctx.rules, kit, world))
    return clamp_int(instruments + await best_navigator(ctx, town) * table.skill_pct, 0, PERCENT)


async def instrument_navigation(ctx: TickContext, ends: tuple[int, int], hops: int) -> float:
    table = ctx.rules.navigation_instruments
    accuracy = max([await accuracy_of(ctx, end) for end in ends])
    factor = 1 - accuracy * table.danger_pct / PERCENT / PERCENT
    if hops > table.shore_hops and accuracy < table.open_sea_from:
        factor *= 1 + table.adrift_pct / PERCENT
    return factor


async def keep_navigation(ctx: TickContext, tally: NavigationTally) -> None:
    await equip_ports(ctx, tally)
    await refine(ctx, tally)
    await ctx.session.flush()
