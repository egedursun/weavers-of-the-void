from enum import StrEnum


class StressComponent(StrEnum):
    POPULATION_PRESSURE = "population_pressure"
    IMMISERATION = "immiseration"
    ELITE_OVERPRODUCTION = "elite_overproduction"
    FISCAL_DISTRESS = "fiscal_distress"


class CyclePhase(StrEnum):
    GROWTH = "growth"
    STAGFLATION = "stagflation"
    CRISIS = "crisis"
    DEPRESSION = "depression"


class ChallengeKind(StrEnum):
    DISASTER = "disaster"
    CLIMATE = "climate"
    INVASION = "invasion"
    PLAGUE = "plague"
    FAMINE = "famine"
    COLLAPSE = "collapse"
    SECESSION = "secession"
    TECHNOLOGICAL_SHOCK = "technological_shock"
    SOURCE_DEPLETION = "source_depletion"
    RUNAWAY = "runaway"
    REVELATION = "revelation"
    MIGRATION_WAVE = "migration_wave"


class ChallengeResponse(StrEnum):
    STAGNATION = "stagnation"
    RESPONSE = "response"
    COLLAPSE = "collapse"


class LongPlanKind(StrEnum):
    ECOLOGICAL_TRANSFORMATION = "ecological_transformation"
    BLOODLINE = "bloodline"
    CONVERSION = "conversion"
    WONDER = "wonder"
    FORECAST = "forecast"
    NETWORK = "network"
    MEGASTRUCTURE = "megastructure"
    PROGRAMME = "programme"
    REALM = "realm"
    LINE = "line"
    REFORM = "reform"
    EXPLORATION = "exploration"


class LongPlanStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class GiftOccasion(StrEnum):
    COURTESY = "courtesy"
    FEAST = "feast"
    CIRCUIT = "circuit"
    OFFERING = "offering"
    MARRIAGE = "marriage"
    RETURN = "return"
    ALLIANCE = "alliance"
    RELIEF = "relief"


class GiftState(StrEnum):
    OPEN = "open"
    RETURNED = "returned"
    REFUSED = "refused"
    DESTROYED = "destroyed"
    LAPSED = "lapsed"


class KinshipDescent(StrEnum):
    PATRILINEAL = "patrilineal"
    MATRILINEAL = "matrilineal"
    BILATERAL = "bilateral"
    DOUBLE = "double"
    AMBILINEAL = "ambilineal"


class ResidenceRule(StrEnum):
    PATRILOCAL = "patrilocal"
    MATRILOCAL = "matrilocal"
    NEOLOCAL = "neolocal"
    AVUNCULOCAL = "avunculocal"


class DescentGroup(StrEnum):
    LINEAGE = "lineage"
    CLAN = "clan"
    MOIETY = "moiety"
    HOUSE = "house"


class CousinTerms(StrEnum):
    DISTINCT = "distinct"
    PARALLEL_AS_SIBLINGS = "parallel_as_siblings"
    ALL_AS_SIBLINGS = "all_as_siblings"


class MarriagePreference(StrEnum):
    NONE = "none"
    CROSS_COUSIN = "cross_cousin"
    CLAN_EXOGAMY = "clan_exogamy"
    MOIETY_EXOGAMY = "moiety_exogamy"


class MarriagePayment(StrEnum):
    NONE = "none"
    BRIDE_PRICE = "bride_price"
    DOWRY = "dowry"
    BRIDE_SERVICE = "bride_service"


class ReproductiveSystem(StrEnum):
    TWO_SEX = "two_sex"
    SEQUENTIAL = "sequential"
    AMBISEXUAL = "ambisexual"
    CASTE = "caste"
    ASEXUAL = "asexual"


class ReproductiveCaste(StrEnum):
    WORKER = "worker"
    SOLDIER = "soldier"
    BREEDER = "breeder"


class MobilityMode(StrEnum):
    SEDENTARY = "sedentary"
    TRANSHUMANT = "transhumant"
    NOMADIC = "nomadic"


class LegacyKind(StrEnum):
    MARTIAL_STYLE = "martial_style"
    AESTHETIC = "aesthetic"
    FUNERAL_RITE = "funeral_rite"
    BELIEF = "belief"
    VALUE = "value"
    INNOVATION = "innovation"
    ART_FORM = "art_form"
    TECHNIQUE = "technique"
    LAW = "law"
    INSTITUTION = "institution"
    LANGUAGE = "language"


class LabourRegime(StrEnum):
    INDENTURE = "indenture"
    PEONAGE = "peonage"


class ManumissionPath(StrEnum):
    PURCHASE = "purchase"
    WILL = "will"
    SERVICE = "service"
    LAW = "law"
    REVOLT = "revolt"
