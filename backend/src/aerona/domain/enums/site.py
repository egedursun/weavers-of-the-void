from enum import StrEnum


class SiteRoomKind(StrEnum):
    GATE = "gate"
    HALL = "hall"
    STAIR = "stair"
    CELL = "cell"
    CHAMBER = "chamber"
    VAULT = "vault"
    SHRINE = "shrine"
    LAIR = "lair"
    LIBRARY = "library"
    ARMOURY = "armoury"
    CRYPT = "crypt"
    LABORATORY = "laboratory"
    HOUSE = "house"
    STORE = "store"
    HEART = "heart"
    CISTERN = "cistern"
    FORGE = "forge"


class SiteChallenge(StrEnum):
    NONE = "none"
    TRAP = "trap"
    GUARDIAN = "guardian"
    PUZZLE = "puzzle"
    HAZARD = "hazard"
    SEAL = "seal"
    MAZE = "maze"


class RoomContentKind(StrEnum):
    ITEM = "item"
    SPIRIT = "spirit"
    BEAST = "beast"
    TRAP = "trap"
    MIND = "mind"
    RELIC = "relic"
    REALM_GATE = "realm_gate"
    RECORDS = "records"


class ExcavationStage(StrEnum):
    SURVEY = "survey"
    CLEARING = "clearing"
    DIGGING = "digging"
    DEEP_LAYERS = "deep_layers"
    INNER_SANCTUM = "inner_sanctum"


class ExcavationStatus(StrEnum):
    OPEN = "open"
    STALLED = "stalled"
    FINISHED = "finished"
    COLLAPSED = "collapsed"
    ABANDONED = "abandoned"


class ExcavationRisk(StrEnum):
    NONE = "none"
    CURSE = "curse"
    SPIRIT = "spirit"
    COLLAPSE = "collapse"
    FLOODING = "flooding"
    GAS = "gas"
    DISEASE = "disease"


class ExcavationFind(StrEnum):
    NOTHING = "nothing"
    ARTIFACT = "artifact"
    BOOK = "book"
    TECHNIQUE = "technique"
    REGALIA = "regalia"
    ROUTE_MAP = "route_map"
    WAKING = "waking"
    REMAINS = "remains"
    RECORDS = "records"


class BattlefieldFeature(StrEnum):
    MASS_GRAVE = "mass_grave"
    SALVAGE_FIELD = "salvage_field"
    EARTHWORKS = "earthworks"
    ORDNANCE = "ordnance"
    MEMORIAL = "memorial"
