from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from aerona.core.total import total
from aerona.domain.enums.physics import TerraformAim

Reshaping = Literal["pressure", "breathable", "shift"]


@dataclass(frozen=True)
class TerraformSpec:
    words: str
    touches_air: bool
    reshaping: Reshaping
    column: str | None = None
    sign: int = 1
    floored: bool = False


T = TerraformAim
TERRAFORM_AIMS: Mapping[TerraformAim, TerraformSpec] = total(
    TerraformAim,
    {
        T.THICKEN_AIR: TerraformSpec("thicken its air", True, "pressure", "pressure", 1),
        T.THIN_AIR: TerraformSpec("thin its air", True, "pressure", "pressure", -1),
        T.BREATHABLE_AIR: TerraformSpec("make its air breathable", True, "breathable"),
        T.WARM: TerraformSpec("warm it", True, "shift", "carbon_dioxide", 1),
        T.COOL: TerraformSpec("cool it", True, "shift", "carbon_dioxide", -1, floored=True),
        T.WATER: TerraformSpec("give it water", False, "shift", "hydrosphere", 1),
        T.DRY: TerraformSpec("dry it", False, "shift", "hydrosphere", -1),
        T.BRIGHTEN: TerraformSpec("raise its brightness", False, "shift", "albedo", 1),
        T.DARKEN: TerraformSpec("lower its brightness", False, "shift", "albedo", -1),
    },
)
