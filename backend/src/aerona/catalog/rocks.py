from collections.abc import Callable, Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.environment import SoilKind
from aerona.domain.enums.geology import BuildingGrade, RockKind
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.world import WorldType
from aerona.rules.registry import Rules


@dataclass(frozen=True)
class RockSpec:
    label: str
    hardness: Callable[[Rules], int]
    porosity: Callable[[Rules], int]
    solubility: Callable[[Rules], int]
    workability: Callable[[Rules], int]
    grade: BuildingGrade
    veins: tuple[MaterialKind, ...]
    soil: SoilKind
    worlds: frozenset[WorldType] = frozenset()
    seals: bool = False
    organic: bool = False
    floats: bool = False


GASSY_ROCKS = frozenset({RockKind.COAL, RockKind.SHALE, RockKind.FROZEN_METHANE})
ROCKS: Mapping[RockKind, RockSpec] = total(
    RockKind,
    {
        RockKind.SOIL: RockSpec(
            "Soil",
            lambda rules: rules.rocks.soil_hardness,
            lambda rules: rules.rocks.soil_porosity,
            lambda rules: rules.rocks.soil_solubility,
            lambda rules: rules.rocks.soil_workability,
            BuildingGrade.PLAIN,
            (),
            SoilKind.LOAM,
        ),
        RockKind.CLAY: RockSpec(
            "Clay",
            lambda rules: rules.rocks.clay_hardness,
            lambda rules: rules.rocks.clay_porosity,
            lambda rules: rules.rocks.clay_solubility,
            lambda rules: rules.rocks.clay_workability,
            BuildingGrade.PLAIN,
            (MaterialKind.CLAY,),
            SoilKind.CLAY,
            seals=True,
        ),
        RockKind.SAND: RockSpec(
            "Sand",
            lambda rules: rules.rocks.sand_hardness,
            lambda rules: rules.rocks.sand_porosity,
            lambda rules: rules.rocks.sand_solubility,
            lambda rules: rules.rocks.sand_workability,
            BuildingGrade.PLAIN,
            (MaterialKind.GLASS,),
            SoilKind.SAND,
        ),
        RockKind.LIMESTONE: RockSpec(
            "Limestone",
            lambda rules: rules.rocks.limestone_hardness,
            lambda rules: rules.rocks.limestone_porosity,
            lambda rules: rules.rocks.limestone_solubility,
            lambda rules: rules.rocks.limestone_workability,
            BuildingGrade.FINE,
            (
                MaterialKind.STONE,
                MaterialKind.LEAD,
            ),
            SoilKind.CALCAREOUS,
        ),
        RockKind.SANDSTONE: RockSpec(
            "Sandstone",
            lambda rules: rules.rocks.sandstone_hardness,
            lambda rules: rules.rocks.sandstone_porosity,
            lambda rules: rules.rocks.sandstone_solubility,
            lambda rules: rules.rocks.sandstone_workability,
            BuildingGrade.FINE,
            (
                MaterialKind.STONE,
                MaterialKind.COPPER,
            ),
            SoilKind.SAND,
        ),
        RockKind.SHALE: RockSpec(
            "Shale",
            lambda rules: rules.rocks.shale_hardness,
            lambda rules: rules.rocks.shale_porosity,
            lambda rules: rules.rocks.shale_solubility,
            lambda rules: rules.rocks.shale_workability,
            BuildingGrade.PLAIN,
            (
                MaterialKind.CLAY,
                MaterialKind.AMBER,
            ),
            SoilKind.CLAY,
            seals=True,
            organic=True,
        ),
        RockKind.GRANITE: RockSpec(
            "Granite",
            lambda rules: rules.rocks.granite_hardness,
            lambda rules: rules.rocks.granite_porosity,
            lambda rules: rules.rocks.granite_solubility,
            lambda rules: rules.rocks.granite_workability,
            BuildingGrade.FINE,
            (
                MaterialKind.STONE,
                MaterialKind.TIN,
                MaterialKind.GOLD,
                MaterialKind.GEMS,
            ),
            SoilKind.THIN,
        ),
        RockKind.BASALT: RockSpec(
            "Basalt",
            lambda rules: rules.rocks.basalt_hardness,
            lambda rules: rules.rocks.basalt_porosity,
            lambda rules: rules.rocks.basalt_solubility,
            lambda rules: rules.rocks.basalt_workability,
            BuildingGrade.PLAIN,
            (
                MaterialKind.STONE,
                MaterialKind.IRON,
                MaterialKind.COPPER,
            ),
            SoilKind.VOLCANIC,
        ),
        RockKind.MARBLE: RockSpec(
            "Marble",
            lambda rules: rules.rocks.marble_hardness,
            lambda rules: rules.rocks.marble_porosity,
            lambda rules: rules.rocks.marble_solubility,
            lambda rules: rules.rocks.marble_workability,
            BuildingGrade.SPLENDID,
            (MaterialKind.STONE,),
            SoilKind.CALCAREOUS,
        ),
        RockKind.OBSIDIAN: RockSpec(
            "Obsidian",
            lambda rules: rules.rocks.obsidian_hardness,
            lambda rules: rules.rocks.obsidian_porosity,
            lambda rules: rules.rocks.obsidian_solubility,
            lambda rules: rules.rocks.obsidian_workability,
            BuildingGrade.FINE,
            (MaterialKind.OBSIDIAN,),
            SoilKind.VOLCANIC,
        ),
        RockKind.SLATE: RockSpec(
            "Slate",
            lambda rules: rules.rocks.slate_hardness,
            lambda rules: rules.rocks.slate_porosity,
            lambda rules: rules.rocks.slate_solubility,
            lambda rules: rules.rocks.slate_workability,
            BuildingGrade.FINE,
            (
                MaterialKind.STONE,
                MaterialKind.SILVER,
            ),
            SoilKind.THIN,
        ),
        RockKind.CRYSTAL_BEDROCK: RockSpec(
            "Crystal bedrock",
            lambda rules: rules.rocks.crystal_bedrock_hardness,
            lambda rules: rules.rocks.crystal_bedrock_porosity,
            lambda rules: rules.rocks.crystal_bedrock_solubility,
            lambda rules: rules.rocks.crystal_bedrock_workability,
            BuildingGrade.SPLENDID,
            (
                MaterialKind.CRYSTAL,
                MaterialKind.GEMS,
            ),
            SoilKind.CRYSTALLINE,
            frozenset({WorldType.CRYSTAL}),
        ),
        RockKind.FROZEN_METHANE: RockSpec(
            "Frozen methane",
            lambda rules: rules.rocks.frozen_methane_hardness,
            lambda rules: rules.rocks.frozen_methane_porosity,
            lambda rules: rules.rocks.frozen_methane_solubility,
            lambda rules: rules.rocks.frozen_methane_workability,
            BuildingGrade.PLAIN,
            (),
            SoilKind.PERMAFROST,
            frozenset({WorldType.METHANE}),
        ),
        RockKind.BONE: RockSpec(
            "Bone",
            lambda rules: rules.rocks.bone_hardness,
            lambda rules: rules.rocks.bone_porosity,
            lambda rules: rules.rocks.bone_solubility,
            lambda rules: rules.rocks.bone_workability,
            BuildingGrade.FINE,
            (
                MaterialKind.CALCIFIED_TISSUE,
                MaterialKind.IVORY,
            ),
            SoilKind.REGOLITH,
            frozenset({WorldType.CORPSE_WORLD}),
        ),
        RockKind.GLASS: RockSpec(
            "Glass",
            lambda rules: rules.rocks.glass_hardness,
            lambda rules: rules.rocks.glass_porosity,
            lambda rules: rules.rocks.glass_solubility,
            lambda rules: rules.rocks.glass_workability,
            BuildingGrade.FINE,
            (
                MaterialKind.GLASS,
                MaterialKind.VOID_GLASS,
            ),
            SoilKind.REGOLITH,
            frozenset({WorldType.DEAD, WorldType.SHATTERED}),
        ),
        RockKind.HALITE: RockSpec(
            "Halite",
            lambda rules: rules.rocks.halite_hardness,
            lambda rules: rules.rocks.halite_porosity,
            lambda rules: rules.rocks.halite_solubility,
            lambda rules: rules.rocks.halite_workability,
            BuildingGrade.PLAIN,
            (MaterialKind.HALITE,),
            SoilKind.SALINE,
            seals=True,
        ),
        RockKind.COAL: RockSpec(
            "Coal",
            lambda rules: rules.rocks.coal_hardness,
            lambda rules: rules.rocks.coal_porosity,
            lambda rules: rules.rocks.coal_solubility,
            lambda rules: rules.rocks.coal_workability,
            BuildingGrade.PLAIN,
            (MaterialKind.SULFUR,),
            SoilKind.PEAT,
            organic=True,
        ),
        RockKind.CHALK: RockSpec(
            "Chalk",
            lambda rules: rules.rocks.chalk_hardness,
            lambda rules: rules.rocks.chalk_porosity,
            lambda rules: rules.rocks.chalk_solubility,
            lambda rules: rules.rocks.chalk_workability,
            BuildingGrade.PLAIN,
            (MaterialKind.FLINT,),
            SoilKind.CALCAREOUS,
        ),
        RockKind.TUFF: RockSpec(
            "Tuff",
            lambda rules: rules.rocks.tuff_hardness,
            lambda rules: rules.rocks.tuff_porosity,
            lambda rules: rules.rocks.tuff_solubility,
            lambda rules: rules.rocks.tuff_workability,
            BuildingGrade.FINE,
            (MaterialKind.STONE,),
            SoilKind.VOLCANIC,
        ),
        RockKind.GNEISS: RockSpec(
            "Gneiss",
            lambda rules: rules.rocks.gneiss_hardness,
            lambda rules: rules.rocks.gneiss_porosity,
            lambda rules: rules.rocks.gneiss_solubility,
            lambda rules: rules.rocks.gneiss_workability,
            BuildingGrade.SPLENDID,
            (
                MaterialKind.STONE,
                MaterialKind.GEMS,
            ),
            SoilKind.THIN,
        ),
        RockKind.QUARTZITE: RockSpec(
            "Quartzite",
            lambda rules: rules.rocks.quartzite_hardness,
            lambda rules: rules.rocks.quartzite_porosity,
            lambda rules: rules.rocks.quartzite_solubility,
            lambda rules: rules.rocks.quartzite_workability,
            BuildingGrade.FINE,
            (
                MaterialKind.STONE,
                MaterialKind.GOLD,
            ),
            SoilKind.THIN,
        ),
        RockKind.WATER_ICE: RockSpec(
            "Water ice",
            lambda rules: rules.rocks.water_ice_hardness,
            lambda rules: rules.rocks.water_ice_porosity,
            lambda rules: rules.rocks.water_ice_solubility,
            lambda rules: rules.rocks.water_ice_workability,
            BuildingGrade.PLAIN,
            (),
            SoilKind.PERMAFROST,
            frozenset({WorldType.ICE, WorldType.ICE_SHELL, WorldType.DWARF_PLANET, WorldType.ICE_GIANT}),
        ),
        RockKind.IRON: RockSpec(
            "Iron crust",
            lambda rules: rules.rocks.iron_hardness,
            lambda rules: rules.rocks.iron_porosity,
            lambda rules: rules.rocks.iron_solubility,
            lambda rules: rules.rocks.iron_workability,
            BuildingGrade.FINE,
            (
                MaterialKind.IRON,
                MaterialKind.STEEL,
            ),
            SoilKind.REGOLITH,
            frozenset({WorldType.IRON}),
        ),
        RockKind.CARBON: RockSpec(
            "Carbon crust",
            lambda rules: rules.rocks.carbon_hardness,
            lambda rules: rules.rocks.carbon_porosity,
            lambda rules: rules.rocks.carbon_solubility,
            lambda rules: rules.rocks.carbon_workability,
            BuildingGrade.FINE,
            (
                MaterialKind.GEMS,
                MaterialKind.CRYSTAL,
            ),
            SoilKind.REGOLITH,
            frozenset({WorldType.CARBON}),
        ),
        RockKind.LIVING_TISSUE: RockSpec(
            "Living tissue",
            lambda rules: rules.rocks.living_tissue_hardness,
            lambda rules: rules.rocks.living_tissue_porosity,
            lambda rules: rules.rocks.living_tissue_solubility,
            lambda rules: rules.rocks.living_tissue_workability,
            BuildingGrade.PLAIN,
            (
                MaterialKind.DIVINE_TISSUE,
                MaterialKind.GREAT_BEAST_TISSUE,
            ),
            SoilKind.HUMIC,
            frozenset({WorldType.LIVING}),
        ),
        RockKind.PUMICE: RockSpec(
            "Pumice",
            lambda rules: rules.rocks.pumice_hardness,
            lambda rules: rules.rocks.pumice_porosity,
            lambda rules: rules.rocks.pumice_solubility,
            lambda rules: rules.rocks.pumice_workability,
            BuildingGrade.PLAIN,
            (MaterialKind.STONE,),
            SoilKind.TEPHRA,
            floats=True,
        ),
        RockKind.SERPENTINITE: RockSpec(
            "Serpentinite",
            lambda rules: rules.rocks.serpentinite_hardness,
            lambda rules: rules.rocks.serpentinite_porosity,
            lambda rules: rules.rocks.serpentinite_solubility,
            lambda rules: rules.rocks.serpentinite_workability,
            BuildingGrade.FINE,
            (MaterialKind.STONE,),
            SoilKind.THIN,
        ),
        RockKind.TRAVERTINE: RockSpec(
            "Travertine",
            lambda rules: rules.rocks.travertine_hardness,
            lambda rules: rules.rocks.travertine_porosity,
            lambda rules: rules.rocks.travertine_solubility,
            lambda rules: rules.rocks.travertine_workability,
            BuildingGrade.SPLENDID,
            (MaterialKind.STONE,),
            SoilKind.CALCAREOUS,
        ),
    },
)
WORLD_CRUSTS: Mapping[WorldType, RockKind] = {world: rock for rock, spec in ROCKS.items() for world in sorted(spec.worlds)}
