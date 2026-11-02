from aerona.prompts import PromptId, render
from aerona.prompts.contexts.base import EmptyContext, RulesContext
from aerona.rules.registry import Rules


def cliche_ban() -> str:
    return render(PromptId.CLICHE_BAN, EmptyContext())


def image_prompt_rules() -> str:
    return render(PromptId.IMAGE_PROMPT_RULES, EmptyContext())


def section_keys_rule() -> str:
    return render(PromptId.SECTION_KEYS_RULE, EmptyContext())


def verdict_criteria() -> str:
    return render(PromptId.VERDICT_CRITERIA, EmptyContext())


def rationale_rule(rules: Rules) -> str:
    return render(PromptId.RATIONALE_RULE, RulesContext(rules=rules))
