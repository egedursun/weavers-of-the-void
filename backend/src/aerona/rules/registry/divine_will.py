from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

C = RuleGroup.CONTEXT_BUDGETS
A = RuleGroup.AGENTS_AND_MODEL


@dataclass(frozen=True)
class DivineWillRules:
    remembered_cycles: int = rule(
        10, 1, 100, C, "Completed exchanges of the session the Divine Will keeps in mind, each a question and its final answer with every step between"
    )
    max_steps: int = rule(40, 5, 200, A, "Model replies one exchange with the Divine Will may take")
    page_tokens: int = rule(6000, 500, 50000, C, "Token budget of one page of a Divine Will tool result; the rest is read page by page")
    search_page: int = rule(12, 3, 100, C, "Hits on one page of a Divine Will search")
    costly_essence: int = rule(25, 0, 100000, A, "Essence at or above which an act of the Divine Will asks the player first")
    forecast_max_epochs: int = rule(3, 1, 10, A, "Most epochs a Divine Will forecast may live on its copy of the world")
    index_batch: int = rule(16, 1, 256, A, "Passages the Divine Will index embeds in one batch")
