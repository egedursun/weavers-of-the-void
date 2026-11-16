from enum import StrEnum


class CultivationMethod(StrEnum):
    SELECTIVE_BREEDING = "selective_breeding"
    CULTIVATION = "cultivation"
    SHAPING = "shaping"
    ENGINEERING = "engineering"
    SYNTHESIS = "synthesis"
    BINDING = "binding"
    CLONING = "cloning"
    CHIMERA = "chimera"
    INDUCTION = "induction"


class Metabolism(StrEnum):
    FEEDING = "feeding"
    LIGHT = "light"
    CHEMICAL = "chemical"
    HOST = "host"
    SOURCE = "source"
    PARTNER = "partner"
    DORMANT = "dormant"


class GrowthStage(StrEnum):
    SEED = "seed"
    YOUNG = "young"
    GROWN = "grown"
    PRIME = "prime"
    OLD = "old"
    DYING = "dying"
    DEAD = "dead"


class Fertility(StrEnum):
    STERILE = "sterile"
    BREEDS_TRUE = "breeds_true"
    BREEDS_WILD = "breeds_wild"
    NEEDS_MAKER = "needs_maker"


class HostPlacement(StrEnum):
    SKIN = "skin"
    BLOOD = "blood"
    ORGAN = "organ"
    NERVE = "nerve"
    MIND = "mind"


class HostRelation(StrEnum):
    MUTUAL = "mutual"
    COMMENSAL = "commensal"
    PARASITIC = "parasitic"
    CONTROLLING = "controlling"


class LivingCraftStance(StrEnum):
    ABOMINATION = "abomination"
    PERMITTED = "permitted"
    SACRED_DUTY = "sacred_duty"
    SILENT = "silent"


class LineTrait(StrEnum):
    YIELD = "yield"
    HARDINESS = "hardiness"
    CLIMATE_TOLERANCE = "climate_tolerance"
    DISEASE_RESISTANCE = "disease_resistance"
    STRENGTH = "strength"
    SPEED = "speed"
    SIZE = "size"
    REGENERATION = "regeneration"
    LIFESPAN = "lifespan"
    DOCILITY = "docility"
    POTENCY = "potency"
    FIBRE = "fibre"
    VENOM = "venom"
    FLIGHT = "flight"
    AQUATIC = "aquatic"
    VOID_HARDY = "void_hardy"
    GIFT = "gift"
    NERVOUS_SYSTEM = "nervous_system"
    SAPIENCE = "sapience"


class LineOutcome(StrEnum):
    AS_MEANT = "as_meant"
    UNSTABLE = "unstable"
    STERILE = "sterile"
    SIDE_EFFECTS = "side_effects"
    NON_VIABLE = "non_viable"
    ESCAPED = "escaped"
