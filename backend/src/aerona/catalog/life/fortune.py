from collections.abc import Mapping

from aerona.core.total import total
from aerona.domain.enums.body import DamageType
from aerona.domain.enums.folkways import MishapKind

HARMED: Mapping[MishapKind, DamageType | None] = total(
    MishapKind,
    {
        MishapKind.ILLNESS: None,
        MishapKind.CROP_FAILURE: None,
        MishapKind.CHILD_DEATH: None,
        MishapKind.LIVESTOCK_DEATH: None,
        MishapKind.ACCIDENT: DamageType.BLUNT,
        MishapKind.BAD_LUCK: None,
        MishapKind.FALL: DamageType.BLUNT,
        MishapKind.CRUSH: DamageType.BLUNT,
        MishapKind.CUT: DamageType.CUT,
        MishapKind.BURN: DamageType.FIRE,
        MishapKind.SCALD: DamageType.FIRE,
        MishapKind.DROWNING: DamageType.COLD,
        MishapKind.BEAST: DamageType.PIERCE,
        MishapKind.TOOL: DamageType.CUT,
        MishapKind.MACHINE: DamageType.CUT,
        MishapKind.VEHICLE: DamageType.BLUNT,
        MishapKind.COLLAPSE: DamageType.BLUNT,
        MishapKind.HOUSE_FIRE: DamageType.FIRE,
        MishapKind.POISONING: DamageType.CHEMICAL,
        MishapKind.CHOKING: DamageType.BLUNT,
        MishapKind.EXPOSURE: DamageType.COLD,
        MishapKind.LIGHTNING: DamageType.ELECTRIC,
        MishapKind.SPORT: DamageType.BLUNT,
        MishapKind.BRAWL: DamageType.BLUNT,
        MishapKind.LOST_WAY: None,
        MishapKind.STORES_SPOILED: None,
        MishapKind.GOODS_LOST: None,
        MishapKind.PURSE_LOST: None,
        MishapKind.THEFT_SUFFERED: None,
        MishapKind.TOOL_BROKEN: None,
        MishapKind.NEAR_MISS: None,
    },
)


EVERYDAY = (
    MishapKind.FALL,
    MishapKind.CUT,
    MishapKind.BURN,
    MishapKind.SCALD,
    MishapKind.CRUSH,
    MishapKind.BEAST,
    MishapKind.TOOL,
    MishapKind.VEHICLE,
    MishapKind.COLLAPSE,
    MishapKind.HOUSE_FIRE,
    MishapKind.POISONING,
    MishapKind.CHOKING,
    MishapKind.DROWNING,
    MishapKind.SPORT,
    MishapKind.BRAWL,
    MishapKind.LOST_WAY,
    MishapKind.STORES_SPOILED,
    MishapKind.GOODS_LOST,
    MishapKind.PURSE_LOST,
    MishapKind.THEFT_SUFFERED,
    MishapKind.TOOL_BROKEN,
    MishapKind.NEAR_MISS,
)


WORKING = (MishapKind.TOOL, MishapKind.MACHINE, MishapKind.CRUSH, MishapKind.COLLAPSE, MishapKind.BEAST)


CHILDHOOD = (MishapKind.FALL, MishapKind.DROWNING, MishapKind.BURN, MishapKind.SCALD, MishapKind.CHOKING, MishapKind.POISONING)


WEATHER = (MishapKind.EXPOSURE, MishapKind.LIGHTNING)


SPORTING = (MishapKind.SPORT, MishapKind.BRAWL)
