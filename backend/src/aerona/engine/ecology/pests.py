from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.society import CreatureTrait
from aerona.engine.context import TickContext
from aerona.engine.ecology.ranges import Wilds
from aerona.engine.economy.stocks import GoodsLedger
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import set_stats, stat

T = CreatureTrait
PESTS = frozenset({T.CROP_PEST, T.IRON_EATING, T.PLAGUE_BEARER, T.SPIRIT_SIGHT})


async def gnaw_ore(ctx: TickContext, wilds: Wilds, region: int, amount: int) -> int:
    ledger = GoodsLedger(ctx.session, ctx.epoch)
    taken = 0
    for community in wilds.hunters.get(region, []):
        taken += await ledger.take_units(community.id, CommodityKind.ORE, amount, GoodsFlow.LOSS)
    return taken


async def calm_spirits(ctx: TickContext, region: int, amount: int, wilds: Wilds) -> int:
    calmed = 0
    spirits = await ctx.session.scalars(select(EntityRow).where(EntityRow.entity_type == EntityType.SPIRIT, EntityRow.status == EntityStatus.CANON))
    for spirit in list(spirits):
        if wilds.atlas.top_region(spirit.id) == region and stat(spirit, "unrest") is not None:
            set_stats(spirit, unrest=clamp_int((stat(spirit, "unrest") or 0) - amount, 0, PERCENT))
            calmed += 1
    return calmed


async def plague_of_pests(ctx: TickContext, wilds: Wilds) -> dict[str, int]:
    table = ctx.rules.pests
    counts = {"blighted": 0, "ore_gnawed": 0, "disease_spread": 0, "spirits_calmed": 0}
    for species_id, rows in sorted(wilds.ranges.items()):
        traits = wilds.traits.get(species_id, set()) & PESTS
        if not traits:
            continue
        for region, row in sorted(rows.items()):
            weight = row.abundance / PERCENT
            land = wilds.lands.get(region)
            if T.CROP_PEST in traits and land is not None and ctx.rng(f"pest.{species_id}.{region}.{ctx.epoch}").chance(table.pest_year_chance):
                land.harvest_pct = clamp_int(land.harvest_pct - round_half_up(table.harvest_loss * weight), 0, PERCENT * 2)
                counts["blighted"] += 1
            if T.IRON_EATING in traits:
                counts["ore_gnawed"] += await gnaw_ore(ctx, wilds, region, round_half_up(table.ore_loss * weight))
            if T.PLAGUE_BEARER in traits and land is not None:
                land.disease_load = clamp_int(land.disease_load + round_half_up(table.disease_load * weight), 0, PERCENT)
                counts["disease_spread"] += 1
            if T.SPIRIT_SIGHT in traits:
                counts["spirits_calmed"] += await calm_spirits(ctx, region, ctx.rules.habitat.spirit_calm, wilds)
    return counts
