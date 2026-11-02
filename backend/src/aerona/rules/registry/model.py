from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class ModelRules:
    retry_attempts: int = rule(3, 1, 10, RuleGroup.AGENTS_AND_MODEL, "Total attempts on a transient model error (if the caller gives no rule of its own)")
    retry_wait_1: int = rule(2, 0, 600, RuleGroup.AGENTS_AND_MODEL, "Wait before retrying: after the 1st error (s)")
    retry_wait_2: int = rule(6, 0, 600, RuleGroup.AGENTS_AND_MODEL, "Wait before retrying: after the 2nd error (s)")
    retry_wait_3: int = rule(15, 0, 600, RuleGroup.AGENTS_AND_MODEL, "Wait before retrying: after the 3rd and later errors (s)")
    structured_timeout: int = rule(300, 10, 3600, RuleGroup.AGENTS_AND_MODEL, "Default timeout of a structured model call (s)")
    structured_max_steps: int = rule(8, 1, 20, RuleGroup.AGENTS_AND_MODEL, "Maximum model steps in a structured call")
    agent_timeout: int = rule(420, 30, 3600, RuleGroup.AGENTS_AND_MODEL, "Default timeout of an agent turn (s)")
    agent_max_steps: int = rule(10, 1, 100, RuleGroup.AGENTS_AND_MODEL, "Default step limit of an agent turn")
    sessions_per_turn_cap: int = rule(6, 1, 30, RuleGroup.AGENTS_AND_MODEL, "Maximum sessions in one agent turn (including restarts and continuations)")
    restart_attempts: int = rule(2, 0, 10, RuleGroup.AGENTS_AND_MODEL, "Number of restarts for a turn that crashed without leaving a trace")
    restart_wait: int = rule(3, 0, 600, RuleGroup.AGENTS_AND_MODEL, "Wait before a restart (s; multiplied by the attempt number)")
    max_continuations: int = rule(2, 0, 10, RuleGroup.AGENTS_AND_MODEL, "Maximum continuation sessions for an interrupted turn")
    continuation_wait: int = rule(3, 0, 600, RuleGroup.AGENTS_AND_MODEL, "Wait before a continuation session after a connection error (s)")
    continuation_action_summary_chars: int = rule(
        220, 40, 5000, RuleGroup.CONTEXT_BUDGETS, "Summary of each performed action in the continuation prompt (characters)"
    )
