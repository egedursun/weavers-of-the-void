from aerona.db.session import Database
from aerona.events.bus import EventBus
from aerona.services.rule_changes import RuleDesk
from aerona.services.rules import RulesService


def harness_rule_desk(database: Database) -> RuleDesk:
    return RuleDesk(RulesService(database), database, EventBus(), lambda: False)
