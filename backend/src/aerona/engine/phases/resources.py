from aerona.constants.units import PERCENT
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityType
from aerona.engine.context import TickContext
from aerona.engine.environment.book import EnvironmentBook
from aerona.engine.phase import Phase
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.prosperity import add_prosperity
from aerona.engine.primitives.queries import active_bonds, canon, living_entity
from aerona.engine.primitives.stats import set_stats, stat
from aerona.rules.registry import Rules

GROWING_KEYS = ("wealth", "craft")


def deepest_layer(ground: RegionEnvironmentRow | None) -> str | None:
    if ground is None or not ground.mineral_layers:
        return None
    return max(sorted(ground.mineral_layers), key=lambda material: ground.mineral_layers[material])


def work_seam(rules: Rules, ground: RegionEnvironmentRow | None, owners: int) -> None:
    material = deepest_layer(ground)
    if ground is None or material is None:
        return
    settings = rules.land_use
    ground.mined = clamp_int(ground.mined + settings.mining_per_owner * owners, 0, PERCENT)
    layers = dict(ground.mineral_layers)
    layers[material] = max(0, layers[material] - settings.seam_depletion * owners)
    ground.mineral_layers = {key: value for key, value in layers.items() if value > 0}


async def resource_economy(ctx: TickContext) -> None:
    rules = ctx.rules
    effects = rules.world_effects
    book = await EnvironmentBook.load(ctx.session, rules, ctx.epoch)
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
        work_seam(rules, book.region_of(resource.id), len(owners))
        ctx.count("resources_worked")


def regrowth(rules: Rules, ground: RegionEnvironmentRow | None) -> int:
    regen = rules.world_effects.resource_regen
    material = deepest_layer(ground)
    if ground is None:
        return regen
    if material is None:
        return round_half_up(regen * rules.land_use.barren_regen_pct / PERCENT)
    return round_half_up(regen * (rules.land_use.barren_regen_pct + ground.mineral_layers[material]) / PERCENT)


async def resource_regeneration(ctx: TickContext) -> None:
    book = await EnvironmentBook.load(ctx.session, ctx.rules, ctx.epoch)
    for resource in await canon(ctx.session, [EntityType.RESOURCE]):
        gain = regrowth(ctx.rules, book.region_of(resource.id))
        set_stats(resource, abundance=clamp_int((stat(resource, "abundance") or 0) + gain, 0, PERCENT))


ECONOMY_PHASES = (Phase("resource_economy", resource_economy),)
REGENERATION_PHASES = (Phase("resource_regeneration", resource_regeneration),)
PHASES = ECONOMY_PHASES + REGENERATION_PHASES
