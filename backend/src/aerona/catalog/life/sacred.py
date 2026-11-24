from collections.abc import Callable, Mapping

from aerona.core.total import total
from aerona.domain.enums.mind import DreamKind, MemoryKind
from aerona.domain.enums.sacred import DivinationQuestion, PetitionKind, SacramentKind
from aerona.rules.registry import Rules

COMMON_NEEDS = (PetitionKind.HEALING, PetitionKind.FERTILITY, PetitionKind.SAFE_PASSAGE, PetitionKind.PROSPERITY)

TRUE_OMEN_DIVINATION_QUESTIONS = frozenset({DivinationQuestion.BATTLE, DivinationQuestion.WAR})
PERSONAL_QUESTIONS = frozenset({DivinationQuestion.CORONATION, DivinationQuestion.WEDDING, DivinationQuestion.ILLNESS})

PETITION_GRANTS: Mapping[PetitionKind, Callable[[Rules], int]] = total(
    PetitionKind,
    {
        PetitionKind.HEALING: lambda rules: rules.petitions.healing_grant_pct,
        PetitionKind.HARVEST: lambda rules: rules.petitions.harvest_grant_pct,
        PetitionKind.FERTILITY: lambda rules: rules.petitions.fertility_grant_pct,
        PetitionKind.SAFE_PASSAGE: lambda rules: rules.petitions.safe_passage_grant_pct,
        PetitionKind.PROSPERITY: lambda rules: rules.petitions.prosperity_grant_pct,
        PetitionKind.SUIT: lambda rules: rules.petitions.suit_grant_pct,
        PetitionKind.RAIN: lambda rules: rules.petitions.rain_grant_pct,
        PetitionKind.PROTECTION: lambda rules: rules.petitions.protection_grant_pct,
        PetitionKind.VENGEANCE: lambda rules: rules.petitions.vengeance_grant_pct,
        PetitionKind.FINDING: lambda rules: rules.petitions.finding_grant_pct,
        PetitionKind.JUSTICE: lambda rules: rules.petitions.justice_grant_pct,
    },
)

WRONGS = (MemoryKind.BETRAYED_ME, MemoryKind.CHEATED_US)

FORESEEING_DREAMS = frozenset({DreamKind.PROPHETIC, DreamKind.VISITATION})
LATER_SACRAMENTS = frozenset({SacramentKind.PENANCE, SacramentKind.COMMUNION})
SHARED_MEAL_AFTER = (SacramentKind.INITIATION, SacramentKind.ORDINATION)
TARGETED_PETITIONS = frozenset({PetitionKind.VENGEANCE, PetitionKind.JUSTICE})
