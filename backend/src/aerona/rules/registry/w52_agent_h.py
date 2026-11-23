from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

K = RuleGroup.CIVILIZATION


@dataclass(frozen=True)
class GreatPersonsRules:
    scholar_weight: int = rule(50, 0, 100, K, "How readily great scholars rise; 50 keeps the points their field gathers")
    artist_weight: int = rule(50, 0, 100, K, "How readily great artists rise; 50 keeps the points their field gathers")
    general_weight: int = rule(50, 0, 100, K, "How readily great generals rise; 50 keeps the points their field gathers")
    prophet_weight: int = rule(50, 0, 100, K, "How readily great prophets rise; 50 keeps the points their field gathers")
    engineer_weight: int = rule(50, 0, 100, K, "How readily great engineers rise; 50 keeps the points their field gathers")
    merchant_weight: int = rule(50, 0, 100, K, "How readily great merchants rise; 50 keeps the points their field gathers")
    explorer_weight: int = rule(50, 0, 100, K, "How readily great explorers rise; 50 keeps the points their field gathers")
    healer_weight: int = rule(50, 0, 100, K, "How readily great healers rise; 50 keeps the points their field gathers")
    lawgiver_weight: int = rule(50, 0, 100, K, "How readily great lawgivers rise; 50 keeps the points their field gathers")
    teacher_weight: int = rule(50, 0, 100, K, "How readily great teachers rise; 50 keeps the points their field gathers")
    reformer_weight: int = rule(50, 0, 100, K, "How readily great reformers rise; 50 keeps the points their field gathers")
    healer_progress: int = rule(30, 0, 100, K, "Progress a great healer's school gives an open technique of medicine or natural history")
    lawgiver_legitimacy: int = rule(10, 0, 100, K, "Legitimacy a great lawgiver's code gives their realm")
    lawgiver_progress: int = rule(30, 0, 100, K, "Progress a great lawgiver gives written or codified law where it is not yet known")
    teacher_literacy: int = rule(8, 0, 100, K, "Literacy a great teacher's pupils give their people")
    teacher_progress: int = rule(20, 0, 100, K, "Progress a great teacher gives an open technique of writing, language lore or mathematics")
    reformer_calm: int = rule(15, 0, 100, K, "Unrest a great reformer's movement eases in their town")
    reformer_shaken: int = rule(5, 0, 100, K, "Legitimacy a great reformer's movement costs the realm whose order it changes")
