from aerona.constants.units import PERCENT
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.society import KnowledgeBranch
from aerona.engine.context import TickContext
from aerona.engine.lifecycle.wounds import WoundOutcome, wound
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import active_bonds, add_flag, canon, has_flag, living_entity, remove_flag
from aerona.engine.primitives.stats import headcount_bounds, set_stats, stat

HEADCOUNT_KEYS = ("population", "followers")
DECAYING_KEYS = ("prosperity", "fertility", "abundance", "strength", "wealth")
CURSE_DEATH = "melted away under the curse and died"


async def cursed(ctx: TickContext) -> list[EntityRow]:
    return await EntityRepository(ctx.session).with_flag(EntityFlag.CURSED)


async def curser_of(ctx: TickContext, entity: EntityRow) -> int | None:
    bonds = await active_bonds(ctx.session, [BondKind.CURSED], targets=[entity.id])
    return bonds[-1].source_node_id if bonds else None


async def curse_decay(ctx: TickContext) -> None:
    rules = ctx.rules
    effects = rules.world_effects
    for entity in await cursed(ctx):
        floor, cap = headcount_bounds(rules, entity)
        updates: dict[str, int | None] = {}
        for key in HEADCOUNT_KEYS:
            value = stat(entity, key)
            if value is not None:
                updates[key] = clamp_int(value * effects.curse_population_kept_pct / PERCENT, max(1, floor if key == "population" else 1), cap)
        for key in DECAYING_KEYS:
            value = stat(entity, key)
            if value is not None:
                updates[key] = clamp_int(value - effects.curse_stat_loss, 0, PERCENT)
        set_stats(entity, **updates)
        ctx.count("cursed_decay")
        if entity.entity_type is EntityType.MORTAL and rules.world_engine.curse_hp_loss > 0:
            await wound(ctx, entity, rules.world_engine.curse_hp_loss, cause=CURSE_DEATH, killer_id=await curser_of(ctx, entity))


async def lift_curses(ctx: TickContext) -> None:
    engine = ctx.rules.world_engine
    rng = ctx.rng()
    knowledge = await KnowledgeMap.load(ctx.session)
    for entity in await cursed(ctx):
        chance = engine.curse_lift_chance
        chance += engine.curse_magic_bonus_pct if knowledge.knows(entity.id, KnowledgeBranch.MAGIC) else 0
        chance += engine.curse_medicine_bonus_pct if knowledge.knows(entity.id, KnowledgeBranch.MEDICINE) else 0
        if rng.chance(chance):
            await lift_curse(ctx, entity)


async def lift_curse(ctx: TickContext, entity: EntityRow) -> bool:
    if not await remove_flag(ctx.session, entity.id, EntityFlag.CURSED):
        return False
    await note(ctx, f"The curse upon {entity.name} was lifted.", key="curses.lifted", ids=[entity.id])
    return True


async def cursed_items(ctx: TickContext) -> None:
    rules = ctx.rules
    effects = rules.world_effects
    rng = ctx.rng()
    for item in await canon(ctx.session, [EntityType.ITEM]):
        curse = stat(item, "curse") or 0
        if curse < effects.item_curse_threshold:
            continue
        owners = await active_bonds(ctx.session, [BondKind.OWNS], targets=[item.id])
        owner = await living_entity(ctx.session, owners[0].source_node_id) if owners else None
        if owner is None:
            continue
        hp_damage = round_half_up(curse / effects.item_curse_hp_divisor)
        stat_damage = round_half_up(curse / effects.item_curse_stat_divisor)
        hp = stat(owner, "hp")
        if hp is not None and owner.entity_type is not EntityType.MORTAL:
            set_stats(owner, hp=clamp_int(hp - hp_damage, 1, rules.limits.hp_cap))
        for key in ("prosperity", "defense"):
            value = stat(owner, key)
            if value is not None:
                set_stats(owner, **{key: clamp_int(value - stat_damage, 0, PERCENT)})
        if owner.entity_type is EntityType.MORTAL and hp is not None:
            outcome = await wound(ctx, owner, hp_damage, cause=f"gave up their life to the curse of {item.name}")
            if outcome is WoundOutcome.DIED:
                continue
        contagious = owner.status is EntityStatus.CANON and rng.chance(rules.world_engine.cursed_item_contagion_chance)
        if contagious and not await has_flag(ctx.session, owner.id, EntityFlag.CURSED):
            await add_flag(ctx.session, owner.id, EntityFlag.CURSED, ctx.epoch)
            await note(ctx, f"The curse of {item.name} spread to its owner {owner.name}.", key="curses.spread", ids=[item.id, owner.id])


DECAY_PHASES = (Phase("curse_decay", curse_decay),)
LIFT_PHASES = (Phase("curse_lifting", lift_curses), Phase("cursed_items", cursed_items))
PHASES = DECAY_PHASES + LIFT_PHASES
