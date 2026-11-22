from collections.abc import Callable, Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.crafts import CatchGround, CatchMedium, Gear
from aerona.rules.registry import Rules


@dataclass(frozen=True)
class GroundSpec:
    medium: CatchMedium
    gear: tuple[Gear, ...]


@dataclass(frozen=True)
class GearSpec:
    rate: Callable[[Rules], int]


GROUNDS: Mapping[CatchGround, GroundSpec] = total(
    CatchGround,
    {
        CatchGround.FISHERY: GroundSpec(CatchMedium.WATER, (Gear.LINES, Gear.NETS, Gear.WEIRS)),
        CatchGround.MARINE_HUNT: GroundSpec(CatchMedium.WATER, (Gear.HARPOONS,)),
        CatchGround.TRAPPING: GroundSpec(CatchMedium.LAND, (Gear.TRAPS, Gear.SNARES)),
        CatchGround.FOWLING: GroundSpec(CatchMedium.LAND, (Gear.SNARES,)),
    },
)

GEAR: Mapping[Gear, GearSpec] = total(
    Gear,
    {
        Gear.LINES: GearSpec(lambda rules: rules.grounds.lines_pct),
        Gear.NETS: GearSpec(lambda rules: rules.grounds.nets_pct),
        Gear.WEIRS: GearSpec(lambda rules: rules.grounds.weirs_pct),
        Gear.TRAPS: GearSpec(lambda rules: rules.grounds.traps_pct),
        Gear.SNARES: GearSpec(lambda rules: rules.grounds.snares_pct),
        Gear.HARPOONS: GearSpec(lambda rules: rules.grounds.harpoons_pct),
    },
)


def grounds_in(medium: CatchMedium) -> tuple[CatchGround, ...]:
    return tuple(ground for ground, spec in GROUNDS.items() if spec.medium is medium)
