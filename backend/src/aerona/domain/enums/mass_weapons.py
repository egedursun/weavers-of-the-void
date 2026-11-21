from enum import StrEnum


class MassHarm(StrEnum):
    BLAST = "blast"
    FIRE = "fire"
    POISON = "poison"
    DISEASE = "disease"
    RADIATION = "radiation"
    SWARM = "swarm"
    FIELD = "field"
    RITE = "rite"
    DIVINE_RELIC = "divine_relic"


class MassReach(StrEnum):
    SETTLEMENT = "settlement"
    REGION = "region"
    WORLD = "world"


class ProgrammeStage(StrEnum):
    SOUGHT = "sought"
    BUILDING = "building"
    READY = "ready"
    TESTED = "tested"


class Posture(StrEnum):
    NONE = "none"
    DECLARED = "declared"
    AMBIGUOUS = "ambiguous"
    FIRST_USE = "first_use"
    RETALIATION_ONLY = "retaliation_only"
    SHARED_WITH_LEAGUE = "shared_with_league"


class RemnantKind(StrEnum):
    BURIED_CHARGES = "buried_charges"
    POISONED_GROUND = "poisoned_ground"
    FALLOUT = "fallout"
    WRECK_FIELD = "wreck_field"
    UNQUIET_DEAD = "unquiet_dead"
    CURSED_GROUND = "cursed_ground"
    ABANDONED_MACHINES = "abandoned_machines"


ARMED_STAGES = frozenset({ProgrammeStage.READY, ProgrammeStage.TESTED})
