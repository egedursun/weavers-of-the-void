from dataclasses import dataclass

from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.nature import PlantDefence
from aerona.engine.context import TickContext
from aerona.engine.economy.stocks import GoodsLedger
from aerona.engine.nature.cover import defence_cover
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.stats import shift_stat, stat


@dataclass
class PlantTally:
    dangerous: int = 0
    medicine: int = 0


async def keep_plant_defences(ctx: TickContext, tally: PlantTally) -> None:
    table = ctx.rules.plant_defences
    atlas = await RegionAtlas.load(ctx.session)
    ledger = GoodsLedger(ctx.session, ctx.epoch)
    for region_id, cover in sorted((await defence_cover(ctx.session)).items()):
        if held(region_id):
            continue
        region = await ctx.session.get(EntityRow, region_id)
        floor = round_half_up(cover.get(PlantDefence.CARNIVOROUS, 0.0) * table.carnivorous_danger)
        if region is not None and floor > 0 and (stat(region, "danger") or 0) < floor:
            shift_stat(region, "danger", floor - (stat(region, "danger") or 0))
            tally.dangerous += 1
        gathered = round_half_up(cover.get(PlantDefence.TOXINS, 0.0) * table.toxin_medicine)
        if gathered <= 0:
            continue
        for town in atlas.communities_in(region_id):
            if not held(town):
                tally.medicine += await ledger.add(town, CommodityKind.MEDICINE, gathered, GoodsFlow.HARVEST)
    await ctx.session.flush()
