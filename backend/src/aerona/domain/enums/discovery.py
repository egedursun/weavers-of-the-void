from enum import StrEnum


class GreatField(StrEnum):
    SCHOLAR = "scholar"
    ARTIST = "artist"
    GENERAL = "general"
    PROPHET = "prophet"
    ENGINEER = "engineer"
    MERCHANT = "merchant"
    EXPLORER = "explorer"
    HEALER = "healer"
    LAWGIVER = "lawgiver"
    TEACHER = "teacher"
    REFORMER = "reformer"


class AgeKind(StrEnum):
    NORMAL = "normal"
    GOLDEN = "golden"
    DARK = "dark"
    HEROIC = "heroic"
    RISING = "rising"
    DECLINING = "declining"
    TRANSFORMING = "transforming"
    STAGNANT = "stagnant"
    WANDERING = "wandering"
    REBORN = "reborn"


class EraDeed(StrEnum):
    FIRST_TECHNIQUE = "first_technique"
    FIRST_INSTITUTION = "first_institution"
    GREAT_VICTORY = "great_victory"
    WONDER = "wonder"
    GREAT_PERSON = "great_person"
    DEFEAT = "defeat"
    FAMINE = "famine"
    FIRST_NETWORK = "first_network"
    FIRST_MADE_MIND = "first_made_mind"
    FIRST_LINE = "first_line"
    REVELATION = "revelation"
    COLLAPSE = "collapse"
    GREAT_PEACE = "great_peace"
    GREAT_MIGRATION = "great_migration"
    FIRST_CHARTER = "first_charter"


class ResearchIncident(StrEnum):
    LEAK = "leak"
    RELEASED_BEAST = "released_beast"
    PLAGUE = "plague"
    BACKLASH = "backlash"
    FIRE = "fire"
    EXPLOSION = "explosion"
    POISONING = "poisoning"
    SUMMONING_GONE_WRONG = "summoning_gone_wrong"
    STOLEN = "stolen"
    CHANCE_FIND = "chance_find"


class TheoryDomain(StrEnum):
    MEDICINE = "medicine"
    COSMOLOGY = "cosmology"
    MATTER = "matter"
    LIFE = "life"
    MIND = "mind"
    MAGIC = "magic"
    HISTORY = "history"
    SOCIETY = "society"
    LANGUAGE = "language"
    LAW = "law"


class AnomalyKind(StrEnum):
    FAILED_PREDICTION = "failed_prediction"
    CONTRARY_CURE = "contrary_cure"
    OBSERVATION = "observation"
    DIVINE_SIGN = "divine_sign"
    CONTRARY_RECORD = "contrary_record"
    OUT_OF_PLACE_FIND = "out_of_place_find"


class BlueprintKind(StrEnum):
    VESSEL = "vessel"
    SIEGE_ENGINE = "siege_engine"
    STRUCTURE = "structure"
    ARTIFACT_PATTERN = "artifact_pattern"
    MADE_BODY = "made_body"
    AUGMENT = "augment"
    LINE = "line"
    NETWORK = "network"
    RITE_PATTERN = "rite_pattern"
    PROCESS = "process"
    REMEDY = "remedy"


class BlueprintSource(StrEnum):
    DRAWN = "drawn"
    STOLEN = "stolen"
    TRADED = "traded"
    LICENSED = "licensed"
    GRANTED = "granted"
    FOUND = "found"
