from aerona.db.tables.sons import SonRow
from aerona.prompts import PromptId, render
from aerona.prompts.contexts.son_turn import ReputationLineContext


def reputation_line(son: SonRow, passions: list[str]) -> str:
    if son.reputation_label is None:
        return ""
    context = ReputationLineContext(
        stance=son.reputation_label,
        love=son.reputation_love or 0,
        fear=son.reputation_fear or 0,
        oblivion=son.reputation_forgotten or 0,
        unanswered_prayers=son.reputation_unanswered or 0,
        passions=passions,
    )
    return render(PromptId.REPUTATION_LINE, context)
