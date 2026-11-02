from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class LedgerRules:
    keep_epochs: int = rule(6, 1, 200, RuleGroup.RECORDS, "Epochs kept in the action ledger")
