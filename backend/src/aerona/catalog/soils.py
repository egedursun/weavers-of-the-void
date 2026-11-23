from collections.abc import Callable, Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.environment import SoilKind
from aerona.rules.registry import Rules


@dataclass(frozen=True)
class SoilSpec:
    label: str
    fertility: Callable[[Rules], int]
    drainage: Callable[[Rules], int]
    workability: Callable[[Rules], int]
    acidity: int
    erosion: int
    drawn: bool = False


SOILS: Mapping[SoilKind, SoilSpec] = total(
    SoilKind,
    {
        SoilKind.THIN: SoilSpec(
            "Thin",
            lambda rules: rules.environment.soil_thin,
            lambda rules: rules.soils.thin_drainage,
            lambda rules: rules.soils.thin_workability,
            50,
            40,
            drawn=True,
        ),
        SoilKind.LOAM: SoilSpec(
            "Loam",
            lambda rules: rules.environment.soil_loam,
            lambda rules: rules.soils.loam_drainage,
            lambda rules: rules.soils.loam_workability,
            50,
            30,
            drawn=True,
        ),
        SoilKind.CLAY: SoilSpec(
            "Clay",
            lambda rules: rules.environment.soil_clay,
            lambda rules: rules.soils.clay_drainage,
            lambda rules: rules.soils.clay_workability,
            55,
            20,
            drawn=True,
        ),
        SoilKind.SAND: SoilSpec(
            "Sand",
            lambda rules: rules.environment.soil_sand,
            lambda rules: rules.soils.sand_drainage,
            lambda rules: rules.soils.sand_workability,
            45,
            60,
            drawn=True,
        ),
        SoilKind.VOLCANIC: SoilSpec(
            "Volcanic",
            lambda rules: rules.environment.soil_volcanic,
            lambda rules: rules.soils.volcanic_drainage,
            lambda rules: rules.soils.volcanic_workability,
            40,
            30,
        ),
        SoilKind.PEAT: SoilSpec(
            "Peat",
            lambda rules: rules.environment.soil_peat,
            lambda rules: rules.soils.peat_drainage,
            lambda rules: rules.soils.peat_workability,
            85,
            25,
            drawn=True,
        ),
        SoilKind.SALINE: SoilSpec(
            "Saline", lambda rules: rules.environment.soil_salt, lambda rules: rules.soils.saline_drainage, lambda rules: rules.soils.saline_workability, 20, 35
        ),
        SoilKind.TEPHRA: SoilSpec(
            "Tephra", lambda rules: rules.environment.soil_ash, lambda rules: rules.soils.tephra_drainage, lambda rules: rules.soils.tephra_workability, 45, 45
        ),
        SoilKind.CRYSTALLINE: SoilSpec(
            "Crystalline",
            lambda rules: rules.environment.soil_crystal,
            lambda rules: rules.soils.crystalline_drainage,
            lambda rules: rules.soils.crystalline_workability,
            50,
            5,
        ),
        SoilKind.CALCAREOUS: SoilSpec(
            "Calcareous",
            lambda rules: rules.environment.soil_bone,
            lambda rules: rules.soils.calcareous_drainage,
            lambda rules: rules.soils.calcareous_workability,
            15,
            30,
        ),
        SoilKind.LATERITE: SoilSpec(
            "Laterite",
            lambda rules: rules.environment.soil_laterite,
            lambda rules: rules.soils.laterite_drainage,
            lambda rules: rules.soils.laterite_workability,
            70,
            50,
        ),
        SoilKind.PERMAFROST: SoilSpec(
            "Permafrost",
            lambda rules: rules.environment.soil_permafrost,
            lambda rules: rules.soils.permafrost_drainage,
            lambda rules: rules.soils.permafrost_workability,
            60,
            15,
        ),
        SoilKind.REGOLITH: SoilSpec(
            "Regolith",
            lambda rules: rules.environment.soil_regolith,
            lambda rules: rules.soils.regolith_drainage,
            lambda rules: rules.soils.regolith_workability,
            50,
            55,
        ),
        SoilKind.ARTIFICIAL: SoilSpec(
            "Artificial",
            lambda rules: rules.environment.soil_artificial,
            lambda rules: rules.soils.artificial_drainage,
            lambda rules: rules.soils.artificial_workability,
            50,
            10,
        ),
        SoilKind.HUMIC: SoilSpec(
            "Humic",
            lambda rules: rules.soils.humic_fertility,
            lambda rules: rules.soils.humic_drainage,
            lambda rules: rules.soils.humic_workability,
            45,
            35,
            drawn=True,
        ),
        SoilKind.LEACHED: SoilSpec(
            "Leached",
            lambda rules: rules.soils.leached_fertility,
            lambda rules: rules.soils.leached_drainage,
            lambda rules: rules.soils.leached_workability,
            85,
            30,
            drawn=True,
        ),
        SoilKind.SILT: SoilSpec(
            "Silt",
            lambda rules: rules.soils.silt_fertility,
            lambda rules: rules.soils.silt_drainage,
            lambda rules: rules.soils.silt_workability,
            50,
            70,
            drawn=True,
        ),
        SoilKind.GLEY: SoilSpec(
            "Gley",
            lambda rules: rules.soils.gley_fertility,
            lambda rules: rules.soils.gley_drainage,
            lambda rules: rules.soils.gley_workability,
            65,
            15,
            drawn=True,
        ),
        SoilKind.CRACKING_CLAY: SoilSpec(
            "Cracking clay",
            lambda rules: rules.soils.cracking_clay_fertility,
            lambda rules: rules.soils.cracking_clay_drainage,
            lambda rules: rules.soils.cracking_clay_workability,
            40,
            40,
            drawn=True,
        ),
    },
)


def soft(rules: Rules, soil: SoilKind) -> bool:
    return SOILS[soil].workability(rules) >= rules.soils.soft_workability
