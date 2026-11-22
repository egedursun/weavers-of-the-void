from sqlalchemy import select

from aerona.catalog.life.living import BREED_FERTILITYS
from aerona.catalog.life_traits import METABOLISM_TRAITS, having
from aerona.constants.units import PERCENT
from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.living import LivingLineRow, LivingLineTraitRow, LivingProfileRow
from aerona.db.tables.military import ArmyUnitRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.economy import GoodsFlow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.life_traits import MetabolismTrait
from aerona.domain.enums.living import Fertility, GrowthStage, LineTrait, Metabolism
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import StepAction, StepOutcome
from aerona.engine.context import TickContext
from aerona.engine.economy.stocks import goods_of
from aerona.engine.living.traits import eased, scaled, traits_of
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, clamp_percent
from aerona.engine.primitives.records import retire_in
from aerona.engine.primitives.stats import shift_stat
from aerona.engine.recording.record import StepDraft, record

SELF_FED = having(METABOLISM_TRAITS, MetabolismTrait.SELF_FED)
STILL = frozenset({GrowthStage.DEAD})
UNGROWN = frozenset({GrowthStage.SEED, GrowthStage.YOUNG})
BEINGS = frozenset({EntityType.BEAST, EntityType.MORTAL})


async def town_of(ctx: TickContext, thing: EntityRow) -> int | None:
    place = await ctx.session.get(EntityRow, thing.location_id) if thing.location_id is not None else None
    if place is None:
        return None
    if place.entity_type is EntityType.SETTLEMENT:
        return place.id
    return await town_of(ctx, place) if place.entity_type is not EntityType.REGION else None


async def fed(ctx: TickContext, row: LivingProfileRow, thing: EntityRow) -> bool:
    if row.metabolism in SELF_FED or row.metabolism is Metabolism.DORMANT:
        return True
    if row.metabolism is Metabolism.HOST:
        host = await ctx.session.get(EntityRow, row.bonded_to_node_id) if row.bonded_to_node_id is not None else None
        if host is None or host.status is not EntityStatus.CANON:
            return False
        if not held(host.id):
            shift_stat(host, "hp", -max(1, row.feed_per_season // 2), 0)
        return True
    if row.feed_commodity is None or not row.feed_per_season:
        return True
    town = await town_of(ctx, thing)
    if town is None or held(town):
        return False
    wanted = row.feed_per_season * ctx.rules.living.seasons_in_epoch
    eaten = await goods_of(ctx.session, ctx.epoch).take_units(town, row.feed_commodity, wanted, GoodsFlow.INPUT)
    return eaten >= wanted


def stage_for(ctx: TickContext, row: LivingProfileRow) -> GrowthStage:
    table = ctx.rules.living
    life = max(1, row.lifespan_years * ctx.rules.living.seasons_per_epoch)
    if row.health <= 0:
        return GrowthStage.DEAD
    if row.age_seasons * PERCENT >= life * table.dying_at_pct:
        return GrowthStage.DYING
    if row.age_seasons * PERCENT >= life * table.old_at_pct:
        return GrowthStage.OLD
    if row.age_seasons >= table.prime_at:
        return GrowthStage.PRIME
    if row.age_seasons >= table.grown_at:
        return GrowthStage.GROWN
    return GrowthStage.YOUNG if row.age_seasons >= table.young_at else GrowthStage.SEED


async def decay(ctx: TickContext, thing: EntityRow) -> None:
    atlas = await RegionAtlas.load(ctx.session)
    region = atlas.top_region(thing.id)
    land = await ctx.session.get(RegionEnvironmentRow, region) if region is not None else None
    if land is not None and not held(land.entity_id) and "soil_fertility" not in (land.locked or []):
        land.soil_fertility = clamp_percent(land.soil_fertility + ctx.rules.living.decay_fertility)


async def end(ctx: TickContext, row: LivingProfileRow, thing: EntityRow) -> None:
    await decay(ctx, thing)
    if thing.status is EntityStatus.CANON:
        await retire_in(ctx, thing, "its life ran out", EntityStatus.DEAD if thing.entity_type in BEINGS else EntityStatus.DESTROYED)
    await record(
        ctx,
        "living.died",
        roles={IncidentRole.SUBJECT: thing.id},
        facts={"age_seasons": row.age_seasons, "lifespan": row.lifespan_years},
        steps=(StepDraft(StepAction.DIE, actor=thing.id, outcome=StepOutcome.KILLED),),
    )


async def breed(ctx: TickContext, row: LivingProfileRow) -> None:
    if row.line_id is None or row.growth_stage is not GrowthStage.PRIME or row.fertility in BREED_FERTILITYS:
        return
    line = await ctx.session.get(LivingLineRow, row.line_id)
    if (
        line is None
        or held(row.thing_node_id)
        or not ctx.rng(f"living.breed.{row.thing_node_id}.{ctx.epoch}").chance(ctx.rules.living.over_epoch(ctx.rules.living.breed_chance))
    ):
        return
    if "generation" not in line.locked:
        line.generation += 1
    await mutate(ctx, line)
    if row.fertility is Fertility.BREEDS_WILD and "drift_pct" not in line.locked:
        line.drift_pct = clamp_percent(line.drift_pct + ctx.rules.living.wild_drift)


async def mutate(ctx: TickContext, line: LivingLineRow) -> None:
    table = ctx.rules.living
    rng = ctx.rng(f"living.mutate.{line.id}.{line.generation}")
    if not rng.chance(table.mutation_pct):
        return
    carried = set(await ctx.session.scalars(select(LivingLineTraitRow.trait).where(LivingLineTraitRow.line_id == line.id)))
    fresh = [trait for trait in LineTrait if trait not in carried and trait is not LineTrait.SAPIENCE]
    if not fresh:
        return
    trait = rng.pick(fresh)
    strength = table.mutation_strength if rng.chance(PERCENT // 2) else -table.mutation_strength
    ctx.session.add(LivingLineTraitRow(line_id=line.id, trait=trait, strength=strength, side_effect=strength < 0, locked=[]))
    await record(ctx, "living.mutated", roles={IncidentRole.SUBJECT: line.species_entity_id}, facts={"line": line.name, "trait": trait, "strength": strength})


async def mend_army(ctx: TickContext, row: LivingProfileRow, thing: EntityRow, eating: bool, healed: int) -> None:
    if thing.entity_type is not EntityType.ARMY:
        return
    for unit in list(await ctx.session.scalars(select(ArmyUnitRow).where(ArmyUnitRow.army_entity_id == thing.id))):
        if unit.locked:
            continue
        if eating:
            mended = unit.wounded * healed // PERCENT
            unit.wounded -= mended
            unit.count += mended
        else:
            unit.condition = clamp_percent(unit.condition - ctx.rules.living.unfed_army_harm)


async def mend_body(ctx: TickContext, row: LivingProfileRow, healed: int) -> None:
    work = await ctx.session.get(StructureProfileRow, row.thing_node_id)
    if work is not None and "condition" not in work.locked:
        work.condition = clamp_percent(work.condition + healed)
        if row.growth_stage in UNGROWN:
            work.condition = min(work.condition, clamp_percent(row.size_pct))
    if not healed:
        return
    vessel = await ctx.session.get(VesselProfileRow, row.thing_node_id)
    if vessel is not None and "condition" not in (vessel.locked or []):
        vessel.condition = clamp_percent(vessel.condition + healed)


async def live(ctx: TickContext, row: LivingProfileRow, thing: EntityRow) -> None:
    table = ctx.rules.living
    eating = await fed(ctx, row, thing)
    healed = row.regeneration * table.regeneration_pct // PERCENT
    if row.metabolism is not Metabolism.DORMANT and "age_seasons" not in row.locked:
        row.age_seasons += table.seasons_in_epoch
    traits = await traits_of(ctx.session, row.line_id)
    if "health" not in row.locked:
        hunger = eased(table.hunger_harm, traits.get(LineTrait.HARDINESS, 0))
        row.health = clamp_percent(row.health + (healed if eating else -hunger))
    if "bond" not in row.locked and row.bonded_to_node_id is not None:
        row.bond = clamp_percent(row.bond + (scaled(table.care_bond, traits.get(LineTrait.DOCILITY, 0)) if eating else -table.neglect_bond))
    await mend_body(ctx, row, healed if eating else 0)
    await mend_army(ctx, row, thing, eating, healed)
    if "size_pct" not in row.locked and eating and row.growth_stage in {GrowthStage.SEED, GrowthStage.YOUNG, GrowthStage.GROWN}:
        row.size_pct = clamp_int(row.size_pct + table.growth_size, 0, scaled(PERCENT, traits.get(LineTrait.SIZE, 0)))
    if "growth_stage" not in row.locked:
        row.growth_stage = stage_for(ctx, row)
    await breed(ctx, row)
    await turn_away(ctx, row, thing)
    if row.growth_stage is GrowthStage.DEAD:
        await end(ctx, row, thing)


async def keep_profiles(ctx: TickContext) -> int:
    kept = 0
    for row in list(
        await ctx.session.scalars(select(LivingProfileRow).where(LivingProfileRow.growth_stage.not_in(list(STILL))).order_by(LivingProfileRow.thing_node_id))
    ):
        thing = await ctx.session.get(EntityRow, row.thing_node_id)
        if thing is None or thing.status is not EntityStatus.CANON or held(thing.id):
            continue
        await live(ctx, row, thing)
        kept += 1
    return kept


async def turn_away(ctx: TickContext, row: LivingProfileRow, thing: EntityRow) -> None:
    if row.bonded_to_node_id is None or "bonded_to_node_id" in row.locked or not refuses(ctx, row):
        return
    handler = await ctx.session.get(EntityRow, row.bonded_to_node_id)
    row.bonded_to_node_id = None
    await record(ctx, "living.turned", roles={IncidentRole.SUBJECT: thing.id, IncidentRole.OWNER: handler.id if handler else None}, facts={"bond": row.bond})


def refuses(ctx: TickContext, row: LivingProfileRow | None) -> bool:
    return row is not None and row.temperament is not None and row.bond < ctx.rules.living.refuse_bond
