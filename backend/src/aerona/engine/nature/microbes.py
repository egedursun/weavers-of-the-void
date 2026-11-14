from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.read_memo import memoized
from aerona.db.tables.agrarian import SoilNutrientRow
from aerona.db.tables.cuisine import CommunityDishRow, DishRow
from aerona.db.tables.disease import OutbreakRow
from aerona.db.tables.economy import TradeRouteProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.industry import RegionPollutionRow
from aerona.db.tables.nature import FermentCultureRow, SoilMicrobiotaRow
from aerona.db.write_guard import held
from aerona.domain.enums.agrarian import NutrientKind
from aerona.domain.enums.cuisine import CookingMethod, DishCourse
from aerona.domain.enums.disease import OutbreakStatus
from aerona.domain.enums.economy import TradeRouteStatus
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.nature import FermentKind
from aerona.engine.context import TickContext
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.rules.registry import Rules

F = FermentKind
M = CookingMethod
CULTURED: Mapping[FermentKind, frozenset[CookingMethod]] = MappingProxyType(
    {
        F.YEAST: frozenset({M.BAKED}),
        F.STARTER: frozenset({M.BAKED}),
        F.MOULD: frozenset({M.CURED, M.FERMENTED}),
        F.LACTIC: frozenset({M.FERMENTED, M.PICKLED}),
        F.VINEGAR: frozenset({M.PICKLED}),
    }
)
FOUNDED: Mapping[CookingMethod, FermentKind] = MappingProxyType({M.BAKED: F.STARTER, M.FERMENTED: F.LACTIC, M.CURED: F.MOULD, M.PICKLED: F.VINEGAR})
HOLDERS = (EntityType.SETTLEMENT, EntityType.FACTION, EntityType.STRUCTURE, EntityType.HOUSE)


@dataclass
class MicrobeTally:
    soils: int = 0
    sterile: int = 0
    founded: int = 0
    tended: int = 0
    lost: int = 0
    traded: int = 0


def microbe_factor(rules: Rules, life: int | None) -> float:
    if life is None:
        return 1.0
    half = PERCENT / 2
    return max(0.0, 1 + (life - half) / half * rules.microbes.recycling_pct / PERCENT)


@memoized(SoilMicrobiotaRow)
async def soil_lives(session: AsyncSession) -> dict[int, int]:
    return {row.region_entity_id: row.life for row in await session.scalars(select(SoilMicrobiotaRow))}


def target_life(rules: Rules, land: RegionEnvironmentRow, pollution: int, salinity: int) -> int:
    table = rules.microbes
    value = (
        table.rest
        + land.moisture * table.moisture_pct / PERCENT / 2
        + (land.soil_base - PERCENT / 2) * table.fertility_pct / PERCENT
        - pollution * table.pollution_pct / PERCENT
        - salinity * table.salinity_pct / PERCENT
    )
    return clamp_int(round_half_up(value), 0, PERCENT)


async def keep_microbiota(ctx: TickContext, tally: MicrobeTally) -> None:
    table = ctx.rules.microbes
    atlas = await RegionAtlas.load(ctx.session)
    pollution = {row.region_node_id: row.soil for row in await ctx.session.scalars(select(RegionPollutionRow))}
    salt = {
        row.region_entity_id: row.stock for row in await ctx.session.scalars(select(SoilNutrientRow).where(SoilNutrientRow.nutrient == NutrientKind.SALINITY))
    }
    rows = {row.region_entity_id: row for row in await ctx.session.scalars(select(SoilMicrobiotaRow))}
    for land in await ctx.session.scalars(select(RegionEnvironmentRow).order_by(RegionEnvironmentRow.entity_id)):
        if atlas.is_water(land.entity_id) or held(land.entity_id):
            continue
        target = target_life(ctx.rules, land, pollution.get(land.entity_id, 0), salt.get(land.entity_id, 0))
        row = rows.get(land.entity_id)
        if row is None:
            ctx.session.add(SoilMicrobiotaRow(region_entity_id=land.entity_id, life=target, updated_epoch=ctx.epoch, locked=[]))
            tally.soils += 1
            continue
        sterile = row.life < table.sterile_below
        if "life" not in row.locked:
            share = table.sterile_drift_pct if sterile else table.drift_pct
            row.life = clamp_int(row.life + round_half_up((target - row.life) * share / PERCENT), 0, PERCENT)
        if "sterile_epochs" not in row.locked:
            row.sterile_epochs = row.sterile_epochs + 1 if row.life < table.sterile_below else 0
        row.updated_epoch = ctx.epoch
        tally.soils += 1
        tally.sterile += row.life < table.sterile_below
    await ctx.session.flush()


async def live_cultures(session: AsyncSession, holder_ids: list[int]) -> list[FermentCultureRow]:
    if not holder_ids:
        return []
    return list(
        await session.scalars(
            select(FermentCultureRow)
            .where(FermentCultureRow.holder_entity_id.in_(holder_ids), FermentCultureRow.lost_epoch.is_(None))
            .order_by(FermentCultureRow.id)
        )
    )


async def keepers_in(session: AsyncSession, town_id: int) -> list[int]:
    inside = await session.scalars(select(EntityRow.id).where(EntityRow.location_id == town_id, EntityRow.entity_type.in_(list(HOLDERS[1:]))))
    return [town_id, *inside]


async def culture_lift(session: AsyncSession, rules: Rules, town_id: int, method: CookingMethod, course: DishCourse) -> float:
    best = 0
    for row in await live_cultures(session, await keepers_in(session, town_id)):
        if method in CULTURED[row.kind] or (row.kind is F.YEAST and course is DishCourse.DRINK):
            best = max(best, row.quality)
    return 1 + best / PERCENT * rules.fermentation.delight_pct / PERCENT


async def found_cultures(ctx: TickContext, tally: MicrobeTally) -> None:
    table = ctx.rules.fermentation
    pairs = await ctx.session.execute(
        select(CommunityDishRow.community_entity_id, DishRow.method, DishRow.course)
        .join(DishRow, DishRow.id == CommunityDishRow.dish_id)
        .join(EntityRow, EntityRow.id == CommunityDishRow.community_entity_id)
        .where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON, DishRow.retired.is_(False))
        .order_by(CommunityDishRow.community_entity_id, DishRow.id)
    )
    wanted: dict[int, set[FermentKind]] = {}
    for town, method, course in pairs:
        kind = F.YEAST if course is DishCourse.DRINK else FOUNDED.get(method)
        if kind is not None:
            wanted.setdefault(town, set()).add(kind)
    for town, kinds in wanted.items():
        if held(town):
            continue
        have = {row.kind for row in await live_cultures(ctx.session, [town])}
        for kind in sorted(kinds - have):
            if ctx.rng(seed_of("culture.found", town, kind.value, ctx.epoch)).chance(table.found_chance):
                ctx.session.add(FermentCultureRow(holder_entity_id=town, kind=kind, quality=table.start_quality, since_epoch=ctx.epoch, locked=[]))
                tally.founded += 1


async def tend_cultures(ctx: TickContext, tally: MicrobeTally) -> None:
    table = ctx.rules.fermentation
    atlas = await RegionAtlas.load(ctx.session)
    sick = set(await ctx.session.scalars(select(OutbreakRow.region_entity_id).where(OutbreakRow.status == OutbreakStatus.ACTIVE)))
    for row in list(await ctx.session.scalars(select(FermentCultureRow).where(FermentCultureRow.lost_epoch.is_(None)).order_by(FermentCultureRow.id))):
        holder = await ctx.session.get(EntityRow, row.holder_entity_id)
        if holder is None or holder.status is not EntityStatus.CANON or held(holder.id):
            continue
        region = atlas.top_region(holder.id)
        if region in sick and "lost_epoch" not in row.locked and ctx.rng(seed_of("culture.plague", row.id, ctx.epoch)).chance(table.plague_loss_chance):
            row.lost_epoch = ctx.epoch
            tally.lost += 1
            continue
        if "quality" not in row.locked and row.quality < table.ceiling:
            row.quality = min(table.ceiling, row.quality + table.tending)
            tally.tended += 1


async def trade_cultures(ctx: TickContext, tally: MicrobeTally) -> None:
    table = ctx.rules.fermentation
    routes = await ctx.session.scalars(
        select(TradeRouteProfileRow).where(TradeRouteProfileRow.status == TradeRouteStatus.OPEN).order_by(TradeRouteProfileRow.route_entity_id)
    )
    for route in list(routes):
        for giver, taker in ((route.first_market_id, route.second_market_id), (route.second_market_id, route.first_market_id)):
            if held(taker):
                continue
            have = {row.kind for row in await live_cultures(ctx.session, [taker])}
            for row in await live_cultures(ctx.session, [giver]):
                if row.kind in have or not ctx.rng(seed_of("culture.trade", row.id, taker, ctx.epoch)).chance(table.trade_chance):
                    continue
                quality = round_half_up(row.quality * table.traded_quality_pct / PERCENT)
                ctx.session.add(FermentCultureRow(holder_entity_id=taker, kind=row.kind, quality=quality, since_epoch=ctx.epoch, locked=[]))
                have.add(row.kind)
                tally.traded += 1


async def keep_microbes(ctx: TickContext, tally: MicrobeTally) -> None:
    await keep_microbiota(ctx, tally)
    await found_cultures(ctx, tally)
    await tend_cultures(ctx, tally)
    await trade_cultures(ctx, tally)
    await ctx.session.flush()
