from enum import StrEnum


class CultivationMethod(StrEnum):
    SELECTIVE_BREEDING = "selective_breeding"
    CULTIVATION = "cultivation"
    SHAPING = "shaping"
    ENGINEERING = "engineering"
    SYNTHESIS = "synthesis"
    BINDING = "binding"
    CLONING = "cloning"
    MERGING = "merging"
    INDUCTION = "induction"
    HYBRIDISING = "hybridising"
    WILD_RELEASE = "wild_release"


class Metabolism(StrEnum):
    FEEDING = "feeding"
    LIGHT = "light"
    CHEMICAL = "chemical"
    HOST = "host"
    SOURCE = "source"
    PARTNER = "partner"
    DORMANT = "dormant"
    HEAT = "heat"


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
    CROSSES_WILD = "crosses_wild"


class HostPlacement(StrEnum):
    SKIN = "skin"
    BLOOD = "blood"
    ORGAN = "organ"
    NERVE = "nerve"
    MIND = "mind"
    GUT = "gut"


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
    REGULATED = "regulated"


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
    LIGHT_MAKING = "light_making"
    INHERITED_LEARNING = "inherited_learning"
    FILTERING = "filtering"
    SECRETES_BUILDING = "secretes_building"


class LineOutcome(StrEnum):
    AS_MEANT = "as_meant"
    UNSTABLE = "unstable"
    STERILE = "sterile"
    SIDE_EFFECTS = "side_effects"
    NON_VIABLE = "non_viable"
    ESCAPED = "escaped"
    EXCEEDED = "exceeded"
