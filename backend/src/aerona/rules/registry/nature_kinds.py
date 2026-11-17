from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

G = RuleGroup.CIVILIZATION
M = RuleGroup.MATERIALS


@dataclass(frozen=True)
class TraitRules:
    drift_pct: int = rule(10, 0, 100, G, "Share of the gap between a capacity and what its traits pull it toward that closes each epoch (%)")
    pull: int = rule(50, 0, 100, G, "Share of a trait's strength by which it pulls its holder's capacity away from the middle (%)")


@dataclass(frozen=True)
class OfficeDutyRules:
    unrest: int = rule(4, 0, 100, G, "Unrest a neglected office of oaths or judgement adds to each town at full neglect")
    piety_loss: int = rule(4, 0, 100, G, "Piety a neglected office of the sky, messages or memory takes from each community at full neglect")
    prosperity_loss: int = rule(4, 0, 100, G, "Prosperity a neglected office of making or healing takes from each community at full neglect")


@dataclass(frozen=True)
class BuildingRules:
    fire_pct: int = rule(100, 0, 300, M, "How strongly a building material's ignition point keeps fire from spreading (%)")
    strength_pct: int = rule(100, 0, 300, M, "How strongly a building material's resistance to blows and cuts holds walls against siege (%)")
