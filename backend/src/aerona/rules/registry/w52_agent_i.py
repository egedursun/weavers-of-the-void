from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

H = RuleGroup.HEROES_AND_MORTALS


@dataclass(frozen=True)
class GiftedRules:
    conscript_share_pct: int = rule(50, 0, 100, H, "Share of the gifted who draw on a source under a conscripting law that the realm sends to serve (%)")
    exploited_grievance: int = rule(15, 0, 100, H, "Stress the gifted of a people that exploits them gain each epoch")
    exploited_profit: int = rule(2, 0, 100, H, "Prosperity a town gains each epoch for each gifted one its people exploit, up to five")
    envy_theft_pct: int = rule(100, 0, 400, H, "Added chance of a power being taken from a gifted one among a people that envies them (%)")
    pity_fear_cut: int = rule(20, 0, 100, H, "Weight a doctrine of pity takes from a people's fear of the gifted")
    power_tax: int = rule(5, 0, 10000, H, "Coin in treasury a gifted one pays the realm each time it draws on a source the law taxes")
