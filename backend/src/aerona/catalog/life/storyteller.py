from aerona.domain.enums.ages import ArcRole, ArcTemplate
from aerona.domain.enums.collective import StoryletId

OPPOSED = (ArcRole.FOE, ArcRole.RIVAL)


ADVANCED_BY: dict[StoryletId, frozenset[ArcTemplate]] = {
    StoryletId.LOST_HEIR: frozenset({ArcTemplate.EXILE_AND_RETURN, ArcTemplate.RAGS_TO_RICHES, ArcTemplate.COMING_OF_AGE}),
    StoryletId.HOARDED_STORE: frozenset({ArcTemplate.CORRUPTION, ArcTemplate.REDEMPTION}),
    StoryletId.BEAST_DEMAND: frozenset({ArcTemplate.QUEST, ArcTemplate.REVENGE, ArcTemplate.APOTHEOSIS}),
    StoryletId.FORBIDDEN_TEXT: frozenset({ArcTemplate.CORRUPTION, ArcTemplate.MENTOR_AND_HEIR, ArcTemplate.APOTHEOSIS}),
    StoryletId.DEFILED_SITE: frozenset({ArcTemplate.REDEMPTION, ArcTemplate.TRAGEDY, ArcTemplate.CORRUPTION}),
    StoryletId.WEDDING_CHALLENGE: frozenset({ArcTemplate.FORBIDDEN_LOVE, ArcTemplate.RIVALRY, ArcTemplate.FOUNDING}),
    StoryletId.DYING_RULER: frozenset({ArcTemplate.RISE_AND_FALL, ArcTemplate.TRAGEDY, ArcTemplate.FALL_OF_A_HOUSE, ArcTemplate.MENTOR_AND_HEIR}),
    StoryletId.INSULTED_ENVOY: frozenset({ArcTemplate.RIVALRY, ArcTemplate.REVENGE, ArcTemplate.EXILE_AND_RETURN}),
}

ADVANCE_ARC_ROLES = (ArcRole.FOE, ArcRole.RIVAL)
