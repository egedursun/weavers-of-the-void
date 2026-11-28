from aerona.constants.units import PERCENT
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import ConditionKind, HarmCause
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.environment import ScarKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.society import KnowledgeBranch
from aerona.engine.body.conditions import end_condition
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.environment.book import add_scar, region_environment
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.lifecycle.wounds import WoundOutcome, apply_hits
from aerona.engine.phase import Phase
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import active_bonds, add_flag, canon, has_flag, living_entity, remove_flag
from aerona.engine.primitives.stats import headcount_bounds, set_stats, stat
from aerona.engine.recording.record import record

HEADCOUNT_KEYS = ("population", "followers")
DECAYING_KEYS = ("prosperity", "fertility", "abundance", "strength", "wealth")
BLIGHTABLE = frozenset({EntityType.REGION, EntityType.PLACE})
CURSE_DEATH = "wasted away under the curse and died"


async def cursed(ctx: TickContext) -> list[EntityRow]:
    return await EntityRepository(ctx.session).with_flag(EntityFlag.CURSED)


async def curser_of(ctx: TickContext, entity: EntityRow) -> int | None:
    bonds = await active_bonds(ctx.session, [BondKind.CURSED], targets=[entity.id])
    return bonds[-1].source_node_id if bonds else None


@reads(
    "item.protection",
    "mortal.age",
    "mortal.agility",
    "mortal.charisma",
    "mortal.endurance",
    "mortal.hp",
    "mortal.intellect",
    "mortal.lifespan",
    "mortal.strength",
    "mortal.willpower",
    "people.population",
    "people.prosperity",
    "people.wealth",
    "settlement.population",
    "settlement.prosperity",
    "settlement.wealth",
    "table.assistive_aids",
    "table.augment_effects",
    "table.augments",
    "table.bodies",
    "table.body_customs",
    "table.bonds",
    "table.charms",
    "table.conditions",
    "table.creature_anatomy",
    "table.cult_tenets",
    "table.culture_values",
    "table.entities",
    "table.entity_flags",
    "table.entity_tags",
    "table.genomes",
    "table.holder_levels",
    "table.incubating_ideas",
    "table.injuries",
    "table.item_profiles",
    "table.mind_attributes",
    "table.mortal_equipment",
    "table.mortal_profiles",
    "table.node_births",
    "table.nodes",
    "table.nutrition_scores",
    "table.prostheses",
    "table.sense_profiles",
    "table.traits",
)
@writes(
    "mortal.hp",
    "mortal.strength",
    "people.population",
    "settlement.population",
    "settlement.prosperity",
    "settlement.wealth",
    "table.bodies",
    "table.body_customs",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.injuries",
    "table.mortal_profiles",
)
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
        if entity.entity_type in BLIGHTABLE:
            ground = await region_environment(ctx.session, entity.id)
            if ground is not None:
                add_scar(ground, ScarKind.BLIGHTED, rules.scars.curse_blight_depth)
        ctx.count("cursed_decay")
        if entity.entity_type is EntityType.MORTAL and rules.world_engine.curse_hp_loss > 0:
            curser = await curser_of(ctx, entity)
            await apply_hits(ctx, entity, Harm(rules.world_engine.curse_hp_loss, HarmCause.CURSE, CURSE_DEATH, source_node_id=curser, killer_id=curser))


@reads(
    "item.protection",
    "mortal.age",
    "mortal.agility",
    "mortal.charisma",
    "mortal.endurance",
    "mortal.hp",
    "mortal.intellect",
    "mortal.lifespan",
    "mortal.strength",
    "mortal.willpower",
    "table.augment_effects",
    "table.augments",
    "table.bonds",
    "table.conditions",
    "table.creator",
    "table.cult_tenets",
    "table.dimensions",
    "table.entities",
    "table.entity_flags",
    "table.entity_tags",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.holder_levels",
    "table.incident_participants",
    "table.incidents",
    "table.injuries",
    "table.item_profiles",
    "table.node_births",
    "table.nodes",
    "table.polity_profiles",
    "table.prostheses",
    "table.sons",
    "table.stars",
    "table.state_changes",
    "table.worlds",
)
@writes(
    "table.bodies",
    "table.body_customs",
    "table.chronicle",
    "table.chronicle_entities",
    "table.conditions",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_steps",
    "table.incidents",
)
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
    if entity.entity_type is EntityType.MORTAL:
        await end_condition(ctx, entity, ConditionKind.ENDLESS_HUNGER)
    await record(ctx, "curses.lifted", roles={IncidentRole.SUBJECT: entity.id})
    return True


@reads(
    "item.curse",
    "item.protection",
    "mortal.age",
    "mortal.agility",
    "mortal.charisma",
    "mortal.creativity",
    "mortal.endurance",
    "mortal.hp",
    "mortal.intellect",
    "mortal.lifespan",
    "mortal.perception",
    "mortal.strength",
    "mortal.willpower",
    "mortal.wisdom",
    "people.prosperity",
    "settlement.defense",
    "settlement.prosperity",
    "table.afflictions",
    "table.armies",
    "table.army_officers",
    "table.assistive_aids",
    "table.augment_effects",
    "table.augments",
    "table.avatars",
    "table.bodies",
    "table.body_customs",
    "table.bonds",
    "table.charms",
    "table.conditions",
    "table.cosmos",
    "table.creator",
    "table.creature_anatomy",
    "table.cult_tenets",
    "table.culture_values",
    "table.deep_passages",
    "table.dimensional_events",
    "table.dimensions",
    "table.divine_wounds",
    "table.entities",
    "table.entity_flags",
    "table.entity_tags",
    "table.foreign_gods",
    "table.galactic_structures",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.genomes",
    "table.grave_goods",
    "table.holder_levels",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_steps",
    "table.incidents",
    "table.incubating_ideas",
    "table.injuries",
    "table.insurance_policies",
    "table.insurers",
    "table.item_profiles",
    "table.marriages",
    "table.memories",
    "table.mind_attributes",
    "table.mind_profiles",
    "table.minds",
    "table.mortal_equipment",
    "table.mortal_profiles",
    "table.natural_law_profiles",
    "table.node_births",
    "table.node_materials",
    "table.nodes",
    "table.nutrition_scores",
    "table.passions",
    "table.polity_members",
    "table.prostheses",
    "table.routes",
    "table.sense_profiles",
    "table.sons",
    "table.stars",
    "table.state_changes",
    "table.tradition_profiles",
    "table.traits",
    "table.wills",
    "table.world_domain_hooks",
    "table.world_materials",
    "table.worlds",
)
@writes(
    "mortal.death_year",
    "mortal.hp",
    "settlement.defense",
    "settlement.prosperity",
    "table.bodies",
    "table.body_customs",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.entity_flags",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_steps",
    "table.incidents",
    "table.injuries",
    "table.memories",
    "table.mortal_profiles",
    "table.node_births",
    "table.sons",
)
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
        if owner is None or held(owner.id, item.id):
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
            harm = Harm(hp_damage, HarmCause.CURSE, f"gave up their life to the curse of {item.name}", source_node_id=item.id)
            if (await apply_hits(ctx, owner, harm)).outcome is WoundOutcome.DIED:
                continue
        contagious = owner.status is EntityStatus.CANON and rng.chance(rules.world_engine.cursed_item_contagion_chance)
        if contagious and not await has_flag(ctx.session, owner.id, EntityFlag.CURSED):
            await add_flag(ctx.session, owner.id, EntityFlag.CURSED, ctx.epoch)
            await record(ctx, "curses.spread", roles={IncidentRole.SUBJECT: item.id, IncidentRole.OWNER: owner.id})


DECAY_PHASES = (Phase("curse_decay", curse_decay),)
LIFT_PHASES = (Phase("curse_lifting", lift_curses), Phase("cursed_items", cursed_items))
PHASES = DECAY_PHASES + LIFT_PHASES
