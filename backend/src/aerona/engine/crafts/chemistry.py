from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.crafts import ChemicalWorksRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.industry import RegionPollutionRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.crafts import ChemicalProduct
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.industry import Pollutant
from aerona.engine.body.customs import people_of
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.economy.stocks import goods_of
from aerona.engine.industry.pollution import shift
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.lore.research import has_technique
from aerona.engine.notes import note
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int

P = ChemicalProduct
C = CommodityKind


@dataclass(frozen=True)
class Recipe:
    techniques: tuple[Technique, ...]
    raw: CommodityKind
    made: CommodityKind | None


RECIPES = {
    P.DYE: Recipe((Technique.HERBALISM,), C.HERBS, C.DYE),
    P.SOAP: Recipe((Technique.HERBALISM,), C.MEAT, None),
    P.MORDANT: Recipe((Technique.ALCHEMY,), C.ORE, C.DYE),
    P.TANNING: Recipe((Technique.HERBALISM,), C.TIMBER, C.CLOTH),
    P.FERTILISER: Recipe((Technique.CROP_ROTATION,), C.DUNG, None),
    P.MEDICINE: Recipe((Technique.HERBALISM,), C.HERBS, C.MEDICINE),
    P.INCENDIARY: Recipe((Technique.ALCHEMY,), C.FUEL, C.SIEGE_MATERIEL),
    P.EXPLOSIVE: Recipe((Technique.ALCHEMY, Technique.SIEGECRAFT), C.COAL, C.SIEGE_MATERIEL),
}


@dataclass
class ChemistryTally:
    founded: int = 0
    made: int = 0
    accidents: int = 0


async def knows(ctx: TickContext, town: EntityRow, techniques: tuple[Technique, ...]) -> bool:
    people = await people_of(ctx.session, town)
    holders = [town.id, *([people.id] if people is not None else [])]
    for technique in techniques:
        if not any([await has_technique(ctx.session, holder, technique) for holder in holders]):
            return False
    return True


async def found_works(ctx: TickContext, town: EntityRow, tally: ChemistryTally) -> None:
    table = ctx.rules.chemistry
    have = set(await ctx.session.scalars(select(ChemicalWorksRow.product).where(ChemicalWorksRow.settlement_entity_id == town.id)))
    for product, recipe in RECIPES.items():
        if product in have or not await knows(ctx, town, recipe.techniques):
            continue
        if not ctx.rng(seed_of("chemistry.found", town.id, product.value, ctx.epoch)).chance(table.found_chance):
            continue
        ctx.session.add(ChemicalWorksRow(settlement_entity_id=town.id, product=product, founded_epoch=ctx.epoch, locked=[]))
        tally.founded += 1
        await note(ctx, f"{town.name} set up works for {product.value.replace('_', ' ')}.", key="chemistry.founded", ids=[town.id])
        return


async def run_works(ctx: TickContext, town: EntityRow, row: ChemicalWorksRow, atlas: RegionAtlas, tally: ChemistryTally) -> None:
    table = ctx.rules.chemistry
    recipe = RECIPES[row.product]
    ledger = goods_of(ctx.session, ctx.epoch)
    wanted = max(1, round(row.output / table.input_per_output))
    taken = await ledger.take_units(town.id, recipe.raw, wanted, GoodsFlow.INPUT)
    if "output" not in row.locked:
        row.output = clamp_int(row.output + (table.output_gain if taken >= wanted else -table.output_gain), 0, PERCENT)
    made = row.output // table.yield_per_output
    if recipe.made is not None and made > 0:
        await ledger.add(town.id, recipe.made, made, GoodsFlow.PRODUCTION)
        tally.made += made
    region = atlas.top_region(town.id)
    if region is not None and row.pollution > 0 and not held(region):
        pollution = await ctx.session.get(RegionPollutionRow, region)
        if pollution is None:
            pollution = RegionPollutionRow(region_node_id=region, air=0, water=0, soil=0, polluters={}, epoch=ctx.epoch, locked=[])
            ctx.session.add(pollution)
        amount = row.pollution * row.output / PERCENT * table.pollution_pct / PERCENT
        shift(pollution, Pollutant.WATER, amount)
        shift(pollution, Pollutant.SOIL, amount)
    rng = ctx.rng(seed_of("chemistry.accident", town.id, row.product.value, ctx.epoch))
    if row.output <= 0 or not rng.chance(row.hazard):
        return
    workers = [
        mortal
        for mortal in await ctx.session.scalars(
            select(EntityRow)
            .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, await present_among(ctx.session, [town.id]))
            .order_by(EntityRow.id)
        )
        if not held(mortal.id)
    ]
    if not workers:
        return
    hurt = rng.pick(workers)
    await apply_hits(
        ctx, hurt, Harm(damage=table.accident_harm, cause=HarmCause.ACCIDENT, death_cause=f"died in an accident at the works for {row.product.value}")
    )
    if "accidents" not in row.locked:
        row.accidents += 1
    tally.accidents += 1


async def keep_chemistry(ctx: TickContext, tally: ChemistryTally) -> None:
    atlas = await RegionAtlas.load(ctx.session)
    towns = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    for town in list(towns):
        if held(town.id):
            continue
        await found_works(ctx, town, tally)
        for row in list(
            await ctx.session.scalars(select(ChemicalWorksRow).where(ChemicalWorksRow.settlement_entity_id == town.id).order_by(ChemicalWorksRow.product))
        ):
            await run_works(ctx, town, row, atlas, tally)
    await ctx.session.flush()
