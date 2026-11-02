from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class ArchiveRules:
    event_epochs: int = rule(3, 1, 100, RuleGroup.ATLAS_ARCHIVE, "Epochs an event goes unmentioned before passing into history")
    prophecy_epochs: int = rule(4, 1, 100, RuleGroup.ATLAS_ARCHIVE, "Epochs after which a prophecy passes into history")
    spirit_epochs: int = rule(4, 1, 100, RuleGroup.ATLAS_ARCHIVE, "Epochs after which a spirit passes into history")
    settlement_epochs: int = rule(5, 1, 100, RuleGroup.ATLAS_ARCHIVE, "Epochs after which a settlement passes into history")
    item_epochs: int = rule(6, 1, 100, RuleGroup.ATLAS_ARCHIVE, "Epochs after which an item passes into history")
    tradition_epochs: int = rule(8, 1, 100, RuleGroup.ATLAS_ARCHIVE, "Epochs after which a tradition passes into history")
    importance_threshold: int = rule(60, 0, 500, RuleGroup.ATLAS_ARCHIVE, "Records with importance above this never pass into history")
    w_power_level: int = rule(10, 0, 100, RuleGroup.ATLAS_ARCHIVE, "Importance: per power level")
    w_link: int = rule(3, 0, 50, RuleGroup.ATLAS_ARCHIVE, "Importance: per link")
    w_link_cap: int = rule(40, 0, 500, RuleGroup.ATLAS_ARCHIVE, "Importance: maximum from links")
    w_mention: int = rule(2, 0, 50, RuleGroup.ATLAS_ARCHIVE, "Importance: per mention in the chronicle")
    w_mention_cap: int = rule(30, 0, 500, RuleGroup.ATLAS_ARCHIVE, "Importance: maximum from mentions")
    w_favorite: int = rule(50, 0, 500, RuleGroup.ATLAS_ARCHIVE, "Importance: bonus for a favourite record")
    w_freshness: int = rule(20, 0, 500, RuleGroup.ATLAS_ARCHIVE, "Importance: freshness bonus for a recently mentioned record")
    w_freshness_decay: int = rule(4, 0, 500, RuleGroup.ATLAS_ARCHIVE, "Importance: decrease of the freshness bonus per epoch")
    w_population_log: int = rule(4, 0, 100, RuleGroup.ATLAS_ARCHIVE, "Importance: per log10 of population")
    w_population_cap: int = rule(20, 0, 500, RuleGroup.ATLAS_ARCHIVE, "Importance: maximum from population")
    w_not_living_penalty: int = rule(15, 0, 500, RuleGroup.ATLAS_ARCHIVE, "Importance: subtracted from a record that is no longer alive")
    dead_epochs: int = rule(2, 0, 100, RuleGroup.ATLAS_ARCHIVE, "Epochs a dead, destroyed or fulfilled record goes unmentioned before passing into history")
