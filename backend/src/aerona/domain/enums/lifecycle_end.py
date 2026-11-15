from enum import StrEnum


class LifecycleKind(StrEnum):
    IDEOLOGY = "ideology"
    THEORY = "theory"
    RITE = "rite"
    DISEASE = "disease"
    OUTER_BEING = "outer_being"


class LifecycleState(StrEnum):
    ACTIVE = "active"
    DORMANT = "dormant"
    EXTINCT = "extinct"
    LOST = "lost"
    CORRUPTED = "corrupted"
    ERADICATED = "eradicated"
    BANISHED = "banished"
    DESTROYED = "destroyed"


class LifecycleCause(StrEnum):
    LIVING = "living"
    NO_ADHERENTS = "no_adherents"
    NO_TEXTS = "no_texts"
    NO_PRACTITIONERS = "no_practitioners"
    NO_HOSTS = "no_hosts"
    SEALED = "sealed"
    REVIVED = "revived"
    REDISCOVERED = "rediscovered"
    RECONSTRUCTED = "reconstructed"
    RERELEASED = "rereleased"
    RETURNED = "returned"
    GOD_ACT = "god_act"
