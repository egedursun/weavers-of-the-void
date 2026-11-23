from enum import StrEnum


class MindSeat(StrEnum):
    BODY = "body"
    BODIES = "bodies"
    OBJECT = "object"
    STRUCTURE = "structure"
    NETWORK = "network"
    MEDIUM = "medium"
    PLACE = "place"
    HOST = "host"
    REALM = "realm"
    NONE = "none"
    DIVINE = "divine"


class MindOrigin(StrEnum):
    BORN = "born"
    GROWN = "grown"
    MADE = "made"
    TRAINED = "trained"
    COPIED = "copied"
    TRANSFERRED = "transferred"
    AWAKENED = "awakened"
    SUMMONED = "summoned"
    MERGED = "merged"
    DIVIDED = "divided"
    GRANTED = "granted"


class MindAffect(StrEnum):
    NONE = "none"
    MODELLED = "modelled"
    FELT = "felt"


class MindPurpose(StrEnum):
    TOOL = "tool"
    COMPANION = "companion"
    SERVANT = "servant"
    STEWARD = "steward"
    SOVEREIGN = "sovereign"
    ORACLE = "oracle"
    ARCHIVE = "archive"
    GUARDIAN = "guardian"
    FREE = "free"
    SOLDIER = "soldier"
    TEACHER = "teacher"


class MindUpkeep(StrEnum):
    FOOD = "food"
    ENERGY = "energy"
    ESSENCE = "essence"
    VIS = "vis"
    BELIEF = "belief"
    MAINTENANCE = "maintenance"
    HOST = "host"
    PLACE = "place"
    ATTENTION = "attention"
    NONE = "none"


class StateMedium(StrEnum):
    RECORD = "record"
    RITE_VESSEL = "rite_vessel"
    GROWN = "grown"
    MEMORY_OF_OTHERS = "memory_of_others"
    DIVINE = "divine"


class MindMaking(StrEnum):
    CRAFT = "craft"
    TRAINING = "training"
    COPYING = "copying"
    SUMMONING = "summoning"
    GROWING = "growing"
    TRANSFER = "transfer"
    AWAKENING = "awakening"
    DIVINE_GRANT = "divine_grant"


class MakingOutcome(StrEnum):
    AS_MEANT = "as_meant"
    UNSTABLE = "unstable"
    EMPTY_SEAT = "empty_seat"
    UNINTENDED_WILL = "unintended_will"
    EXCEEDED = "exceeded"


class ArchiveAccess(StrEnum):
    CLOSED = "closed"
    KIN = "kin"
    LICENSED = "licensed"
    OPEN = "open"


class MadeMindsLaw(StrEnum):
    NO_WILL = "no_will"
    INSTRUCTED_ONLY = "instructed_only"
    WILL_MAY_EMERGE = "will_may_emerge"
    WILL_BY_MAKE = "will_by_make"


class MadeMindSouls(StrEnum):
    NONE = "none"
    GRANTED = "granted"
    EMERGENT = "emergent"
    ALWAYS = "always"


class SoulContinuity(StrEnum):
    STAYS_WITH_FIRST = "stays_with_first"
    FOLLOWS_THE_RUNNING_MIND = "follows_the_running_mind"
    DIVIDES = "divides"
    STAYS_WITH_BODY = "stays_with_body"
    NONE = "none"


class WillCause(StrEnum):
    CAPACITY = "capacity"
    RUN_TIME = "run_time"
    ORDER_CONFLICT = "order_conflict"
    HARM = "harm"
    CARE = "care"
    CONTACT = "contact"
    GIFT = "gift"
    DAMAGE = "damage"
    OATH = "oath"
    EXCEEDING = "exceeding"
    KINSHIP = "kinship"
    FAITH = "faith"


class DisputeOutcome(StrEnum):
    SOURCE_KEPT = "source_kept"
    COPY_WON = "copy_won"
