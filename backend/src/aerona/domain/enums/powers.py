from enum import StrEnum


class SourceLocus(StrEnum):
    SELF = "self"
    OTHERS = "others"
    PLACE = "place"
    SKY = "sky"
    SURROUNDINGS = "surroundings"
    MADE_THINGS = "made_things"
    PATRON = "patron"
    BOND = "bond"
    STORY = "story"
    VOID = "void"
    SUBSTANCE = "substance"
    LIFE = "life"
    DEATH = "death"
    DREAM = "dream"
    EMOTION = "emotion"


class PowerCost(StrEnum):
    ESSENCE = "essence"
    HP = "hp"
    FATIGUE = "fatigue"
    STRAIN = "strain"
    LIFESPAN = "lifespan"
    MEMORY = "memory"
    EMOTION = "emotion"
    SANITY = "sanity"
    REAGENT = "reagent"
    MATERIAL = "material"
    VIS = "vis"
    BELIEF = "belief"
    RENOWN = "renown"
    OATH_STANDING = "oath_standing"
    DEBT = "debt"
    SOUL = "soul"
    TIME = "time"
    SURROUNDINGS = "surroundings"
    LUCK = "luck"
    WARPING = "warping"
    NONE = "none"


class SourceRenewal(StrEnum):
    REST = "rest"
    TIME = "time"
    SEASON = "season"
    SKY_CYCLE = "sky_cycle"
    WORSHIP = "worship"
    FEEDING = "feeding"
    TAKING = "taking"
    VOWS_KEPT = "vows_kept"
    RETURN_TO_PLACE = "return_to_place"
    NONE = "none"


class SourceAccess(StrEnum):
    ANYONE = "anyone"
    GIFTED = "gifted"
    TRAINED = "trained"
    GRANTED = "granted"
    BLOODLINE = "bloodline"
    BONDED = "bonded"
    MADE = "made"


class ResistanceKind(StrEnum):
    WILL = "will"
    DISCIPLINE = "discipline"
    FAITH = "faith"
    SANCTITY = "sanctity"
    MATERIAL = "material"
    DAMPENER = "dampener"
    DISTANCE = "distance"
    COUNTER_SOURCE = "counter_source"
    NONE = "none"


class PowerVisibility(StrEnum):
    OVERT = "overt"
    SUBTLE = "subtle"
    HIDDEN = "hidden"


class PowerHazard(StrEnum):
    INJURY = "injury"
    MADNESS = "madness"
    LEAK = "leak"
    ESCAPE = "escape"
    DEPLETION = "depletion"
    WARPING = "warping"
    BURNOUT = "burnout"
    DEPENDENCY = "dependency"
    ATTENTION = "attention"


class SourceRelation(StrEnum):
    SUPPRESSES = "suppresses"
    AMPLIFIES = "amplifies"
    CONVERTS_INTO = "converts_into"
    CONFLICTS = "conflicts"


class TideCycle(StrEnum):
    SEASON = "season"
    SKY = "sky"
    EPOCH = "epoch"
    AUTHORED = "authored"


class PowerStructure(StrEnum):
    RITE = "rite"
    INNATE = "innate"
    GRANTED = "granted"
    BONDED = "bonded"
    CRAFTED = "crafted"
    MIXED = "mixed"


class Learnability(StrEnum):
    ANYONE = "anyone"
    GIFTED_ONLY = "gifted_only"
    GRANTED_ONLY = "granted_only"
    CANNOT_BE_TAUGHT = "cannot_be_taught"


class SystemRelation(StrEnum):
    OPPOSES = "opposes"
    COMPLEMENTS = "complements"
    SAME_ROOT = "same_root"
    UNAWARE = "unaware"


class PowerOrigin(StrEnum):
    BORN = "born"
    AWAKENED = "awakened"
    EXPOSURE = "exposure"
    GRANTED = "granted"
    BONDED = "bonded"
    DISCIPLINE = "discipline"
    MADE = "made"
    GROWN = "grown"
    BLOODLINE = "bloodline"
    HELD = "held"


class PowerState(StrEnum):
    LATENT = "latent"
    EMERGING = "emerging"
    ACTIVE = "active"
    STRAINED = "strained"
    BURNED_OUT = "burned_out"
    SUPPRESSED = "suppressed"
    LOST = "lost"


class PowerTrigger(StrEnum):
    STRESS = "stress"
    EMOTION = "emotion"
    DANGER = "danger"
    WILL = "will"
    CONTACT = "contact"
    PLACE = "place"
    TIME = "time"


class RestrictionKind(StrEnum):
    ONLY_IN_PLACE = "only_in_place"
    ONLY_AT_TIME = "only_at_time"
    ONLY_AGAINST = "only_against"
    SPOKEN_VOW = "spoken_vow"
    PRICE_EACH_USE = "price_each_use"
    NEVER_ON_SELF = "never_on_self"
    FORBIDDEN_ACT = "forbidden_act"
    MUST_BE_SEEN = "must_be_seen"
    MUST_BE_UNSEEN = "must_be_unseen"
    MUST_TOUCH = "must_touch"


class PowerDeviceEffect(StrEnum):
    AMPLIFY = "amplify"
    DAMPEN = "dampen"
    AWAKEN = "awaken"
    STABILISE = "stabilise"
    EXTEND_RANGE = "extend_range"
    SHIELD = "shield"
    DETECT = "detect"


class GiftedAttitude(StrEnum):
    HONOURED = "honoured"
    FEARED = "feared"
    PERSECUTED = "persecuted"
    REGULATED = "regulated"
    ORDINARY = "ordinary"


class GiftedStance(StrEnum):
    SACRED = "sacred"
    TOOL = "tool"
    FORBIDDEN = "forbidden"
    SUSPECT = "suspect"
    SILENT = "silent"


class BloodlineRule(StrEnum):
    NONE = "none"
    ELDEST = "eldest"
    ALL_CHILDREN = "all_children"
    SKIPPED = "skipped"


class SourceLawLevel(StrEnum):
    FREE = "free"
    LICENSED = "licensed"
    BANNED = "banned"
