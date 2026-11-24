from enum import StrEnum


class PopulationAim(StrEnum):
    GROW = "grow"
    HOLD = "hold"
    SHRINK = "shrink"
    REBALANCE_AGE = "rebalance_age"
    REBALANCE_CLASS = "rebalance_class"
    SETTLE_LAND = "settle_land"
    EMPTY_LAND = "empty_land"
    KEEP_KIND = "keep_kind"
    MIX_KINDS = "mix_kinds"
    NONE = "none"


class PopulationInstrument(StrEnum):
    BIRTH_REWARD = "birth_reward"
    BIRTH_TAX = "birth_tax"
    UNION_LAW = "union_law"
    CHILD_LIMIT = "child_limit"
    CHILD_SUPPORT = "child_support"
    INHERITANCE_RULE = "inheritance_rule"
    SETTLEMENT_GRANT = "settlement_grant"
    MIGRATION_PERMIT = "migration_permit"
    MIGRATION_BAN = "migration_ban"
    EXPULSION = "expulsion"
    RESETTLEMENT = "resettlement"
    RECRUITMENT_ABROAD = "recruitment_abroad"
    HEALTH_CAMPAIGN = "health_campaign"
    FAITH_TEACHING = "faith_teaching"
    MADE_BIRTH = "made_birth"
    IMMUNISATION = "immunisation"
    SANITATION = "sanitation"
