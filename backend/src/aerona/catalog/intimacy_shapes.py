from aerona.domain.enums.intimacy import LegitimacyPath, NormEnforcer, PostnatalCustom, RestraintOccasion

POSTNATAL_RECOVERY_PCT: dict[PostnatalCustom, int] = {
    PostnatalCustom.REST_PERIOD: 120,
    PostnatalCustom.SECLUSION: 100,
    PostnatalCustom.KIN_CARE: 110,
    PostnatalCustom.SPECIALIST_CARE: 150,
    PostnatalCustom.RITE: 90,
    PostnatalCustom.NONE: 0,
    PostnatalCustom.PARTNER_REST: 115,
}

OCCASION_ODDS_PCT: dict[RestraintOccasion, int] = {
    RestraintOccasion.ALWAYS: 100,
    RestraintOccasion.BEFORE_BATTLE: 100,
    RestraintOccasion.SEASON: 50,
    RestraintOccasion.RITE: 25,
}

ENFORCER_FORCE_PCT: dict[NormEnforcer, int] = {
    NormEnforcer.KIN: 60,
    NormEnforcer.FAITH: 80,
    NormEnforcer.LAW: 100,
    NormEnforcer.NONE: 0,
}

PATH_COST_PCT: dict[LegitimacyPath, int] = {
    LegitimacyPath.RECOGNITION: 100,
    LegitimacyPath.ADOPTION: 120,
    LegitimacyPath.PAYMENT: 100,
    LegitimacyPath.RITE: 80,
    LegitimacyPath.NONE: 0,
}
