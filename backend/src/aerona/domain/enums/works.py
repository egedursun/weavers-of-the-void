from enum import StrEnum


class WorksKind(StrEnum):
    ROAD = "road"
    BRIDGE = "bridge"
    CANAL = "canal"
    RAIL_LINE = "rail_line"
    AQUEDUCT = "aqueduct"
    DAM = "dam"
    DRAINAGE = "drainage"
    HARBOUR_WORKS = "harbour_works"
    WALLS = "walls"
    GRANARY_SYSTEM = "granary_system"
    SEWER = "sewer"
    POWER_LINE = "power_line"
    NETWORK_LINE = "network_line"
    TERRAFORMING_STAGE = "terraforming_stage"
    MEGASTRUCTURE_STAGE = "megastructure_stage"
    GROWN_WORKS = "grown_works"
    LIGHTHOUSE = "lighthouse"
    TERRACING = "terracing"
    IRRIGATION = "irrigation"
    TUNNEL = "tunnel"


class LabourRegime(StrEnum):
    PAID = "paid"
    CORVEE = "corvee"
    BOUND = "bound"
    MADE_MINDS = "made_minds"
    CONSTRUCTS = "constructs"


class WorksStatus(StrEnum):
    BUILDING = "building"
    FINISHED = "finished"
    FAILED = "failed"


class EnterpriseForm(StrEnum):
    MONOPOLY = "monopoly"
    ROYAL_WORKS = "royal_works"
    STATE_COMPANY = "state_company"
    LICENCE_HOLDER = "licence_holder"
    ARSENAL = "arsenal"
    MINT = "mint"
    GRANARY_BOARD = "granary_board"
    POST = "post"


class EnterpriseManagement(StrEnum):
    OFFICIAL = "official"
    COMPANY = "company"
    MADE_MIND = "made_mind"
