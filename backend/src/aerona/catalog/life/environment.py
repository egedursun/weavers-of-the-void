from collections.abc import Callable

from aerona.domain.enums.environment import SoilKind, TerrainKind
from aerona.domain.enums.happening import LandAct
from aerona.domain.enums.world import WorldType
from aerona.rules.registry import Rules

WORLD_TEMPERATURE: dict[WorldType, Callable[[Rules], int]] = {
    WorldType.ORDINARY: lambda rules: rules.environment.temperature_ordinary,
    WorldType.OCEAN: lambda rules: rules.environment.temperature_ocean,
    WorldType.SAND: lambda rules: rules.environment.temperature_sand,
    WorldType.ICE: lambda rules: rules.environment.temperature_ice,
    WorldType.LAVA: lambda rules: rules.environment.temperature_lava,
    WorldType.CRYSTAL: lambda rules: rules.environment.temperature_crystal,
    WorldType.LIVING: lambda rules: rules.environment.temperature_living,
    WorldType.DEAD: lambda rules: rules.environment.temperature_dead,
    WorldType.DREAM: lambda rules: rules.environment.temperature_dream,
    WorldType.MIRROR: lambda rules: rules.environment.temperature_mirror,
    WorldType.GAS: lambda rules: rules.environment.temperature_gas,
    WorldType.RINGED: lambda rules: rules.environment.temperature_ringed,
    WorldType.ASTEROID_BELT: lambda rules: rules.environment.temperature_asteroid_belt,
    WorldType.TIDALLY_LOCKED: lambda rules: rules.environment.temperature_tidally_locked,
    WorldType.VOID_POCKET: lambda rules: rules.environment.temperature_void_pocket,
    WorldType.GODS_PALACE: lambda rules: rules.environment.temperature_gods_palace,
    WorldType.GENERATION_SHIP: lambda rules: rules.environment.temperature_generation_ship,
    WorldType.CORPSE_WORLD: lambda rules: rules.environment.temperature_corpse_world,
    WorldType.FORGE: lambda rules: rules.environment.temperature_forge,
    WorldType.SUPER_EARTH: lambda rules: rules.environment.temperature_super_earth,
    WorldType.ICE_GIANT: lambda rules: rules.environment.temperature_ice_giant,
    WorldType.HOT_GIANT: lambda rules: rules.environment.temperature_hot_giant,
    WorldType.IRON: lambda rules: rules.environment.temperature_iron,
    WorldType.CARBON: lambda rules: rules.environment.temperature_carbon,
    WorldType.GREENHOUSE: lambda rules: rules.environment.temperature_greenhouse,
    WorldType.DWARF_PLANET: lambda rules: rules.environment.temperature_dwarf_planet,
    WorldType.CHTHONIAN: lambda rules: rules.environment.temperature_chthonian,
    WorldType.HYCEAN: lambda rules: rules.environment.temperature_hycean,
    WorldType.JUNGLE: lambda rules: rules.environment.temperature_jungle,
    WorldType.FUNGAL: lambda rules: rules.environment.temperature_fungal,
    WorldType.SHATTERED: lambda rules: rules.environment.temperature_shattered,
    WorldType.HOLLOW: lambda rules: rules.environment.temperature_hollow,
    WorldType.ICE_SHELL: lambda rules: rules.environment.temperature_ice_shell,
    WorldType.METHANE: lambda rules: rules.environment.temperature_methane,
    WorldType.ROGUE: lambda rules: rules.environment.temperature_rogue,
    WorldType.ARCHIPELAGO: lambda rules: rules.environment.temperature_archipelago,
    WorldType.MEGASTRUCTURE: lambda rules: rules.environment.temperature_megastructure,
}


WORLD_TERRAIN: dict[WorldType, TerrainKind] = {
    WorldType.LAVA: TerrainKind.VOLCANIC,
    WorldType.CRYSTAL: TerrainKind.CRYSTAL_FIELD,
    WorldType.LIVING: TerrainKind.FLESH,
    WorldType.CORPSE_WORLD: TerrainKind.FLESH,
    WorldType.VOID_POCKET: TerrainKind.VOID_SHORE,
    WorldType.GENERATION_SHIP: TerrainKind.UNDERGROUND,
    WorldType.ASTEROID_BELT: TerrainKind.CANYON,
    WorldType.GREENHOUSE: TerrainKind.VOLCANIC,
    WorldType.DWARF_PLANET: TerrainKind.ICE_SHEET,
    WorldType.CHTHONIAN: TerrainKind.VOLCANIC,
    WorldType.JUNGLE: TerrainKind.JUNGLE,
    WorldType.ICE_SHELL: TerrainKind.ICE_SHEET,
    WorldType.METHANE: TerrainKind.TUNDRA,
    WorldType.ROGUE: TerrainKind.ICE_SHEET,
}


WORLD_SOIL: dict[WorldType, SoilKind] = {
    WorldType.LAVA: SoilKind.VOLCANIC,
    WorldType.CRYSTAL: SoilKind.CRYSTALLINE,
    WorldType.DEAD: SoilKind.CALCAREOUS,
    WorldType.CORPSE_WORLD: SoilKind.CALCAREOUS,
    WorldType.SAND: SoilKind.SAND,
    WorldType.ICE: SoilKind.PERMAFROST,
    WorldType.ASTEROID_BELT: SoilKind.REGOLITH,
    WorldType.VOID_POCKET: SoilKind.TEPHRA,
    WorldType.FORGE: SoilKind.TEPHRA,
    WorldType.IRON: SoilKind.THIN,
    WorldType.CARBON: SoilKind.TEPHRA,
    WorldType.GREENHOUSE: SoilKind.VOLCANIC,
    WorldType.DWARF_PLANET: SoilKind.REGOLITH,
    WorldType.CHTHONIAN: SoilKind.VOLCANIC,
    WorldType.JUNGLE: SoilKind.LATERITE,
    WorldType.FUNGAL: SoilKind.PEAT,
    WorldType.SHATTERED: SoilKind.THIN,
    WorldType.ICE_SHELL: SoilKind.PERMAFROST,
    WorldType.METHANE: SoilKind.THIN,
    WorldType.ROGUE: SoilKind.PERMAFROST,
    WorldType.MEGASTRUCTURE: SoilKind.ARTIFICIAL,
    WorldType.HYCEAN: SoilKind.SALINE,
    WorldType.GODS_PALACE: SoilKind.ARTIFICIAL,
    WorldType.GENERATION_SHIP: SoilKind.ARTIFICIAL,
}


WATERING = {LandAct.CARVE_VALLEY: 1, LandAct.OPEN_SPRING: 1, LandAct.FILL_VALLEY: -1}

WORK_SOIL_LAND_ACTS = (LandAct.PARCH, LandAct.GREEN)
