from enum import StrEnum


class SonStatus(StrEnum):
    ACTIVE = "active"
    ASLEEP = "asleep"
    EXILED = "exiled"
    DEAD = "dead"


class Stat(StrEnum):
    STRENGTH = "strength"
    ENDURANCE = "endurance"
    AGILITY = "agility"
    WISDOM = "wisdom"
    CUNNING = "cunning"
    WILL = "will"
    CREATIVITY = "creativity"
    CHARISMA = "charisma"
    MIGHT = "might"


class StatGroup(StrEnum):
    BODY = "body"
    MIND = "mind"
    SPIRIT = "spirit"


class Passion(StrEnum):
    LOYALTY = "loyalty"
    AMBITION = "ambition"
    WRATH = "wrath"
    MERCY = "mercy"


class SonResource(StrEnum):
    HP = "hp"
    ESSENCE = "essence"
    FAITH = "faith"
    FAME = "fame"
    XP = "xp"


class ExistenceMode(StrEnum):
    CONCRETE = "concrete"
    SEMI_CONCRETE = "semi_concrete"
    CONCEPTUAL = "conceptual"
    REFLECTION = "reflection"
    SCATTERED = "scattered"


class ExistenceBand(StrEnum):
    RADIANT = "radiant"
    SOLID = "solid"
    FADED = "faded"
    BEING_FORGOTTEN = "being_forgotten"


class PowerEffect(StrEnum):
    CHEAP_CREATION = "cheap_creation"
    DUEL_MASTER = "duel_master"
    ESSENCE_SPRING = "essence_spring"
    WORSHIPPED = "worshipped"
    TIRELESS = "tireless"
    UNTOUCHABLE = "untouchable"
    DREAM_WHISPER = "dream_whisper"
    WAR_FATHER = "war_father"
    HARVESTER = "harvester"
    SEER = "seer"
    REVIVING = "reviving"
    BOUNTY_GIVER = "bounty_giver"
    CURSER = "curser"


class SonRelationLabel(StrEnum):
    DEVOTION = "devotion"
    FRIENDSHIP = "friendship"
    DISTANCE = "distance"
    HOSTILITY = "hostility"
    HATRED = "hatred"


class ReputationAxis(StrEnum):
    LOVE = "love"
    FEAR = "fear"
    FORGOTTEN = "forgotten"


class ReputationLabel(StrEnum):
    FORGOTTEN = "forgotten"
    HATED = "hated"
    RESPECTED = "respected"
    FEARED = "feared"
    LOVED = "loved"
    DISTANT = "distant"
    ACKNOWLEDGED = "acknowledged"


class SonDeathCause(StrEnum):
    FADING = "fading"
    KILLED_BY_SIBLING = "killed_by_sibling"
    KILLED_BY_CREATOR = "killed_by_creator"
    DEVOURED = "devoured"
    FOREIGN_GOD = "foreign_god"
    COSMIC_HORROR = "cosmic_horror"
    OTHER = "other"


class ResurrectionPath(StrEnum):
    CREATOR = "creator"
    RITE = "rite"
    THREAD = "thread"
