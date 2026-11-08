from aerona.prompts import PromptId, render
from aerona.prompts.contexts.base import EmptyContext, RulesContext
from aerona.rules.registry import Rules


def image_prompt_rules() -> str:
    return render(PromptId.IMAGE_PROMPT_RULES, EmptyContext())


def rationale_rule(rules: Rules) -> str:
    return render(PromptId.RATIONALE_RULE, RulesContext(rules=rules))
