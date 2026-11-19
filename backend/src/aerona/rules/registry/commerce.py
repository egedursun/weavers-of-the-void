from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule

S = RuleGroup.ECONOMY


@dataclass(frozen=True)
class CommerceRules(Spanned):
    retail_margin_pct: int = rule(20, 0, 200, S, "Margin a retail tier or shop adds to what passes through it")
    wholesale_margin_pct: int = rule(10, 0, 200, S, "Margin a wholesale tier adds to what passes through it")
    promotion_demand_pct: int = rule(10, 0, 100, S, "Reputation a promotion at full reach adds to its brand each epoch, in tenths")
    false_claim_trust_loss: int = rule(20, 0, 100, S, "Reputation and honour lost when a false claim of a promotion is found out")
    lease_default_chance_pct: int = rule(5, 0, 100, S, "Chance each epoch that a lessee fails to pay the rent")
    no_shop_basket_pct: int = rule(15, 0, 100, S, "Share of worn goods a town without shops goes without")
    tier_income_pct: int = rule(5, 0, 100, S, "Share of a market's trade in a good that reaches the holders of its tiers as income, before margin")
    corner_share: int = rule(80, 0, 100, S, "Share of a tier one holder needs to corner it")
    corner_margin: int = rule(10, 0, 200, S, "Margin a cornered tier adds each epoch")
    corner_unrest: int = rule(3, 0, 100, S, "Unrest a cornered tier raises in its town each epoch")
    shop_turnover: int = rule(4, 0, 10000, S, "Stock a shop sells each year, before the pace of its form")
    shop_credit_prosperity: int = rule(1, 0, 100, S, "Prosperity a town gains each epoch from the credit its shops extend, for each ten of credit, in tenths")
    upkeep_cost: int = rule(1, 0, 100, S, "Wealth the party bound to upkeep pays each epoch for a leased thing")
