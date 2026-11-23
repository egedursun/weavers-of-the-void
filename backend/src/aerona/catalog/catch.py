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
    depletion: Callable[[Rules], int]
    harms_bed: bool = False
    sickens: bool = False
    needs_animals: bool = False


GROUNDS: Mapping[CatchGround, GroundSpec] = total(
    CatchGround,
    {
        CatchGround.FISHERY: GroundSpec(CatchMedium.WATER, (Gear.LINES, Gear.NETS, Gear.WEIRS, Gear.TRAWLS, Gear.POISON)),
        CatchGround.MARINE_HUNT: GroundSpec(CatchMedium.WATER, (Gear.HARPOONS,)),
        CatchGround.TRAPPING: GroundSpec(CatchMedium.LAND, (Gear.TRAPS, Gear.SNARES, Gear.POISON)),
        CatchGround.FOWLING: GroundSpec(CatchMedium.LAND, (Gear.SNARES, Gear.MISSILES, Gear.HUNTING_ANIMALS)),
        CatchGround.GAME_HUNT: GroundSpec(CatchMedium.LAND, (Gear.MISSILES, Gear.TRAPS, Gear.HUNTING_ANIMALS)),
        CatchGround.SHORE_GATHERING: GroundSpec(CatchMedium.SHORE, (Gear.NETS, Gear.TRAPS)),
        CatchGround.DIVING: GroundSpec(CatchMedium.UNDER_WATER, (Gear.NETS, Gear.HARPOONS)),
        CatchGround.FISH_PONDS: GroundSpec(CatchMedium.POND, (Gear.NETS, Gear.WEIRS)),
    },
)

GEAR: Mapping[Gear, GearSpec] = total(
    Gear,
    {
        Gear.LINES: GearSpec(lambda rules: rules.grounds.lines_pct, lambda rules: rules.grounds.lines_depletion),
        Gear.NETS: GearSpec(lambda rules: rules.grounds.nets_pct, lambda rules: rules.grounds.nets_depletion),
        Gear.WEIRS: GearSpec(lambda rules: rules.grounds.weirs_pct, lambda rules: rules.grounds.weirs_depletion),
        Gear.TRAPS: GearSpec(lambda rules: rules.grounds.traps_pct, lambda rules: rules.grounds.traps_depletion),
        Gear.SNARES: GearSpec(lambda rules: rules.grounds.snares_pct, lambda rules: rules.grounds.snares_depletion),
        Gear.HARPOONS: GearSpec(lambda rules: rules.grounds.harpoons_pct, lambda rules: rules.grounds.harpoons_depletion),
        Gear.MISSILES: GearSpec(lambda rules: rules.grounds.missiles_pct, lambda rules: rules.grounds.missiles_depletion),
        Gear.TRAWLS: GearSpec(lambda rules: rules.grounds.trawls_pct, lambda rules: rules.grounds.trawls_depletion, harms_bed=True),
        Gear.POISON: GearSpec(lambda rules: rules.grounds.poison_pct, lambda rules: rules.grounds.poison_depletion, sickens=True),
        Gear.HUNTING_ANIMALS: GearSpec(
            lambda rules: rules.grounds.hunting_animals_pct, lambda rules: rules.grounds.hunting_animals_depletion, needs_animals=True
        ),
    },
)


def grounds_in(medium: CatchMedium) -> tuple[CatchGround, ...]:
    return tuple(ground for ground, spec in GROUNDS.items() if spec.medium is medium)
