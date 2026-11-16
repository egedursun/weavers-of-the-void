from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import unheld
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.engine.context import TickContext
from aerona.engine.ecology.foodweb import appetites, raid_chance, raid_herds
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.phases.heroism import encounter, monsters_of
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import active_bonds, canon, connect, directed_bond, living_entity
from aerona.engine.primitives.stats import set_stats, stat
from aerona.rules.registry import Rules


def raid_loss(rules: Rules, monster: EntityRow) -> float:
    danger = stat(monster, "danger")
    return (danger if danger is not None else rules.world_effects.raid_default_danger) / rules.world_engine.raid_loss_divisor


async def raid(ctx: TickContext, monster: EntityRow, settlement: EntityRow) -> None:
    rules = ctx.rules
    effects = rules.world_effects
    limits = rules.limits
    for bond in await active_bonds(ctx.session, [BondKind.PROTECTS], targets=[settlement.id]):
        protector = await living_entity(ctx.session, bond.source_node_id)
        if protector is not None and protector.entity_type is EntityType.MORTAL:
            await encounter(ctx, protector, monster, f"while protecting {settlement.name}")
            return
    herds = await raid_herds(ctx, monster, settlement)
    if herds > 0:
        if await directed_bond(ctx.session, monster.id, settlement.id, BondKind.HUNTS) is None:
            await connect(ctx.session, monster.id, settlement.id, BondKind.HUNTS, ctx.epoch, description="raids its herds")
        ctx.count("herd_raids")
        await note(
            ctx,
            f"{monster.name} fell on the herds of {settlement.name} and carried off {herds} head.",
            key="monsters.herd_raid",
            ids=[monster.id, settlement.id],
        )
        return
    loss = raid_loss(rules, monster)
    population = stat(settlement, "population")
    prosperity = stat(settlement, "prosperity")
    defense = stat(settlement, "defense")
    set_stats(
        settlement,
        population=clamp_int((population or effects.raid_default_population) * (1 - loss), limits.population_floor, limits.settlement_population_cap),
        prosperity=clamp_int((prosperity if prosperity is not None else effects.unknown_prosperity) - effects.raid_prosperity_loss, 0, PERCENT),
        defense=clamp_int((defense if defense is not None else effects.unknown_stat) + effects.raid_defense_gain, 0, PERCENT),
    )
    if await directed_bond(ctx.session, monster.id, settlement.id, BondKind.HUNTS) is None:
        await connect(ctx.session, monster.id, settlement.id, BondKind.HUNTS, ctx.epoch, description="raids")
    ctx.count("raids")
    await note(
        ctx,
        f"{monster.name} raided {settlement.name}; {round_half_up(loss * PERCENT)}% of the population was lost.",
        key="monsters.raid",
        ids=[monster.id, settlement.id],
    )


@reads(
    "cult.zeal",
    "mortal.age",
    "mortal.agility",
    "mortal.charisma",
    "mortal.hp",
    "mortal.intellect",
    "mortal.lifespan",
    "mortal.strength",
    "settlement.defense",
    "settlement.population",
    "settlement.prosperity",
    "species.agility",
    "species.danger",
    "species.strength",
    "table.avatars",
    "table.bodies",
    "table.bonds",
    "table.community_societies",
    "table.community_stocks",
    "table.cosmos",
    "table.creator_taboos",
    "table.creature_anatomy",
    "table.creature_attacks",
    "table.crime_cases",
    "table.cult_doctrines",
    "table.cult_offices",
    "table.culture_ethics",
    "table.culture_values",
    "table.designated_heirs",
    "table.divine_wounds",
    "table.doctrine_sacraments",
    "table.entity_flags",
    "table.entity_traits",
    "table.epoch_year_cursors",
    "table.geasa",
    "table.goods_flows",
    "table.griefs",
    "table.herds",
    "table.holder_levels",
    "table.house_members",
    "table.house_profiles",
    "table.incident_participants",
    "table.incorporeal_rights",
    "table.injuries",
    "table.kinship_systems",
    "table.language_profiles",
    "table.law_jurisdictions",
    "table.lexemes",
    "table.marriages",
    "table.memories",
    "table.mind_facets",
    "table.minds",
    "table.mortal_profiles",
    "table.name_registry",
    "table.nodes",
    "table.outbreaks",
    "table.passions",
    "table.people_biology",
    "table.people_culture",
    "table.personality_values",
    "table.polity_members",
    "table.routes",
    "table.sacraments",
    "table.skills",
    "table.species_profiles",
    "table.species_ranges",
    "table.spirit_profiles",
    "table.tradition_profiles",
    "table.traits",
    "table.transform_prospects",
    "table.world_domain_hooks",
    "table.world_maps",
)
@writes(
    "mortal.charisma",
    "mortal.death_year",
    "settlement.defense",
    "settlement.population",
    "settlement.prosperity",
    "species.danger",
    "table.bodies",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_stocks",
    "table.creature_attacks",
    "table.entities",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.goods_flows",
    "table.griefs",
    "table.house_profiles",
    "table.incident_participants",
    "table.incidents",
    "table.injuries",
    "table.marriages",
    "table.memories",
    "table.mind_facets",
    "table.mortal_profiles",
    "table.name_registry",
    "table.personality_values",
    "table.sacraments",
    "table.sons",
    "table.spirit_profiles",
    "table.thoughts",
    "table.transformations",
)
async def monster_raids(ctx: TickContext) -> None:
    rules = ctx.rules
    rng = ctx.rng()
    atlas = await RegionAtlas.load(ctx.session)
    settlements = await canon(ctx.session, [EntityType.SETTLEMENT])
    monsters = await monsters_of(ctx, beasts=False)
    hunger = await appetites(ctx, monsters, adjust=False)
    for monster in unheld(monsters):
        if monster.status is not EntityStatus.CANON:
            continue
        targets = unheld(settlement for settlement in settlements if atlas.distance(monster.id, settlement.id) <= rules.world_effects.raid_distance)
        if not targets or not rng.probability(min(1.0, await raid_chance(ctx, monster, hunger))):
            continue
        target = rng.pick(targets)
        if target.status is EntityStatus.CANON:
            await raid(ctx, monster, target)


PHASES = (Phase("monster_raids", monster_raids),)
