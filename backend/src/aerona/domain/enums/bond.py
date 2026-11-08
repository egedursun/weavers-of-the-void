from enum import StrEnum


class BondKind(StrEnum):
    INSIDE = "inside"
    LIVES_IN = "lives_in"
    WORSHIPS = "worships"
    ENEMY = "enemy"
    ALLY = "ally"
    DESCENDS_FROM = "descends_from"
    PROTECTS = "protects"
    RULES = "rules"
    OWNS = "owns"
    BEAT = "beat"
    KILLED = "killed"
    CURSED = "cursed"
    BLESSED = "blessed"
    SOURCE_OF = "source_of"
    TELLS_OF = "tells_of"
    DESTROYED = "destroyed"
    LOVES = "loves"
    FEARS = "fears"
    HUNTS = "hunts"
    TRADES_WITH = "trades_with"
    PROPHESIES = "prophesies"
    CAUSED = "caused"
    CELEBRATES = "celebrates"
    FORBIDS = "forbids"
    SPEAKS = "speaks"
    PRODUCED = "produced"
    BUILT = "built"
    MIGRATED_TO = "migrated_to"
    DISCOVERED = "discovered"
    SOUL_DESCENDED_TO = "soul_descended_to"
    PARTY_TO = "party_to"
    MEMBER_OF = "member_of"
    KNOWS = "knows"
    PAYS_TRIBUTE = "pays_tribute"
    RELATED = "related"
    HOLDS_CAPTIVE = "holds_captive"
    SPY_NETWORK = "spy_network"
    PURSUES = "pursues"
    COMPANION = "companion"
    PET_OF = "pet_of"
    RIVAL = "rival"
    APPRENTICE_OF = "apprentice_of"
    COMMANDS = "commands"
    PART_OF = "part_of"
    PASSENGER_OF = "passenger_of"
    CAPTAIN_OF = "captain_of"
    TAMED = "tamed"
    TRUCE = "truce"
    OWES = "owes"
    TREATED_BY = "treated_by"
    PARENT_OF = "parent_of"
    SPOUSE_OF = "spouse_of"
    BETROTHED_TO = "betrothed_to"
    CONCUBINE_OF = "concubine_of"
    FOSTERED_BY = "fostered_by"
    SWORN_KIN = "sworn_kin"
    TELLS = "tells"
    FIXED_IN = "fixed_in"
    ADHERENT_OF = "adherent_of"
    PRACTISES = "practises"


class BondCategory(StrEnum):
    MECHANICAL = "mechanical"
    EVENT = "event"
    NARRATIVE = "narrative"


class LinkGroup(StrEnum):
    ALL = "all"
    TRAVEL = "travel"
    NO_LOCATION = "no_location"
    CONFLICT = "conflict"
    FAITH = "faith"
    LINEAGE = "lineage"
    KNOWLEDGE = "knowledge"


class PseudoLinkKind(StrEnum):
    ROUTE = "route"
    IN_WORLD = "in_world"
    CREATED = "created"


class BondState(StrEnum):
    ACTIVE = "active"
    PAST = "past"
    HIDDEN_REJECTED = "hidden_rejected"
    HIDDEN_CLOSED = "hidden_closed"


class BondRole(StrEnum):
    SIDE = "side"
    VICTOR = "victor"
    LOSER = "loser"
    COMMANDER = "commander"
    DUELED = "dueled"
    SPIRIT_BINDING = "spirit_binding"
    HOMELAND = "homeland"
    MENTIONED_IN_FATE = "mentioned_in_fate"
    FULFILLED_PROPHECY = "fulfilled_prophecy"


DERIVED_BOND_KINDS = frozenset({BondKind.TELLS, BondKind.FIXED_IN, BondKind.ADHERENT_OF, BondKind.PRACTISES})
VISIBLE_BOND_STATES = frozenset({BondState.ACTIVE, BondState.PAST})
ROLE_BOND_KINDS = frozenset({BondKind.PARTY_TO, BondKind.RELATED})
SYMMETRIC_BOND_KINDS = frozenset(
    {
        BondKind.ENEMY,
        BondKind.ALLY,
        BondKind.TRADES_WITH,
        BondKind.TRUCE,
        BondKind.COMPANION,
        BondKind.RIVAL,
        BondKind.SPOUSE_OF,
        BondKind.BETROTHED_TO,
        BondKind.SWORN_KIN,
    }
)
KIN_BOND_KINDS = (
    BondKind.PARENT_OF,
    BondKind.SPOUSE_OF,
    BondKind.CONCUBINE_OF,
    BondKind.FOSTERED_BY,
    BondKind.SWORN_KIN,
    BondKind.BETROTHED_TO,
)
