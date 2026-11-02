from collections.abc import Callable
from dataclasses import dataclass

from aerona.catalog.worlds import WORLD_TYPES
from aerona.domain.enums.travel import TravelMethod
from aerona.domain.enums.world import Atmosphere, Gravity, WorldType
from aerona.rules.registry import Rules

RuleValue = Callable[[Rules], int]


def _zero(rules: Rules) -> int:
    return 0


@dataclass(frozen=True)
class WorldTypeMechanics:
    world_type: WorldType
    capacity_pct: RuleValue | None = None
    route_danger: RuleValue = _zero
    leak: RuleValue = _zero
    leak_repair: RuleValue = _zero
    sanity_erosion: RuleValue = _zero
    fertility_decay: RuleValue = _zero
    hidden_route_method: TravelMethod | None = None
    forced_gravity: Gravity | None = None
    forced_atmosphere: Atmosphere | None = None
    drifts: bool = False


W = WorldType

WORLD_TYPE_MECHANICS: dict[WorldType, WorldTypeMechanics] = {
    mechanics.world_type: mechanics
    for mechanics in (
        WorldTypeMechanics(
            W.RINGED,
            capacity_pct=lambda rules: rules.world_physics.ringed_capacity,
            route_danger=lambda rules: rules.world_physics.ringed_route_danger,
            hidden_route_method=TravelMethod.LIGHT_SAIL,
        ),
        WorldTypeMechanics(
            W.ASTEROID_BELT,
            capacity_pct=lambda rules: rules.world_physics.asteroid_belt_capacity,
            route_danger=lambda rules: rules.world_physics.asteroid_belt_route_danger,
            hidden_route_method=TravelMethod.COSMIC_MOUNT,
            forced_gravity=Gravity.LOW,
        ),
        WorldTypeMechanics(W.TIDALLY_LOCKED, capacity_pct=lambda rules: rules.world_physics.tidally_locked_capacity),
        WorldTypeMechanics(
            W.VOID_POCKET,
            capacity_pct=lambda rules: rules.world_physics.void_pocket_capacity,
            leak=lambda rules: rules.world_physics.void_pocket_leak,
            sanity_erosion=lambda rules: rules.world_physics.void_pocket_sanity_erosion,
            hidden_route_method=TravelMethod.SWALLOWED,
            forced_atmosphere=Atmosphere.THIN,
        ),
        WorldTypeMechanics(
            W.GODS_PALACE,
            capacity_pct=lambda rules: rules.world_physics.gods_palace_capacity,
            leak_repair=lambda rules: rules.world_physics.gods_palace_leak_repair,
            hidden_route_method=TravelMethod.DIVINE_BRIDGE,
            forced_atmosphere=Atmosphere.NORMAL,
        ),
        WorldTypeMechanics(
            W.GENERATION_SHIP,
            capacity_pct=lambda rules: rules.world_physics.generation_ship_capacity,
            hidden_route_method=TravelMethod.LIGHT_SAIL,
            forced_atmosphere=Atmosphere.NORMAL,
            drifts=True,
        ),
        WorldTypeMechanics(
            W.CORPSE_WORLD,
            capacity_pct=lambda rules: rules.world_physics.corpse_world_capacity,
            leak=lambda rules: rules.world_physics.corpse_world_leak,
            fertility_decay=lambda rules: rules.world_physics.corpse_world_fertility_decay,
            hidden_route_method=TravelMethod.RIVER_OF_DEAD,
        ),
    )
}

DEFAULT_MECHANICS = WorldTypeMechanics(W.ORDINARY)


def mechanics_of(world_type: WorldType) -> WorldTypeMechanics:
    return WORLD_TYPE_MECHANICS.get(world_type, DEFAULT_MECHANICS)


def is_realm_of_dead(world_type: WorldType) -> bool:
    return WORLD_TYPES[world_type].realm_of_dead


def is_living(world_type: WorldType) -> bool:
    return WORLD_TYPES[world_type].living


def is_mirror(world_type: WorldType) -> bool:
    return WORLD_TYPES[world_type].mirror


def hidden_route_method(first: WorldType, second: WorldType) -> TravelMethod:
    if is_realm_of_dead(first) or is_realm_of_dead(second):
        return TravelMethod.RIVER_OF_DEAD
    for world_type in (first, second):
        methods = sorted(WORLD_TYPES[world_type].hidden_route_methods)
        if methods:
            return methods[0]
    for world_type in (first, second):
        method = mechanics_of(world_type).hidden_route_method
        if method is not None:
            return method
    return TravelMethod.ANCIENT_GATE
