from enum import StrEnum


class AugmentSlot(StrEnum):
    PART = "part"
    MIND = "mind"
    SENSES = "senses"
    SKIN = "skin"
    BLOOD = "blood"
    WHOLE_BODY = "whole_body"


class AugmentKind(StrEnum):
    REPLACEMENT = "replacement"
    ENHANCEMENT = "enhancement"
    INTERFACE = "interface"
    WEAPON = "weapon"
    REGULATOR = "regulator"
    SENSE = "sense"
    STORAGE = "storage"
    COSMETIC = "cosmetic"


class AugmentMake(StrEnum):
    MADE = "made"
    RITE_BOUND = "rite_bound"
    GROWN = "grown"


class EffectTarget(StrEnum):
    ATTRIBUTE = "attribute"
    CAPACITY = "capacity"
    SKILL = "skill"
    SENSE = "sense"
    RESISTANCE = "resistance"


class RealmPurpose(StrEnum):
    DWELLING = "dwelling"
    AFTERLIFE = "afterlife"
    CONFINEMENT = "confinement"
    TRAINING = "training"
    LEISURE = "leisure"
    LABOUR = "labour"
    WORSHIP = "worship"
    REFUGE = "refuge"
    EXPERIMENT = "experiment"
    FREE = "free"


class RealmEntry(StrEnum):
    INTERFACE = "interface"
    TRANSFER = "transfer"
    RITE = "rite"
    DEATH = "death"
    BIRTH = "birth"


class RealmAwareness(StrEnum):
    KNOWS = "knows"
    RUMOURED = "rumoured"
    UNAWARE = "unaware"


class IntrusionTarget(StrEnum):
    NETWORK = "network"
    DATA_STORE = "data_store"
    MADE_MIND = "made_mind"
    AUGMENT = "augment"
    CONSTRUCT = "construct"
    VEHICLE = "vehicle"
    STRUCTURE = "structure"
    LEDGER = "ledger"
    SAVED_STATE = "saved_state"


class IntrusionApproach(StrEnum):
    TECHNICAL = "technical"
    SOCIAL = "social"
    INSIDER = "insider"
    RITE = "rite"
    POWER = "power"


class IntrusionAim(StrEnum):
    READ = "read"
    ALTER = "alter"
    DENY = "deny"
    SEIZE = "seize"
    PLANT = "plant"
    EXTORT = "extort"


class Attribution(StrEnum):
    UNKNOWN = "unknown"
    SUSPECTED = "suspected"
    KNOWN = "known"
    FALSE_FLAG = "false_flag"


class IntrusionOutcome(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CAUGHT = "caught"


class DataContent(StrEnum):
    SECRET = "secret"
    MIND_STATE = "mind_state"
    KNOWLEDGE = "knowledge"
    ACCOUNT = "account"
    LEDGER = "ledger"
    IDENTITY = "identity"
    ORDERS = "orders"


class SurveillanceFocus(StrEnum):
    CRIME = "crime"
    DISSENT = "dissent"
    FOREIGNERS = "foreigners"
    FAITH = "faith"
    MINDS = "minds"
    GIFTED = "gifted"
    EVERYTHING = "everything"


class Authenticity(StrEnum):
    GENUINE = "genuine"
    ALTERED = "altered"
    FORGED = "forged"
    GENERATED = "generated"
    UNKNOWN = "unknown"


class CompanyCharter(StrEnum):
    CHARTERED = "chartered"
    FREE = "free"
    STATE_OWNED = "state_owned"
    COOPERATIVE = "cooperative"


class CompanyHoldingKind(StrEnum):
    STRUCTURE = "structure"
    NETWORK = "network"
    DATA_STORE = "data_store"
    MADE_MIND = "made_mind"
    FABRICATOR = "fabricator"
    LIVING_LINE = "living_line"
    ROUTE = "route"
    ENCLAVE = "enclave"


class ReplicatorScale(StrEnum):
    MINUTE = "minute"
    MACHINE = "machine"
    WORKS = "works"
    VESSEL = "vessel"


class ReplicatorOutput(StrEnum):
    COPIES = "copies"
    GOODS = "goods"
    STRUCTURES = "structures"
    REPAIR = "repair"
    MEDICINE = "medicine"
    TERRAFORMING = "terraforming"
    DISASSEMBLY = "disassembly"


class ReplicatorStage(StrEnum):
    CONTAINED = "contained"
    WORKING = "working"
    SPREADING = "spreading"
    RUNAWAY = "runaway"
    STOPPED = "stopped"
    EXTINCT = "extinct"


class RelicState(StrEnum):
    WORKING = "working"
    FAILING = "failing"
    DORMANT = "dormant"
    BROKEN = "broken"


class RelicUse(StrEnum):
    AS_MADE = "as_made"
    REPURPOSED = "repurposed"
    REVERED = "revered"
    DISPLAYED = "displayed"
    FEARED = "feared"
    IGNORED = "ignored"


class MadeMindStance(StrEnum):
    ABOMINATION = "abomination"
    TOOL = "tool"
    KIN = "kin"
    SACRED = "sacred"
    SILENT = "silent"


class RelicStance(StrEnum):
    SACRED = "sacred"
    TOOL = "tool"
    FORBIDDEN = "forbidden"
    HERITAGE = "heritage"
    STUDIED = "studied"
