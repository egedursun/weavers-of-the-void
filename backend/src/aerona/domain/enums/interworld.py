from enum import StrEnum


class CampaignStage(StrEnum):
    GATHERING = "gathering"
    TRANSIT = "transit"
    SUPREMACY = "supremacy"
    LANDING = "landing"
    HOLDING = "holding"
    WITHDRAWN = "withdrawn"


class MigrationCause(StrEnum):
    FLIGHT = "flight"
    LAND_HUNGER = "land_hunger"
    FAITH_CALL = "faith_call"
    EXILE = "exile"
    LABOUR_DRAW = "labour_draw"
    WORLD_DYING = "world_dying"
    RESETTLEMENT = "resettlement"


class MigrationReception(StrEnum):
    WELCOME = "welcome"
    QUOTA = "quota"
    REFUSAL = "refusal"


OPEN_CAMPAIGN = frozenset({CampaignStage.GATHERING, CampaignStage.TRANSIT, CampaignStage.SUPREMACY, CampaignStage.LANDING, CampaignStage.HOLDING})
