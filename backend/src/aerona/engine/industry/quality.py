from aerona.constants.units import PERCENT
from aerona.domain.enums.industry import QualityTier
from aerona.rules.registry import Rules

TIERS = tuple(QualityTier)
COMMON_INDEX = TIERS.index(QualityTier.COMMON)
FLOOR = 0.25


def thresholds(rules: Rules) -> tuple[tuple[QualityTier, int], ...]:
    table = rules.quality
    return (
        (QualityTier.ARTIFACT, table.artifact_at),
        (QualityTier.MASTERWORK, table.masterwork_at),
        (QualityTier.EXCEPTIONAL, table.exceptional_at),
        (QualityTier.SUPERIOR, table.superior_at),
        (QualityTier.FINE, table.fine_at),
        (QualityTier.COMMON, table.common_at),
    )


def tier_of(rules: Rules, quality: int) -> QualityTier:
    for tier, floor in thresholds(rules):
        if quality >= floor:
            return tier
    return QualityTier.POOR


def at_least(rules: Rules, quality: int, tier: QualityTier) -> bool:
    return TIERS.index(tier_of(rules, quality)) >= TIERS.index(tier)


def premium(rules: Rules, quality: int) -> float:
    steps = TIERS.index(tier_of(rules, quality)) - COMMON_INDEX
    return max(FLOOR, 1 + steps * rules.quality.premium_step_pct / PERCENT)
