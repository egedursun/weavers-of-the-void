from aerona.constants.units import PERCENT
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityType
from aerona.engine.context import TickContext
from aerona.engine.phase import Phase
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.prosperity import add_prosperity
from aerona.engine.primitives.queries import active_bonds, canon, living_entity
from aerona.engine.primitives.stats import set_stats, stat

GROWING_KEYS = ("wealth", "craft")


async def resource_economy(ctx: TickContext) -> None:
    rules = ctx.rules
    effects = rules.world_effects
    for resource in await canon(ctx.session, [EntityType.RESOURCE]):
        owners = []
        for bond in await active_bonds(ctx.session, [BondKind.OWNS], targets=[resource.id]):
            owner = await living_entity(ctx.session, bond.source_node_id)
            if owner is not None:
                owners.append(owner)
        abundance = stat(resource, "abundance") or 0
        if not owners or abundance < effects.resource_min_abundance:
            continue
        value = stat(resource, "value")
        gain = effects.resource_income + round_half_up((value if value is not None else effects.unknown_stat) / effects.resource_value_divisor)
        for owner in owners:
            add_prosperity(rules, owner, gain)
            for key in GROWING_KEYS:
                current = stat(owner, key)
                if current is not None:
                    set_stats(owner, **{key: clamp_int(current + gain, 0, PERCENT)})
        set_stats(resource, abundance=clamp_int(abundance - effects.resource_consumption * len(owners), 0, PERCENT))
        ctx.count("resources_worked")


async def resource_regeneration(ctx: TickContext) -> None:
    regen = ctx.rules.world_effects.resource_regen
    for resource in await canon(ctx.session, [EntityType.RESOURCE]):
        set_stats(resource, abundance=clamp_int((stat(resource, "abundance") or 0) + regen, 0, PERCENT))


ECONOMY_PHASES = (Phase("resource_economy", resource_economy),)
REGENERATION_PHASES = (Phase("resource_regeneration", resource_regeneration),)
PHASES = ECONOMY_PHASES + REGENERATION_PHASES
