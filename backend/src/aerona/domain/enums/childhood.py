from enum import StrEnum


class InfantFeeding(StrEnum):
    BY_BIRTH_PARENT = "by_birth_parent"
    BY_OTHER_NURSE = "by_other_nurse"
    ANIMAL_MILK = "animal_milk"
    PREPARED_FOOD = "prepared_food"
    MADE_FOOD = "made_food"
    NONE_NEEDED = "none_needed"


class CarryWay(StrEnum):
    CARRIED = "carried"
    CRADLED = "cradled"
    LEFT_TENDED = "left_tended"


class SleepArrangement(StrEnum):
    WITH_PARENT = "with_parent"
    WITH_SIBLINGS = "with_siblings"
    APART = "apart"
    COMMUNAL = "communal"


class InfantCarer(StrEnum):
    KIN = "kin"
    SPECIALIST = "specialist"
    COMMUNITY = "community"
    MADE_MIND = "made_mind"


class SocializationTechnique(StrEnum):
    EXAMPLE = "example"
    INSTRUCTION = "instruction"
    PRAISE = "praise"
    SHAME = "shame"
    PUNISHMENT = "punishment"
    RITUAL_ORDEAL = "ritual_ordeal"
    STORYTELLING = "storytelling"
    PLAY = "play"
    APPRENTICESHIP = "apprenticeship"
    SCHOOLING = "schooling"
    PEER_GROUP = "peer_group"
    AGE_SET = "age_set"
    MENTORING = "mentoring"
    TRAVEL = "travel"


class PedagogyTheory(StrEnum):
    ROTE = "rote"
    DIALECTIC = "dialectic"
    APPRENTICESHIP = "apprenticeship"
    DISCOVERY = "discovery"
    RITUAL_TRANSMISSION = "ritual_transmission"
    EXAMINATION = "examination"
    NETWORK_LEARNING = "network_learning"
    MIND_TRANSFER = "mind_transfer"
    PEER_TEACHING = "peer_teaching"
