from aerona.prompts.budget import budget
from aerona.rules.registry import Rules


def fit(text: str, limit: int, hint: str, rules: Rules) -> str:
    return budget(text, limit, hint, rules.context.budget_trim_min_chars)
