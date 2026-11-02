from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

from aerona.catalog.worlds import WORLD_TYPES
from aerona.constants.units import PERCENT
from aerona.domain.enums.intervention import Disaster
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
    ore_yield_pct: RuleValue | None = None
    disaster_pct: Mapping[Disaster, RuleValue] = field(default_factory=dict)


W = WorldType

WORLD_TYPE_MECHANICS: dict[WorldType, WorldTypeMechanics] = {
    mechanics.world_type: mechanics
    for mechanics in (
        WorldTypeMechanics(
            W.LAVA,
            disaster_pct={
                Disaster.EARTHQUAKE: lambda rules: rules.world_physics.lava_earthquake_pct,
            },
        ),
        WorldTypeMechanics(
            W.OCEAN,
            disaster_pct={
                Disaster.STORM: lambda rules: rules.world_physics.ocean_storm_pct,
            },
        ),
        WorldTypeMechanics(
            W.LIVING,
            disaster_pct={
                Disaster.EARTHQUAKE: lambda rules: rules.world_physics.living_earthquake_pct,
            },
        ),
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
            disaster_pct={
                Disaster.PLAGUE: lambda rules: rules.world_physics.corpse_world_plague_pct,
            },
        ),
        WorldTypeMechanics(
            W.FORGE,
            capacity_pct=lambda rules: rules.world_physics.forge_capacity,
            fertility_decay=lambda rules: rules.world_physics.forge_fertility_decay,
            forced_atmosphere=Atmosphere.DENSE,
            ore_yield_pct=lambda rules: rules.world_physics.forge_ore_yield,
            disaster_pct={
                Disaster.EARTHQUAKE: lambda rules: rules.world_physics.forge_earthquake_pct,
            },
        ),
        WorldTypeMechanics(
            W.SUPER_EARTH,
            capacity_pct=lambda rules: rules.world_physics.super_earth_capacity,
            forced_gravity=Gravity.HIGH,
            disaster_pct={
                Disaster.EARTHQUAKE: lambda rules: rules.world_physics.super_earth_earthquake_pct,
            },
        ),
        WorldTypeMechanics(
            W.ICE_GIANT,
            capacity_pct=lambda rules: rules.world_physics.ice_giant_capacity,
            disaster_pct={
                Disaster.STORM: lambda rules: rules.world_physics.ice_giant_storm_pct,
            },
        ),
        WorldTypeMechanics(
            W.HOT_GIANT,
            capacity_pct=lambda rules: rules.world_physics.hot_giant_capacity,
            route_danger=lambda rules: rules.world_physics.hot_giant_route_danger,
            disaster_pct={
                Disaster.STORM: lambda rules: rules.world_physics.hot_giant_storm_pct,
            },
        ),
        WorldTypeMechanics(
            W.IRON,
            capacity_pct=lambda rules: rules.world_physics.iron_capacity,
            forced_gravity=Gravity.HIGH,
            forced_atmosphere=Atmosphere.THIN,
            ore_yield_pct=lambda rules: rules.world_physics.iron_ore_yield,
            disaster_pct={
                Disaster.EARTHQUAKE: lambda rules: rules.world_physics.iron_earthquake_pct,
                Disaster.STORM: lambda rules: rules.world_physics.iron_storm_pct,
            },
        ),
        WorldTypeMechanics(
            W.CARBON,
            capacity_pct=lambda rules: rules.world_physics.carbon_capacity,
            ore_yield_pct=lambda rules: rules.world_physics.carbon_ore_yield,
            disaster_pct={
                Disaster.EARTHQUAKE: lambda rules: rules.world_physics.carbon_earthquake_pct,
            },
        ),
        WorldTypeMechanics(
            W.GREENHOUSE,
            capacity_pct=lambda rules: rules.world_physics.greenhouse_capacity,
            fertility_decay=lambda rules: rules.world_physics.greenhouse_fertility_decay,
            forced_atmosphere=Atmosphere.TOXIC,
            disaster_pct={
                Disaster.DROUGHT: lambda rules: rules.world_physics.greenhouse_drought_pct,
                Disaster.STORM: lambda rules: rules.world_physics.greenhouse_storm_pct,
            },
        ),
        WorldTypeMechanics(
            W.DWARF_PLANET,
            capacity_pct=lambda rules: rules.world_physics.dwarf_planet_capacity,
            hidden_route_method=TravelMethod.COSMIC_MOUNT,
            forced_gravity=Gravity.LOW,
            forced_atmosphere=Atmosphere.THIN,
            ore_yield_pct=lambda rules: rules.world_physics.dwarf_planet_ore_yield,
            disaster_pct={
                Disaster.STORM: lambda rules: rules.world_physics.dwarf_planet_storm_pct,
                Disaster.FLOOD: lambda rules: rules.world_physics.dwarf_planet_flood_pct,
            },
        ),
        WorldTypeMechanics(
            W.CHTHONIAN,
            capacity_pct=lambda rules: rules.world_physics.chthonian_capacity,
            forced_gravity=Gravity.HIGH,
            forced_atmosphere=Atmosphere.NONE,
            ore_yield_pct=lambda rules: rules.world_physics.chthonian_ore_yield,
            disaster_pct={
                Disaster.EARTHQUAKE: lambda rules: rules.world_physics.chthonian_earthquake_pct,
            },
        ),
        WorldTypeMechanics(
            W.HYCEAN,
            capacity_pct=lambda rules: rules.world_physics.hycean_capacity,
            forced_atmosphere=Atmosphere.DENSE,
            disaster_pct={
                Disaster.STORM: lambda rules: rules.world_physics.hycean_storm_pct,
                Disaster.FLOOD: lambda rules: rules.world_physics.hycean_flood_pct,
            },
        ),
        WorldTypeMechanics(
            W.JUNGLE,
            capacity_pct=lambda rules: rules.world_physics.jungle_capacity,
            disaster_pct={
                Disaster.PLAGUE: lambda rules: rules.world_physics.jungle_plague_pct,
                Disaster.FLOOD: lambda rules: rules.world_physics.jungle_flood_pct,
            },
        ),
        WorldTypeMechanics(
            W.FUNGAL,
            capacity_pct=lambda rules: rules.world_physics.fungal_capacity,
            sanity_erosion=lambda rules: rules.world_physics.fungal_sanity_erosion,
            disaster_pct={
                Disaster.PLAGUE: lambda rules: rules.world_physics.fungal_plague_pct,
            },
        ),
        WorldTypeMechanics(
            W.SHATTERED,
            capacity_pct=lambda rules: rules.world_physics.shattered_capacity,
            route_danger=lambda rules: rules.world_physics.shattered_route_danger,
            leak=lambda rules: rules.world_physics.shattered_leak,
            hidden_route_method=TravelMethod.COSMIC_MOUNT,
            forced_gravity=Gravity.LOW,
            ore_yield_pct=lambda rules: rules.world_physics.shattered_ore_yield,
            disaster_pct={
                Disaster.EARTHQUAKE: lambda rules: rules.world_physics.shattered_earthquake_pct,
            },
        ),
        WorldTypeMechanics(
            W.HOLLOW,
            capacity_pct=lambda rules: rules.world_physics.hollow_capacity,
            leak_repair=lambda rules: rules.world_physics.hollow_leak_repair,
            forced_gravity=Gravity.LOW,
            disaster_pct={
                Disaster.EARTHQUAKE: lambda rules: rules.world_physics.hollow_earthquake_pct,
            },
        ),
        WorldTypeMechanics(
            W.ICE_SHELL,
            capacity_pct=lambda rules: rules.world_physics.ice_shell_capacity,
            forced_gravity=Gravity.LOW,
            forced_atmosphere=Atmosphere.THIN,
            disaster_pct={
                Disaster.EARTHQUAKE: lambda rules: rules.world_physics.ice_shell_earthquake_pct,
                Disaster.STORM: lambda rules: rules.world_physics.ice_shell_storm_pct,
            },
        ),
        WorldTypeMechanics(
            W.METHANE,
            capacity_pct=lambda rules: rules.world_physics.methane_capacity,
            forced_gravity=Gravity.LOW,
            forced_atmosphere=Atmosphere.DENSE,
            disaster_pct={
                Disaster.FLOOD: lambda rules: rules.world_physics.methane_flood_pct,
            },
        ),
    )
}

DEFAULT_MECHANICS = WorldTypeMechanics(W.ORDINARY)


def mechanics_of(world_type: WorldType) -> WorldTypeMechanics:
    return WORLD_TYPE_MECHANICS.get(world_type, DEFAULT_MECHANICS)


def ore_yield_pct(rules: Rules, world_type: WorldType) -> int:
    value = mechanics_of(world_type).ore_yield_pct
    return value(rules) if value is not None else PERCENT


def disaster_pct(rules: Rules, world_type: WorldType, disaster: Disaster) -> int:
    if disaster is Disaster.EARTHQUAKE and WORLD_TYPES[world_type].artificial:
        return rules.world_physics.artificial_earthquake_pct
    value = mechanics_of(world_type).disaster_pct.get(disaster)
    return value(rules) if value is not None else PERCENT


def is_realm_of_dead(world_type: WorldType) -> bool:
    return WORLD_TYPES[world_type].realm_of_dead


def river_reaches(world_type: WorldType) -> bool:
    return is_realm_of_dead(world_type) or mechanics_of(world_type).hidden_route_method is TravelMethod.RIVER_OF_DEAD


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
