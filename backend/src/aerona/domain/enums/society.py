from enum import StrEnum


class SocialClass(StrEnum):
    FARMER = "farmer"
    ARTISAN = "artisan"
    MERCHANT = "merchant"
    PRIEST = "priest"
    WARRIOR = "warrior"
    SCRIBE = "scribe"
    NOBLE = "noble"
    SERF_OR_SLAVE = "serf_or_slave"
    OUTCAST = "outcast"
    MONASTIC = "monastic"


class Commodity(StrEnum):
    FOOD = "food"
    ORE = "ore"
    GOODS = "goods"


class KnowledgeBranch(StrEnum):
    AGRICULTURE = "agriculture"
    METALLURGY = "metallurgy"
    SEAFARING = "seafaring"
    WRITING = "writing"
    ARCHITECTURE = "architecture"
    MEDICINE = "medicine"
    MAGIC = "magic"
    WARFARE = "warfare"
    ASTRONOMY = "astronomy"
    TRADE = "trade"
    SKY_NAVIGATION = "sky_navigation"
    SHIPBUILDING = "shipbuilding"
    GATE_LORE = "gate_lore"
    PATHFINDING = "pathfinding"
    VOID_LIVING = "void_living"
    IMMORTALITY = "immortality"
    BIOMANCY = "biomancy"
    FORBIDDEN = "forbidden"


COSMIC_BRANCHES = frozenset(
    {
        KnowledgeBranch.SKY_NAVIGATION,
        KnowledgeBranch.SHIPBUILDING,
        KnowledgeBranch.GATE_LORE,
        KnowledgeBranch.PATHFINDING,
        KnowledgeBranch.VOID_LIVING,
        KnowledgeBranch.IMMORTALITY,
        KnowledgeBranch.BIOMANCY,
        KnowledgeBranch.FORBIDDEN,
    }
)


class NaturalLaw(StrEnum):
    NONE = "none"
    IMMORTALITY = "immortality"
    SHORT_LIFE = "short_life"
    DEAD_RETURN = "dead_return"
    MAGIC_PRICE = "magic_price"
    WAR_BAN = "war_ban"
    BOUNTY = "bounty"
    DROUGHT = "drought"
    SEA_BAN = "sea_ban"
    ONE_LANGUAGE = "one_language"
    DISASTERS = "disasters"
    SOULS_REINCARNATE = "souls_reincarnate"


class ResourceMechanic(StrEnum):
    DECAYING = "decaying"
    ADDICTIVE = "addictive"
    SENTIENT = "sentient"
    DEPLETION_PRICE = "depletion_price"
    FIXED = "fixed"
    SACRED = "sacred"


class CreatureTrait(StrEnum):
    FLYING = "flying"
    VENOMOUS = "venomous"
    SOUL_EATER = "soul_eater"
    RADIANT = "radiant"
    FISSIPAROUS = "fissiparous"
    HIVE_MIND = "hive_mind"
    STONESKIN = "stoneskin"
    TIME_REWINDER = "time_rewinder"
    SHAPESHIFTER = "shapeshifter"
    MIND_READER = "mind_reader"
    ARMOURED = "armoured"
    BURROWING = "burrowing"
    AQUATIC = "aquatic"
    AMPHIBIOUS = "amphibious"
    PACK_HUNTER = "pack_hunter"
    AMBUSH_PREDATOR = "ambush_predator"
    REGENERATING = "regenerating"
    POISONOUS_FLESH = "poisonous_flesh"
    FIRE_BREATHING = "fire_breathing"
    COLD_BREATHING = "cold_breathing"
    ECHOLOCATION = "echolocation"
    CAMOUFLAGE = "camouflage"
    SWARM_BREEDER = "swarm_breeder"
    LONG_LIVED = "long_lived"
    MIMIC = "mimic"
    SPIRIT_SIGHT = "spirit_sight"
    IRON_EATING = "iron_eating"
    CROP_PEST = "crop_pest"
    PLAGUE_BEARER = "plague_bearer"
    SACRED_ANIMAL = "sacred_animal"


class CommunityRelationLabel(StrEnum):
    BLOOD_ENEMY = "blood_enemy"
    ENEMY = "enemy"
    COLD = "cold"
    NEUTRAL = "neutral"
    FRIEND = "friend"
    CLOSE_FRIEND = "close_friend"
    SIBLING = "sibling"
