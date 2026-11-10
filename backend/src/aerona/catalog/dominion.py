from types import MappingProxyType

from aerona.core.total import total
from aerona.domain.enums.affliction import PackageKind
from aerona.domain.enums.demography import Aesthetic
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.dominion import CreatureDeed, DivineScale, Manifestation, PerceivedAlignment

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
    },
)

ALIGNMENT_AESTHETICS = MappingProxyType({PerceivedAlignment.BENEVOLENT: Aesthetic.ORNATE, PerceivedAlignment.MALEVOLENT: Aesthetic.MACABRE})

ALIGNMENT_MANIFESTATIONS = total(
    PerceivedAlignment,
    {
        PerceivedAlignment.BENEVOLENT: Manifestation.RADIANT,
        PerceivedAlignment.AMBIVALENT: Manifestation.SERENE,
        PerceivedAlignment.MALEVOLENT: Manifestation.DREADFUL,
    },
)

HELPFUL_DEEDS = frozenset({CreatureDeed.TEND_FIELDS, CreatureDeed.HEAL_SICK, CreatureDeed.GUARD_HOLY_SITES})
HARMFUL_DEEDS = frozenset({CreatureDeed.HUNT_FOLK, CreatureDeed.WRECK_WORKS, CreatureDeed.STRIKE_FOES})
FEEDING_DEEDS = frozenset({CreatureDeed.HUNT_FOLK, CreatureDeed.TEND_FIELDS})
