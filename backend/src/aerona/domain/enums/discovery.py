from enum import StrEnum


class GreatField(StrEnum):
    SCHOLAR = "scholar"
    ARTIST = "artist"
    GENERAL = "general"
    PROPHET = "prophet"
    ENGINEER = "engineer"
    MERCHANT = "merchant"
    EXPLORER = "explorer"


class AgeKind(StrEnum):
    NORMAL = "normal"
    GOLDEN = "golden"
    DARK = "dark"
    HEROIC = "heroic"


class EraDeed(StrEnum):
    FIRST_TECHNIQUE = "first_technique"
    FIRST_INSTITUTION = "first_institution"
    GREAT_VICTORY = "great_victory"
    WONDER = "wonder"
    GREAT_PERSON = "great_person"
    DEFEAT = "defeat"
    FAMINE = "famine"


class ResearchIncident(StrEnum):
    LEAK = "leak"
    RELEASED_BEAST = "released_beast"
    PLAGUE = "plague"
    BACKLASH = "backlash"
    FIRE = "fire"
    EXPLOSION = "explosion"
    POISONING = "poisoning"
    SUMMONING_GONE_WRONG = "summoning_gone_wrong"


class TheoryDomain(StrEnum):
    MEDICINE = "medicine"
    COSMOLOGY = "cosmology"
    MATTER = "matter"
    LIFE = "life"
    MIND = "mind"
    MAGIC = "magic"
    HISTORY = "history"
    SOCIETY = "society"


class AnomalyKind(StrEnum):
    FAILED_PREDICTION = "failed_prediction"
    CONTRARY_CURE = "contrary_cure"
    OBSERVATION = "observation"
    DIVINE_SIGN = "divine_sign"


class ArtDiscipline(StrEnum):
    MUSIC = "music"
    POETRY = "poetry"
    DANCE = "dance"
    THEATRE = "theatre"
    PAINTING = "painting"
    SCULPTURE = "sculpture"
    ARCHITECTURE_STYLE = "architecture_style"
    TEXTILE = "textile"
    CALLIGRAPHY = "calligraphy"


class BlueprintKind(StrEnum):
    VESSEL = "vessel"
    SIEGE_ENGINE = "siege_engine"
    STRUCTURE = "structure"
    ARTIFACT_PATTERN = "artifact_pattern"


class BlueprintSource(StrEnum):
    DRAWN = "drawn"
    STOLEN = "stolen"
    TRADED = "traded"
    LICENSED = "licensed"
    GRANTED = "granted"
