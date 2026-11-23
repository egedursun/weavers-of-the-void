from enum import StrEnum


class PlaceKind(StrEnum):
    MOUNTAIN = "mountain"
    PEAK = "peak"
    PASS = "pass"
    FOREST = "forest"
    GROVE = "grove"
    RIVER = "river"
    FORD = "ford"
    LAKE = "lake"
    SPRING = "spring"
    CAVE = "cave"
    CAVERN_SYSTEM = "cavern_system"
    RUIN = "ruin"
    ISLAND = "island"
    SWAMP = "swamp"
    WELL = "well"
    VALLEY = "valley"
    CLIFF = "cliff"
    VOLCANO = "volcano"
    CRATER = "crater"
    BATTLEFIELD = "battlefield"
    BURIAL_GROUND = "burial_ground"
    LAIR = "lair"
    NEXUS = "nexus"
    SHRINE_SITE = "shrine_site"
    DEAD_GOD_SITE = "dead_god_site"
    MINE_SITE = "mine_site"
    HARBOUR_SITE = "harbour_site"
    CROSSROADS = "crossroads"
    WRECK_SITE = "wreck_site"
    MEGASTRUCTURE_RUIN = "megastructure_ruin"
    ANOMALY = "anomaly"
    DEBRIS_FIELD = "debris_field"
    REEF = "reef"
    GLACIER = "glacier"
    DUNES = "dunes"
    CANYON = "canyon"
    OASIS = "oasis"
    GEYSER = "geyser"
    WATERFALL = "waterfall"
    DELTA = "delta"
    PLATEAU = "plateau"
    SINKHOLE = "sinkhole"
    HOT_SPRING = "hot_spring"
    MESA = "mesa"
    NATURAL_ARCH = "natural_arch"
    TAR_PIT = "tar_pit"
    MEADOW = "meadow"
    ISTHMUS = "isthmus"


class SacredClass(StrEnum):
    PROFANE = "profane"
    NOTABLE = "notable"
    HOLY = "holy"


class PlaceHeight(StrEnum):
    FLAT = "flat"
    LOW = "low"
    HIGH = "high"


class SecretKind(StrEnum):
    HIDDEN_RESOURCE = "hidden_resource"
    BURIED_RELIC = "buried_relic"
    SEALED_SPIRIT = "sealed_spirit"
    LOST_KNOWLEDGE = "lost_knowledge"
    LOST_RITE = "lost_rite"
    UNDERWORLD_ENTRANCE = "underworld_entrance"
    HIDDEN_PEOPLE = "hidden_people"
    DORMANT_MIND = "dormant_mind"
    SEALED_REALM = "sealed_realm"
    HIDDEN_ROUTE = "hidden_route"
    SLEEPING_BEAST = "sleeping_beast"
    HIDDEN_GRAVE = "hidden_grave"
    HIDDEN_SPRING = "hidden_spring"
    DORMANT_DISEASE = "dormant_disease"
    FALSE_ACCOUNT = "false_account"


class DiscoveryMode(StrEnum):
    EXPLORER = "explorer"
    SEER = "seer"
    MINER = "miner"
    MYSTERY = "mystery"
    PLAYER = "player"
    SON = "son"


class SecretOrigin(StrEnum):
    LAND = "land"
    PLAYER = "player"
    SON = "son"
