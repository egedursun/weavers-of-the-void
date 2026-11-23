from collections.abc import Awaitable, Callable, Mapping

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.industry import RegionPollutionRow
from aerona.db.tables.living import LivingLineRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.living import LineTrait
from aerona.engine.context import TickContext
from aerona.engine.living.profiles import town_of
from aerona.engine.living.traits import traits_of
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_percent
from aerona.engine.primitives.stats import shift_stat
from aerona.engine.recording.terms import explaining, term


def at_strength(value: int, strength: int) -> int:
    return max(0, value * min(PERCENT, strength) // PERCENT)


async def kept_town(ctx: TickContext, line: LivingLineRow) -> EntityRow | None:
    owner = await ctx.session.get(EntityRow, line.owner_node_id) if line.owner_node_id is not None else None
    if owner is None:
        return None
    town_id = owner.id if owner.entity_type is EntityType.SETTLEMENT else await town_of(ctx, owner)
    town = await ctx.session.get(EntityRow, town_id) if town_id is not None else None
    return town if town is not None and not held(town.id) else None


async def light(ctx: TickContext, line: LivingLineRow, town: EntityRow | None, strength: int) -> None:
    if town is None:
        return
    settled = await ctx.session.get(SettlementProfileRow, town.id)
    if settled is not None and "public_order" not in settled.locked:
        gain = at_strength(ctx.rules.living.light_order, strength)
        with explaining():
            term("living.light_order", gain, source_node_id=line.species_entity_id)
            settled.public_order = clamp_percent(settled.public_order + gain)


async def build(ctx: TickContext, line: LivingLineRow, town: EntityRow | None, strength: int) -> None:
    if town is None:
        return
    gain = at_strength(ctx.rules.living.building_defense, strength)
    with explaining():
        term("living.building_defense", gain, source_node_id=line.species_entity_id)
        shift_stat(town, "defense", gain, ctx.rules.society.default_stat, high=PERCENT)


async def filter_land(ctx: TickContext, line: LivingLineRow, town: EntityRow | None, strength: int) -> None:
    if town is None:
        return
    region_id = (await RegionAtlas.load(ctx.session)).top_region(town.id)
    fouled = await ctx.session.get(RegionPollutionRow, region_id) if region_id is not None else None
    if fouled is None or held(fouled.region_node_id):
        return
    cleaned = at_strength(ctx.rules.living.filtering_clean, strength)
    with explaining():
        term("living.filtering_clean", -cleaned, source_node_id=line.species_entity_id)
        for column in FILTERED:
            if column not in fouled.locked:
                setattr(fouled, column, clamp_percent(getattr(fouled, column) - cleaned))


async def keep_learning(ctx: TickContext, line: LivingLineRow, _town: EntityRow | None, strength: int) -> None:
    if "stability" not in line.locked:
        gain = at_strength(ctx.rules.living.learning_stability, strength)
        with explaining():
            term("living.learning_stability", gain, source_node_id=line.species_entity_id)
            line.stability = clamp_percent(line.stability + gain)


async def trait_works(ctx: TickContext) -> int:
    worked = 0
    for line in list(await ctx.session.scalars(select(LivingLineRow).order_by(LivingLineRow.id))):
        if line.owner_node_id is not None and held(line.owner_node_id):
            continue
        traits = await traits_of(ctx.session, line.id)
        town = await kept_town(ctx, line)
        for trait, work in TRAIT_WORKS.items():
            strength = traits.get(trait, 0)
            if strength > 0 and (town is not None or trait is LineTrait.INHERITED_LEARNING):
                await work(ctx, line, town, strength)
                worked += 1
    return worked


FILTERED = ("air", "water")

Work = Callable[[TickContext, LivingLineRow, EntityRow | None, int], Awaitable[None]]
TRAIT_WORKS: Mapping[LineTrait, Work] = {
    LineTrait.INHERITED_LEARNING: keep_learning,
    LineTrait.LIGHT_MAKING: light,
    LineTrait.SECRETES_BUILDING: build,
    LineTrait.FILTERING: filter_land,
}
