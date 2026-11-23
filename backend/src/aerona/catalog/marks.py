from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from aerona.core.total import total
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.customs import MarkKind, MarkMeaning
from aerona.domain.enums.made import AugmentKind

K = MarkKind
M = MarkMeaning


@dataclass(frozen=True)
class MarkSpec:
    label: str
    seeded: bool = True
    quick: bool = False
    shows_augment: bool = False


@dataclass(frozen=True)
class MeaningSpec:
    label: str
    reading: str | None
    shames: bool = False
    event: BondKind | None = None
    at_birth: bool = False
    seeded: bool = True
    calms: bool = False
    mourns: bool = False
    guild: bool = False


MARKS: Mapping[MarkKind, MarkSpec] = total(
    MarkKind,
    {
        K.TATTOO: MarkSpec("Tattoo"),
        K.SCAR: MarkSpec("Scar"),
        K.PIERCING: MarkSpec("Piercing"),
        K.SHAPING: MarkSpec("Shaping"),
        K.FILED_TEETH: MarkSpec("Filed teeth"),
        K.COSMETIC: MarkSpec("Cosmetic"),
        K.JEWELLERY: MarkSpec("Jewellery"),
        K.BRAND: MarkSpec("Brand", seeded=False),
        K.HAIR: MarkSpec("Hair", quick=True),
        K.IMPLANT: MarkSpec("Implant", seeded=False, shows_augment=True),
    },
)
MEANINGS: Mapping[MarkMeaning, MeaningSpec] = total(
    MarkMeaning,
    {
        M.STATUS: MeaningSpec("Status", "renown", event=BondKind.RULES),
        M.CLAN: MeaningSpec("Clan", "loyalty_community", at_birth=True),
        M.DEED: MeaningSpec("Deed", "renown", event=BondKind.KILLED),
        M.AGE_SET: MeaningSpec("Age-set", "loyalty_community"),
        M.MARRIAGE: MeaningSpec("Marriage", "loyalty_community", event=BondKind.SPOUSE_OF),
        M.MOURNING: MeaningSpec("Mourning", None, calms=True, mourns=True),
        M.PROTECTION: MeaningSpec("Protection", None, at_birth=True, calms=True),
        M.CRIME: MeaningSpec("Crime", "honour", seeded=False, shames=True),
        M.FAITH: MeaningSpec("Faith", "loyalty_god", event=BondKind.ADHERENT_OF),
        M.PROFESSION: MeaningSpec("Trade", "renown", guild=True),
        M.BEAUTY: MeaningSpec("Beauty", "renown", event=BondKind.BETROTHED_TO),
    },
)
MARKABLE = tuple(kind for kind, spec in MARKS.items() if spec.seeded)
SEEDED_MEANINGS = tuple(meaning for meaning, spec in MEANINGS.items() if spec.seeded)
CALMING = tuple(meaning for meaning, spec in MEANINGS.items() if spec.calms)
EVENT_BONDS: Mapping[MarkMeaning, BondKind] = MappingProxyType({meaning: spec.event for meaning, spec in MEANINGS.items() if spec.event is not None})
AUGMENT_MEANINGS: Mapping[AugmentKind, MarkMeaning] = total(
    AugmentKind,
    {
        AugmentKind.REPLACEMENT: M.STATUS,
        AugmentKind.ENHANCEMENT: M.STATUS,
        AugmentKind.INTERFACE: M.PROFESSION,
        AugmentKind.WEAPON: M.DEED,
        AugmentKind.REGULATOR: M.PROTECTION,
        AugmentKind.SENSE: M.PROFESSION,
        AugmentKind.STORAGE: M.PROFESSION,
        AugmentKind.COSMETIC: M.BEAUTY,
    },
)
