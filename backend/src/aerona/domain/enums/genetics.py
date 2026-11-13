from enum import StrEnum

from aerona.domain.enums.culture import MagicSchool


class LocusGroup(StrEnum):
    LOOKS = "looks"
    PREDISPOSITION = "predisposition"
    GIFT = "gift"


class Locus(StrEnum):
    HEIGHT = "height"
    BUILD = "build"
    SKIN = "skin"
    HAIR_COLOUR = "hair_colour"
    HAIR_TEXTURE = "hair_texture"
    EYE_COLOUR = "eye_colour"
    FACE = "face"
    VOICE = "voice"
    LONGEVITY = "longevity"
    FERTILITY = "fertility"
    DISEASE_RESISTANCE = "disease_resistance"
    MADNESS = "madness"
    COLOUR_BLINDNESS = "colour_blindness"
    GIANT_BLOOD = "giant_blood"
    DIVINE_BLOOD = "divine_blood"
    CURSE_MARKER = "curse_marker"
    GIFT_ELEMENTAL_FIRE = "gift_elemental_fire"
    GIFT_ELEMENTAL_WATER = "gift_elemental_water"
    GIFT_EARTH = "gift_earth"
    GIFT_STORM = "gift_storm"
    GIFT_LIFE = "gift_life"
    GIFT_DEATH = "gift_death"
    GIFT_MIND = "gift_mind"
    GIFT_ILLUSION = "gift_illusion"
    GIFT_DIVINATION = "gift_divination"
    GIFT_WARDING = "gift_warding"
    GIFT_BINDING = "gift_binding"
    GIFT_SUMMONING = "gift_summoning"
    GIFT_BLOOD = "gift_blood"
    GIFT_VOID = "gift_void"


GIFT_LOCI: dict[MagicSchool, Locus] = {school: Locus(f"gift_{school.value}") for school in MagicSchool}
SCHOOL_OF_LOCUS: dict[Locus, MagicSchool] = {locus: school for school, locus in GIFT_LOCI.items()}


class GiftStance(StrEnum):
    HONOURED = "honoured"
    FEARED = "feared"
    PERSECUTED = "persecuted"
    TAXED = "taxed"


class HouseholdRole(StrEnum):
    HEAD = "head"
    SPOUSE = "spouse"
    HEIR = "heir"
    DEPENDENT = "dependent"
    CARER = "carer"
    SERVANT = "servant"
    WARD = "ward"
    LODGER = "lodger"


class DwellingKind(StrEnum):
    HUT = "hut"
    LONGHOUSE = "longhouse"
    TOWNHOUSE = "townhouse"
    MANOR = "manor"
    PALACE = "palace"
    TENT = "tent"
    CAVE = "cave"
    SHIP = "ship"
    TOWER = "tower"
    APARTMENT = "apartment"


class HouseholdDecision(StrEnum):
    MARRY = "marry"
    APPRENTICE = "apprentice"
    MIGRATE = "migrate"
    RENOVATE = "renovate"
    TAKE_LODGER = "take_lodger"
    HIRE_SERVANT = "hire_servant"
    DISMISS_SERVANT = "dismiss_servant"
    SELL_FURNISHING = "sell_furnishing"
    LEND = "lend"
