from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class NotificationsRules:
    read_kept: int = rule(1500, 10, 100000, RuleGroup.NOTIFICATIONS, "Read notifications kept")
    total_cap: int = rule(5000, 100, 100000, RuleGroup.NOTIFICATIONS, "Total notification cap")
    toast_min_importance: int = rule(
        3, 1, 5, RuleGroup.NOTIFICATIONS, "Notifications of this importance and above also appear as a short on-screen toast (5: none)"
    )
