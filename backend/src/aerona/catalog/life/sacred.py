from aerona.domain.enums.sacred import DivinationQuestion, PetitionKind

COMMON_NEEDS = (PetitionKind.HEALING, PetitionKind.FERTILITY, PetitionKind.SAFE_PASSAGE, PetitionKind.PROSPERITY)

TRUE_OMEN_DIVINATION_QUESTIONS = frozenset({DivinationQuestion.BATTLE, DivinationQuestion.WAR})
