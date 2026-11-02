from collections.abc import Sequence

from aerona.prompts.budget import BudgetSection, budget, sectioned_budget
from aerona.rules.registry import Rules


def fit(text: str, limit: int, hint: str, rules: Rules) -> str:
    return budget(text, limit, hint, rules.context.budget_trim_min_chars)


def fit_sections(sections: Sequence[tuple[str, str]], limit: int, rules: Rules) -> str:
    floor = rules.context.section_min_chars
    return sectioned_budget([BudgetSection(text, floor, hint) for text, hint in sections], limit, rules.context.budget_trim_min_chars)
