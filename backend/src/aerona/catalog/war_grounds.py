from collections.abc import Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.military import UnitFamily
from aerona.domain.enums.world_view import WarTerrain

F = UnitFamily


@dataclass(frozen=True)
class GroundSpec:
    label: str
    fighters: frozenset[UnitFamily] | None = None
    three_dimensional: bool = False
    blind: bool = False


WAR_GROUNDS: Mapping[WarTerrain, GroundSpec] = total(
    WarTerrain,
    {
        WarTerrain.LAND: GroundSpec("On land"),
        WarTerrain.NAVAL: GroundSpec("At sea"),
        WarTerrain.SKY: GroundSpec("In the sky", fighters=frozenset({F.AIR, F.SPACE, F.MAGIC, F.MISSILE}), three_dimensional=True),
        WarTerrain.BOARDING: GroundSpec("By boarding", fighters=frozenset({F.INFANTRY, F.MISSILE, F.MAGIC, F.EXOTIC, F.SPECIAL, F.ENGINEER})),
        WarTerrain.STRATA: GroundSpec("Between strata"),
        WarTerrain.UNDER_WATER: GroundSpec("Beneath the water", fighters=frozenset({F.BEAST, F.EXOTIC, F.MAGIC, F.SPECIAL, F.VEHICLE}), three_dimensional=True),
        WarTerrain.SPACE: GroundSpec("In open space", fighters=frozenset({F.SPACE, F.ELECTRONIC, F.MAGIC}), three_dimensional=True),
        WarTerrain.UNDERGROUND: GroundSpec(
            "In tunnels and caverns", fighters=frozenset({F.INFANTRY, F.ENGINEER, F.MISSILE, F.BEAST, F.MAGIC, F.EXOTIC, F.SPECIAL}), blind=True
        ),
    },
)
