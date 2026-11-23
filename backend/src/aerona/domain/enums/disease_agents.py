from enum import StrEnum


class DiseaseAgent(StrEnum):
    VIRUS = "virus"
    BACTERIUM = "bacterium"
    FUNGUS = "fungus"
    PARASITE = "parasite"
    PRION = "prion"
    TOXIN = "toxin"
    DEFICIENCY = "deficiency"
    SPIRIT = "spirit"
    CURSE = "curse"
    MADE = "made"
    UNKNOWN = "unknown"


class CureClass(StrEnum):
    REST_AND_CARE = "rest_and_care"
    HERBAL = "herbal"
    ANTIMICROBIAL = "antimicrobial"
    ANTIPARASITIC = "antiparasitic"
    ANTITOXIN = "antitoxin"
    NUTRITIONAL = "nutritional"
    RITE = "rite"
    EXORCISM = "exorcism"
    POWER = "power"
    DESIGNED = "designed"
    SURGERY = "surgery"
    ANTIVIRAL = "antiviral"
