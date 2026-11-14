from enum import StrEnum


class Nutrient(StrEnum):
    ENERGY = "energy"
    PROTEIN = "protein"
    FAT = "fat"
    FRESH = "fresh"
    MINERAL = "mineral"
    LIGHT = "light"
    ESSENCE = "essence"
    CHARGE = "charge"


class DecisionBias(StrEnum):
    OVERCONFIDENCE = "overconfidence"
    SUNK_COST = "sunk_cost"
    LOSS_AVERSION = "loss_aversion"
    CONFIRMATION = "confirmation"
    RECENCY = "recency"
    GROUPTHINK = "groupthink"
    HOSTILE_ATTRIBUTION = "hostile_attribution"
    OPTIMISM = "optimism"
    STATUS_QUO = "status_quo"
    AVAILABILITY = "availability"
    ANCHORING = "anchoring"
    IN_GROUP_FAVOUR = "in_group_favour"
    AUTHORITY_DEFERENCE = "authority_deference"
    SCARCITY_PANIC = "scarcity_panic"
    FATALISM = "fatalism"
    RISK_SEEKING = "risk_seeking"
    PLANNING_FALLACY = "planning_fallacy"
    HALO = "halo"
    PROJECTION = "projection"


class BiasedDecision(StrEnum):
    RAID = "raid"
    PEACE = "peace"
    SURRENDER = "surrender"
    SCHEME = "scheme"
    BELIEF = "belief"
    CONVERSION = "conversion"
    MIGRATION = "migration"
    GOD_GOAL = "god_goal"


class PurityState(StrEnum):
    PURE = "pure"
    IMPURE = "impure"
    DEFILED = "defiled"


class ImpuritySource(StrEnum):
    THE_DEAD = "the_dead"
    BIRTH = "birth"
    BODILY_FLUIDS = "bodily_fluids"
    FOOD = "food"
    SPECIES = "species"
    PROFESSION = "profession"
    OUTSIDERS = "outsiders"
    PLACE = "place"
    OBJECT = "object"
    ACT = "act"
    MADE_THING = "made_thing"
    TABOO = "taboo"
    WOUND = "wound"


class Purification(StrEnum):
    TIME = "time"
    WASHING = "washing"
    FASTING = "fasting"
    OFFERING = "offering"
    RITE = "rite"
    CONFESSION = "confession"
    PAYMENT = "payment"
    ORDEAL = "ordeal"


class MishapKind(StrEnum):
    ILLNESS = "illness"
    CROP_FAILURE = "crop_failure"
    CHILD_DEATH = "child_death"
    LIVESTOCK_DEATH = "livestock_death"
    ACCIDENT = "accident"
    BAD_LUCK = "bad_luck"


class MishapAttribution(StrEnum):
    CHANCE = "chance"
    KNOWN_CAUSE = "known_cause"
    WITCHCRAFT = "witchcraft"
    CURSE = "curse"
    GOD = "god"
    SPIRIT = "spirit"
    ANCESTOR = "ancestor"
    OMEN = "omen"
    FATE = "fate"
    ENEMY_SCHEME = "enemy_scheme"
    IMPURITY = "impurity"
    BROKEN_OATH = "broken_oath"


class MishapResponse(StrEnum):
    NOTHING = "nothing"
    RITE = "rite"
    OFFERING = "offering"
    CHARM = "charm"
    ACCUSATION = "accusation"
    PURIFICATION = "purification"
    SAFETY_CUSTOM = "safety_custom"


class LuckSign(StrEnum):
    DAY = "day"
    NUMBER = "number"
    SIGN = "sign"
    GESTURE = "gesture"
    PLACE = "place"
    ACT = "act"
    PERSON = "person"


class LuckReach(StrEnum):
    HARVEST = "harvest"
    HEALTH = "health"
    BIRTH = "birth"
    JOURNEY = "journey"
    BATTLE = "battle"


class CharmPower(StrEnum):
    PROTECTION = "protection"
    FERTILITY = "fertility"
    LUCK = "luck"
    HEALING = "healing"


class AccusationOutcome(StrEnum):
    PENDING = "pending"
    CLEARED = "cleared"
    PUNISHED = "punished"
    EXILED = "exiled"
    KILLED = "killed"


class IdeaStrain(StrEnum):
    NONE = "none"
    DISTRACTION = "distraction"
    FOCUS_LOSS = "focus_loss"
    OBSESSION = "obsession"
