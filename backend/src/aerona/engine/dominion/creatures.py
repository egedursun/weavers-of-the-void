from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.commodities import FOOD_KINDS
from aerona.catalog.dominion import FEEDING_DEEDS, HARMFUL_DEEDS, HELPFUL_DEEDS
from aerona.constants.units import PERCENT
from aerona.core.random import SeededRandom
from aerona.db.tables.dominion import CreatureLessonRow, DivineCreatureRow, DominionRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.dominion import CreatureDeed, CreatureLesson
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus, EntityType
from aerona.domain.models.entity_stats import BeastStats
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.cosmos.features import add_stock
from aerona.engine.divine.standing import standing_row
from aerona.engine.dominion.core import patrons
from aerona.engine.ecology.control import NewBeast, create_beast
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.notes import note
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import canon
from aerona.engine.primitives.stats import has_stat, shift_stat

DEEDS = tuple(CreatureDeed)
START_WEIGHT = 10
CREATURE_POWER = 6


@dataclass
class CreatureTally:
    acted: int = 0
    helped: int = 0
    harmed: int = 0
    drifted: int = 0


def default_weights() -> dict[str, int]:
    return {deed.value: START_WEIGHT for deed in DEEDS}


async def raise_creature(ctx: TickContext, god_id: int, *, name: str, description: str, home_id: int) -> DivineCreatureRow:
    beast = await create_beast(
        ctx,
        NewBeast(name=name, description=description, stats=BeastStats(strength=70, cunning=50, danger=50), lair_id=home_id, power=CREATURE_POWER),
    )
    row = DivineCreatureRow(creature_entity_id=beast.id, god_node_id=god_id, weights=default_weights(), since_epoch=ctx.epoch, locked=[])
    ctx.session.add(row)
    await ctx.session.flush()
    return row


def taught(rules_shift: int, weights: dict[str, int], deed: CreatureDeed, lesson: CreatureLesson, *, low: int, high: int) -> dict[str, int]:
    step = rules_shift if lesson is CreatureLesson.REWARD else -rules_shift
    current = dict(weights) or default_weights()
    current[deed.value] = clamp_int(current.get(deed.value, START_WEIGHT) + step, low, high)
    return current


async def teach(ctx: TickContext, row: DivineCreatureRow, deed: CreatureDeed, lesson: CreatureLesson) -> CreatureLessonRow:
    table = ctx.rules.divine_creatures
    if "weights" not in row.locked:
        row.weights = taught(table.lesson_shift, row.weights, deed, lesson, low=table.weight_min, high=table.weight_max)
    row.neglect_epochs = 0
    record = CreatureLessonRow(creature_entity_id=row.creature_entity_id, deed=deed, lesson=lesson, strength=table.lesson_shift, epoch=ctx.epoch)
    ctx.session.add(record)
    await ctx.session.flush()
    return record


def choose(ctx: TickContext, row: DivineCreatureRow) -> CreatureDeed:
    table = ctx.rules.divine_creatures
    if row.neglect_epochs >= table.neglect_epochs and row.hunger >= table.hunger_pull:
        return CreatureDeed.HUNT_FOLK
    weights = row.weights or default_weights()
    return ctx.rng(f"creature.{row.creature_entity_id}.{ctx.epoch}").weighted(list(DEEDS), [float(weights.get(deed.value, START_WEIGHT)) for deed in DEEDS])


async def folk_near(ctx: TickContext, atlas: RegionAtlas, region: int | None) -> list[EntityRow]:
    return [mortal for mortal in await canon(ctx.session, [EntityType.MORTAL]) if atlas.top_region(mortal.id) == region and not held(mortal.id)]


async def communities_near(ctx: TickContext, atlas: RegionAtlas, region: int | None) -> list[EntityRow]:
    return [community for community in await canon(ctx.session, list(COMMUNITY_TYPES)) if atlas.top_region(community.id) == region and not held(community.id)]


async def sway(ctx: TickContext, community_id: int, god_id: int, *, love: int = 0, fear: int = 0) -> None:
    if held(community_id, god_id):
        return
    standing = await standing_row(ctx, community_id, god_id)
    if love and "love" not in standing.locked:
        standing.love = clamp_int(standing.love + love, 0, PERCENT)
    if fear and "fear" not in standing.locked:
        standing.fear = clamp_int(standing.fear + fear, 0, PERCENT)


async def presence(ctx: TickContext, god_id: int, region: int | None) -> None:
    if region is None or held(god_id, region):
        return
    row = await ctx.session.get(DominionRow, (god_id, region))
    if row is None:
        row = DominionRow(god_node_id=god_id, region_entity_id=region, epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    if "strength" not in row.locked:
        row.strength = clamp_int(row.strength + ctx.rules.divine_creatures.dominion_per_deed, 0, PERCENT)


@dataclass
class Scene:
    ctx: TickContext
    atlas: RegionAtlas
    beast: EntityRow
    god: int
    region: int | None
    folk: list[EntityRow]
    towns: list[EntityRow]
    faithful: dict[int, int]

    def rng(self) -> SeededRandom:
        return self.ctx.rng(f"creature.deed.{self.beast.id}.{self.ctx.epoch}")


async def hunt(scene: Scene) -> str | None:
    table = scene.ctx.rules.divine_creatures
    if not scene.folk:
        return None
    victim = scene.rng().pick(scene.folk)
    harm = Harm(table.harm, HarmCause.MONSTER, f"was taken by {scene.beast.name}", source_node_id=scene.beast.id, killer_id=scene.beast.id)
    await apply_hits(scene.ctx, victim, harm)
    for town in scene.towns:
        await sway(scene.ctx, town.id, scene.god, fear=table.fear_per_deed)
    return f"{scene.beast.name} hunted {victim.name}"


async def strike(scene: Scene) -> str | None:
    table = scene.ctx.rules.divine_creatures
    foes = [mortal for mortal in scene.folk if scene.faithful.get(mortal.id) not in {None, scene.god}]
    if not foes:
        return None
    victim = scene.rng().pick(foes)
    harm = Harm(table.harm, HarmCause.GOD, f"was struck down by {scene.beast.name}", source_node_id=scene.beast.id, killer_id=scene.beast.id)
    await apply_hits(scene.ctx, victim, harm)
    return f"{scene.beast.name} struck at {victim.name}, who keeps another faith"


async def tend(scene: Scene) -> str | None:
    table = scene.ctx.rules.divine_creatures
    if not scene.towns:
        return None
    town = scene.rng().pick(scene.towns)
    await add_stock(scene.ctx, town, FOOD_KINDS[0], table.tend_food)
    await sway(scene.ctx, town.id, scene.god, love=table.love_per_deed)
    return f"{scene.beast.name} tended the fields of {town.name}"


async def heal(scene: Scene) -> str | None:
    table = scene.ctx.rules.divine_creatures
    if not scene.folk:
        return None
    patient = scene.rng().pick(scene.folk)
    if has_stat(patient, "hp"):
        shift_stat(patient, "hp", table.heal)
    for town in scene.towns:
        await sway(scene.ctx, town.id, scene.god, love=table.love_per_deed)
    return f"{scene.beast.name} tended {patient.name}"


async def guard(scene: Scene) -> str | None:
    table = scene.ctx.rules.divine_creatures
    for town in scene.towns:
        await sway(scene.ctx, town.id, scene.god, love=table.love_per_deed // 2, fear=table.fear_per_deed // 2)
    return f"{scene.beast.name} kept watch over the holy places"


async def wreck(scene: Scene) -> str | None:
    table = scene.ctx.rules.divine_creatures
    works = await scene.ctx.session.execute(
        select(EntityRow, StructureProfileRow)
        .join(StructureProfileRow, StructureProfileRow.structure_entity_id == EntityRow.id)
        .where(EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    near = [(work, profile) for work, profile in works if scene.atlas.top_region(work.id) == scene.region and not held(work.id)]
    if not near:
        return None
    work, profile = scene.rng().pick(near)
    if "condition" not in profile.locked:
        profile.condition = clamp_int(profile.condition - table.wreck, 0, PERCENT)
    for town in scene.towns:
        await sway(scene.ctx, town.id, scene.god, fear=table.fear_per_deed)
    return f"{scene.beast.name} wrecked {work.name}"


async def wander(scene: Scene) -> str | None:
    neighbours = scene.atlas.neighbour_regions(scene.region) if scene.region is not None else []
    if neighbours:
        scene.beast.location_id = scene.rng().pick(neighbours)
    return None


async def rest(scene: Scene) -> str | None:
    return None


DEED_ACTS: dict[CreatureDeed, Callable[[Scene], Awaitable[str | None]]] = {
    CreatureDeed.HUNT_FOLK: hunt,
    CreatureDeed.STRIKE_FOES: strike,
    CreatureDeed.TEND_FIELDS: tend,
    CreatureDeed.HEAL_SICK: heal,
    CreatureDeed.GUARD_HOLY_SITES: guard,
    CreatureDeed.WRECK_WORKS: wreck,
    CreatureDeed.WANDER: wander,
    CreatureDeed.REST: rest,
}


async def perform(ctx: TickContext, atlas: RegionAtlas, beast: EntityRow, row: DivineCreatureRow, faithful: dict[int, int]) -> str | None:
    region = atlas.top_region(beast.id)
    scene = Scene(ctx, atlas, beast, row.god_node_id, region, await folk_near(ctx, atlas, region), await communities_near(ctx, atlas, region), faithful)
    return await DEED_ACTS[row.last_deed or CreatureDeed.REST](scene)


async def act_creatures(ctx: TickContext, tally: CreatureTally) -> None:
    table = ctx.rules.divine_creatures
    atlas = await RegionAtlas.load(ctx.session)
    faithful = await patrons(ctx)
    for row in list(await ctx.session.scalars(select(DivineCreatureRow).order_by(DivineCreatureRow.creature_entity_id))):
        beast = await ctx.session.get(EntityRow, row.creature_entity_id)
        if beast is None or beast.status is not EntityStatus.CANON or held(beast.id, row.god_node_id):
            continue
        deed = choose(ctx, row)
        if row.neglect_epochs >= table.neglect_epochs:
            tally.drifted += 1
        if "last_deed" not in row.locked:
            row.last_deed = deed
        told = await perform(ctx, atlas, beast, row, faithful)
        if "hunger" not in row.locked:
            row.hunger = 0 if deed in FEEDING_DEEDS else clamp_int(row.hunger + table.hunger_gain, 0, PERCENT)
        if "neglect_epochs" not in row.locked:
            row.neglect_epochs += 1
        row.deeds += 1
        tally.acted += 1
        tally.helped += deed in HELPFUL_DEEDS
        tally.harmed += deed in HARMFUL_DEEDS
        await presence(ctx, row.god_node_id, atlas.top_region(beast.id))
        if told:
            await note(ctx, f"{told}.", key=f"dominion.creature_{deed.value}", ids=[beast.id, row.god_node_id])
    await ctx.session.flush()
