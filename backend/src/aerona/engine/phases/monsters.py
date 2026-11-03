from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.engine.context import TickContext
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
    "mortal.age",
    "mortal.agility",
    "mortal.charisma",
    "mortal.intellect",
    "mortal.lifespan",
    "mortal.strength",
    "settlement.defense",
    "settlement.population",
    "settlement.prosperity",
    "species.agility",
    "species.danger",
    "species.strength",
    "table.bodies",
    "table.bonds",
    "table.community_societies",
    "table.cosmos",
    "table.designated_heirs",
    "table.entity_flags",
    "table.entity_traits",
    "table.epoch_year_cursors",
    "table.language_profiles",
    "table.lexemes",
    "table.memories",
    "table.minds",
    "table.name_registry",
    "table.nodes",
    "table.routes",
    "table.skills",
    "table.traits",
    "table.world_maps",
)
@writes(
    "mortal.charisma",
    "mortal.death_year",
    "settlement.defense",
    "settlement.population",
    "settlement.prosperity",
    "species.danger",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
    "table.injuries",
    "table.memories",
    "table.name_registry",
    "table.sons",
)
@reads(
    "mortal.age",
    "mortal.agility",
    "mortal.charisma",
    "mortal.intellect",
    "mortal.lifespan",
    "mortal.strength",
    "settlement.defense",
    "settlement.population",
    "settlement.prosperity",
    "species.agility",
    "species.danger",
    "species.strength",
)
@writes("mortal.charisma", "mortal.death_year", "settlement.defense", "settlement.population", "settlement.prosperity", "species.danger")
async def monster_raids(ctx: TickContext) -> None:
    rules = ctx.rules
    rng = ctx.rng()
    atlas = await RegionAtlas.load(ctx.session)
    settlements = await canon(ctx.session, [EntityType.SETTLEMENT])
    for monster in await monsters_of(ctx):
        if monster.status is not EntityStatus.CANON:
            continue
        targets = [settlement for settlement in settlements if atlas.distance(monster.id, settlement.id) <= rules.world_effects.raid_distance]
        if not targets or not rng.probability((stat(monster, "danger") or 0) / rules.world_engine.raid_danger_divisor):
            continue
        target = rng.pick(targets)
        if target.status is EntityStatus.CANON:
            await raid(ctx, monster, target)


PHASES = (Phase("monster_raids", monster_raids),)
