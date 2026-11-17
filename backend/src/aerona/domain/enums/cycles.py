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
    THROUGH_FIRST_LINE = "through_first_line"
    THROUGH_SECOND_LINE = "through_second_line"
    BILATERAL = "bilateral"
    DOUBLE = "double"
    AMBILINEAL = "ambilineal"


class ResidenceRule(StrEnum):
    WITH_FIRST_FAMILY = "with_first_family"
    WITH_SECOND_FAMILY = "with_second_family"
    NEW_HOUSEHOLD = "new_household"
    WITH_KIN_OF_THE_FIRST_LINE = "with_kin_of_the_first_line"


class DescentGroup(StrEnum):
    LINEAGE = "lineage"
    CLAN = "clan"
    MOIETY = "moiety"
    HOUSE = "house"


class KinTermSystem(StrEnum):
    GENERATIONAL = "generational"
    LINEAL = "lineal"
    BIFURCATE_MERGING = "bifurcate_merging"
    BIFURCATE_COLLATERAL = "bifurcate_collateral"
    CROSS_PARALLEL = "cross_parallel"
    DESCRIPTIVE = "descriptive"


class AdoptionKind(StrEnum):
    HEIR = "heir"
    WARD = "ward"
    FOSTER = "foster"
    SPONSOR = "sponsor"
    BLOOD_BOND = "blood_bond"
    CHOSEN_KIN = "chosen_kin"


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
