from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class BackupRules:
    recent_epoch_backups: int = rule(10, 1, 200, RuleGroup.BACKUPS, "Most recent epoch backups kept")
    milestone_epoch_multiple: int = rule(10, 1, 100, RuleGroup.BACKUPS, "Backups of epochs that are multiples of this are always kept")
    manual_backups: int = rule(30, 1, 500, RuleGroup.BACKUPS, "Manual backups kept")
    safety_backups_per_kind: int = rule(5, 1, 100, RuleGroup.BACKUPS, "Kept per safety-backup kind")
    secondary_target_backups: int = rule(20, 1, 1000, RuleGroup.BACKUPS, "Kept on the secondary backup target (AERONA_YEDEK2)")
