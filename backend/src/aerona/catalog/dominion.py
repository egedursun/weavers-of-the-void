from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

from aerona.catalog.peoples import Style
from aerona.core.total import total
from aerona.domain.enums.affliction import PackageKind
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.dominion import CreatureDeed, DivineScale, Manifestation, PerceivedAlignment, PrayerTone, WorshipMode
from aerona.rules.registry import Rules

D = Domain
ORDER = DivineScale.ORDER
WORK = DivineScale.PRODUCTIVITY
HEAT = DivineScale.HEAT
GROWTH = DivineScale.GROWTH
LUCK = DivineScale.FORTUNE
MAGIC = DivineScale.MAGIC

DOMAIN_SCALES = total(
    Domain,
    {
        D.SEA: ((LUCK, 1),),
        D.FIRE: ((HEAT, 1),),
        D.EARTH: ((WORK, 1),),
        D.SKY: ((ORDER, 1),),
        D.STORM: ((ORDER, -1),),
        D.DEATH: ((GROWTH, -1),),
        D.LIFE: ((GROWTH, 1),),
        D.DREAM: ((MAGIC, 1),),
        D.TIME: ((ORDER, 1),),
        D.LIGHT: ((ORDER, 1),),
        D.SHADOW: ((LUCK, -1),),
        D.WAR: ((ORDER, -1),),
        D.CRAFT: ((WORK, 1),),
        D.KNOWLEDGE: ((MAGIC, 1),),
        D.LOVE: ((GROWTH, 1),),
        D.TRICKERY: ((LUCK, -1),),
        D.HUNT: ((WORK, 1),),
        D.PLANTS: ((GROWTH, 1),),
        D.BONE: ((GROWTH, -1),),
        D.BLOOD: ((MAGIC, 1),),
        D.SOUND: ((ORDER, 1),),
        D.STONE: ((ORDER, 1),),
        D.ICE: ((HEAT, -1),),
        D.MADNESS: ((ORDER, -1),),
        D.TRADE: ((LUCK, 1),),
        D.ROAD: ((WORK, 1),),
        D.PLAGUE: ((GROWTH, -1),),
        D.HARVEST: ((WORK, 1),),
        D.MOON: ((MAGIC, 1),),
        D.SUN: ((HEAT, 1),),
        D.ASH: ((GROWTH, -1),),
        D.BORDER: ((ORDER, 1),),
        D.GLASS: ((MAGIC, 1),),
        D.HUNGER: ((WORK, -1),),
        D.LIES: ((LUCK, -1),),
        D.MEMORY: ((ORDER, 1),),
        D.OATH: ((ORDER, 1),),
        D.SALT: ((WORK, 1),),
        D.SLEEP: ((WORK, -1),),
        D.STAR: ((MAGIC, 1),),
        D.CITIES: ((ORDER, 1),),
        D.INDUSTRY: ((HEAT, 1),),
        D.INFORMATION: ((ORDER, 1),),
        D.MACHINES: ((WORK, 1),),
        D.SCIENCE: ((ORDER, 1),),
        D.SPACE: ((MAGIC, 1),),
        D.TECHNOLOGY: ((WORK, 1),),
    },
)

FAVOURED_POLE = total(DivineScale, {ORDER: 1, WORK: 1, HEAT: 0, GROWTH: 1, LUCK: 1, MAGIC: 1})

SCALE_POLES = total(
    DivineScale,
    {
        ORDER: ("order", "turmoil"),
        WORK: ("productivity", "sloth"),
        HEAT: ("heat", "cold"),
        GROWTH: ("growth", "decay"),
        LUCK: ("fortune", "misfortune"),
        MAGIC: ("magic", "drain"),
    },
)

DOMAIN_CURSES = total(
    Domain,
    {
        D.SEA: PackageKind.HUNGER_CURSE,
        D.FIRE: PackageKind.TRAUMA,
        D.EARTH: PackageKind.HUNGER_CURSE,
        D.SKY: PackageKind.TRAUMA,
        D.STORM: PackageKind.TRAUMA,
        D.DEATH: PackageKind.POSSESSION,
        D.LIFE: PackageKind.HUNGER_CURSE,
        D.DREAM: PackageKind.POSSESSION,
        D.TIME: PackageKind.TRAUMA,
        D.LIGHT: PackageKind.TRAUMA,
        D.SHADOW: PackageKind.VOID_TAINT,
        D.WAR: PackageKind.TRAUMA,
        D.CRAFT: PackageKind.HUNGER_CURSE,
        D.KNOWLEDGE: PackageKind.POSSESSION,
        D.LOVE: PackageKind.TRAUMA,
        D.TRICKERY: PackageKind.POSSESSION,
        D.HUNT: PackageKind.LYCANTHROPY,
        D.PLANTS: PackageKind.HUNGER_CURSE,
        D.BONE: PackageKind.POSSESSION,
        D.BLOOD: PackageKind.VAMPIRISM,
        D.SOUND: PackageKind.TRAUMA,
        D.STONE: PackageKind.HUNGER_CURSE,
        D.ICE: PackageKind.TRAUMA,
        D.MADNESS: PackageKind.VOID_TAINT,
        D.TRADE: PackageKind.HUNGER_CURSE,
        D.ROAD: PackageKind.TRAUMA,
        D.PLAGUE: PackageKind.POSSESSION,
        D.HARVEST: PackageKind.HUNGER_CURSE,
        D.MOON: PackageKind.LYCANTHROPY,
        D.SUN: PackageKind.TRAUMA,
        D.ASH: PackageKind.HUNGER_CURSE,
        D.BORDER: PackageKind.TRAUMA,
        D.GLASS: PackageKind.TRAUMA,
        D.HUNGER: PackageKind.HUNGER_CURSE,
        D.LIES: PackageKind.POSSESSION,
        D.MEMORY: PackageKind.TRAUMA,
        D.OATH: PackageKind.TRAUMA,
        D.SALT: PackageKind.HUNGER_CURSE,
        D.SLEEP: PackageKind.POSSESSION,
        D.STAR: PackageKind.VOID_TAINT,
        D.CITIES: PackageKind.TRAUMA,
        D.INDUSTRY: PackageKind.HUNGER_CURSE,
        D.INFORMATION: PackageKind.POSSESSION,
        D.MACHINES: PackageKind.WARPING,
        D.SCIENCE: PackageKind.WARPING,
        D.SPACE: PackageKind.VOID_TAINT,
        D.TECHNOLOGY: PackageKind.TRAUMA,
    },
)

ALIGNMENT_LOOKS: Mapping[PerceivedAlignment, Style] = MappingProxyType(
    {
        PerceivedAlignment.BENEVOLENT: Style(ornament=90, geometry=50, colour=80, scale=60, symmetry=60),
        PerceivedAlignment.MALEVOLENT: Style(ornament=60, geometry=40, colour=25, scale=50, symmetry=45),
    }
)

ALIGNMENT_MANIFESTATIONS = total(
    PerceivedAlignment,
    {
        PerceivedAlignment.BENEVOLENT: Manifestation.RADIANT,
        PerceivedAlignment.AMBIVALENT: Manifestation.SERENE,
        PerceivedAlignment.MALEVOLENT: Manifestation.DREADFUL,
    },
)
MANIFESTATION_ORDER = total(
    Manifestation,
    {Manifestation.RADIANT: 0, Manifestation.SERENE: 0, Manifestation.STERN: -100, Manifestation.DREADFUL: 50, Manifestation.VEILED: 0},
)

HELPFUL_DEEDS = frozenset({CreatureDeed.TEND_FIELDS, CreatureDeed.HEAL_SICK, CreatureDeed.GUARD_HOLY_SITES})
HARMFUL_DEEDS = frozenset({CreatureDeed.HUNT_FOLK, CreatureDeed.WRECK_WORKS, CreatureDeed.STRIKE_FOES})
FEEDING_DEEDS = frozenset({CreatureDeed.HUNT_FOLK, CreatureDeed.TEND_FIELDS})


@dataclass(frozen=True)
class WorshipModeSpec:
    label: str
    bargains: bool = False


WORSHIP_MODES = total(
    WorshipMode,
    {
        WorshipMode.DEVOTION: WorshipModeSpec("Devotion"),
        WorshipMode.APPEASEMENT: WorshipModeSpec("Appeasement"),
        WorshipMode.BARGAIN: WorshipModeSpec("Bargain", bargains=True),
    },
)
BARGAINING_MODES = frozenset(mode for mode, spec in WORSHIP_MODES.items() if spec.bargains)


@dataclass(frozen=True)
class PrayerToneSpec:
    label: str
    essence: Callable[[Rules], int]
    asks: bool = False
    praises: bool = False


PRAYER_TONES = total(
    PrayerTone,
    {
        PrayerTone.THANKS: PrayerToneSpec("Thanks", lambda rules: rules.worship.thanks_essence),
        PrayerTone.MERCY: PrayerToneSpec("Mercy", lambda rules: rules.worship.mercy_essence, asks=True),
        PrayerTone.REQUEST: PrayerToneSpec("Request", lambda rules: rules.worship.request_essence, asks=True),
        PrayerTone.PRAISE: PrayerToneSpec("Praise", lambda rules: rules.worship.praise_essence, praises=True),
    },
)
