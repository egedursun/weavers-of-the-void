from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.flora import RegionCropRow
from aerona.domain.enums.ecology import SpeciesClass
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.society import CreatureTrait
from aerona.engine.context import TickContext
from aerona.engine.ecology.flora import host_share
from aerona.engine.ecology.ranges import Wilds
from aerona.engine.economy.stocks import GoodsLedger
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import set_stats, stat

T = CreatureTrait
PESTS = frozenset({T.CROP_PEST, T.IRON_EATING, T.PLAGUE_BEARER, T.SPIRIT_SIGHT})
VERMIN_TRAITS = frozenset({T.CROP_PEST, T.PLAGUE_BEARER})


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


def pest_traits(wilds: Wilds, species_id: int) -> set[CreatureTrait]:
    traits = wilds.traits.get(species_id, set()) & PESTS
    profile = wilds.profiles.get(species_id)
    if profile is not None and profile.species_class is SpeciesClass.VERMIN:
        traits |= VERMIN_TRAITS
    return traits


async def crop_loss(ctx: TickContext, species_id: int, region: int, weight: float) -> float:
    crops = list(await ctx.session.scalars(select(RegionCropRow).where(RegionCropRow.region_entity_id == region)))
    share = await host_share(ctx.session, species_id, crops)
    if share is None:
        return ctx.rules.pests.harvest_loss * weight
    return ctx.rules.flora.pest_loss * weight * share


async def plague_of_pests(ctx: TickContext, wilds: Wilds) -> dict[str, int]:
    table = ctx.rules.pests
    counts = {"blighted": 0, "ore_gnawed": 0, "disease_spread": 0, "spirits_calmed": 0}
    for species_id, rows in sorted(wilds.ranges.items()):
        traits = pest_traits(wilds, species_id)
        if not traits:
            continue
        for region, row in sorted(rows.items()):
            weight = row.abundance / PERCENT
            land = wilds.lands.get(region)
            if T.CROP_PEST in traits and land is not None and ctx.rng(f"pest.{species_id}.{region}.{ctx.epoch}").chance(table.pest_year_chance):
                loss = round_half_up(await crop_loss(ctx, species_id, region, weight))
                if loss > 0 and "harvest_pct" not in land.locked:
                    land.harvest_pct = clamp_int(land.harvest_pct - loss, 0, PERCENT * 2)
                    counts["blighted"] += 1
            if T.IRON_EATING in traits:
                counts["ore_gnawed"] += await gnaw_ore(ctx, wilds, region, round_half_up(table.ore_loss * weight))
            if T.PLAGUE_BEARER in traits and land is not None:
                land.disease_load = clamp_int(land.disease_load + round_half_up(table.disease_load * weight), 0, PERCENT)
                counts["disease_spread"] += 1
            if T.SPIRIT_SIGHT in traits:
                counts["spirits_calmed"] += await calm_spirits(ctx, region, ctx.rules.habitat.spirit_calm, wilds)
    return counts
