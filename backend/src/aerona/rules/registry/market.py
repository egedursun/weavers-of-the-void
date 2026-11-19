from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule, span


@dataclass(frozen=True)
class MarketRules(Spanned):
    flow_price_gap_pct: int = rule(
        150, 100, 10000, RuleGroup.ECONOMY, "Trade flow: goods move when the buyer's price is at least this share of the seller's (%)"
    )
    flow_reserve: int = rule(40, 0, 100000, RuleGroup.ECONOMY, "Trade flow: units of a good the seller always keeps in its stores, per 1000 of its people")
    flow_share_pct: int = rule(15, 0, 100, RuleGroup.ECONOMY, "Trade flow: share of the seller's surplus that moves per epoch (%)")
    flow_cap: int = rule(2000, 0, 10000000, RuleGroup.ECONOMY, "Trade flow: most units of one good moving along one road (units per year)")
    famine_gap_pct: int = rule(250, 100, 10000, RuleGroup.ECONOMY, "Trade flow: a grain purchase is chronicled as a famine purchase above this price gap (%)")
    flow_prosperity: int = rule(2, 0, 100, RuleGroup.ECONOMY, "Trade flow: prosperity a seller gains for selling a good")
    credit_threshold: int = rule(25, 0, 100, RuleGroup.ECONOMY, "Trade flow: a buyer below this wealth or prosperity buys on credit (a debt is born)")
    credit_chance: int = rule(12, 0, 100, RuleGroup.ECONOMY, "Trade flow: chance a buyer who could pay still buys a large load on credit (%)")
    credit_term_years: int = span(3, 1, 1250, RuleGroup.ECONOMY, "Term of a credit debt (years)")
    credit_divisor: int = rule(3, 1, 1000, RuleGroup.ECONOMY, "Size of a credit debt: the moved amount divided by this")
    debt_patience_years: int = span(1, 0, 2500, RuleGroup.ECONOMY, "Debt: years the creditor waits after the term before acting")
    debt_forgive_relation: int = rule(30, -100, 100, RuleGroup.ECONOMY, "Debt: a creditor whose relation to the debtor is at least this forgives the debt")
    debt_tribute_chance: int = rule(40, 0, 100, RuleGroup.ECONOMY, "Debt: chance a stronger creditor turns an overdue debt into tribute (%)")
    debt_seize_chance: int = rule(50, 0, 100, RuleGroup.ECONOMY, "Debt: chance the creditor seizes one of the debtor's resources (%)")
    debt_war_chance: int = rule(25, 0, 100, RuleGroup.ECONOMY, "Debt: chance the creditor declares the debtor its enemy over an overdue debt (%)")
    debt_expiry_years: int = span(100, 1, 25000, RuleGroup.ECONOMY, "Debt: an unclosed debt lapses this many years after its term")
    debt_forgive_gain: int = rule(10, 0, 100, RuleGroup.ECONOMY, "Relation gained when a debt is forgiven or written off")
    debt_grudge: int = rule(15, 0, 100, RuleGroup.ECONOMY, "Relation lost when a debt turns into tribute, seizure or war")
    price_scarce_abundance: int = rule(20, 0, 100, RuleGroup.ECONOMY, "Resource price: a resource below this abundance rises in value")
    price_plenty_abundance: int = rule(70, 0, 100, RuleGroup.ECONOMY, "Resource price: an owned resource above this abundance falls in value")
    price_step: int = rule(2, 0, 100, RuleGroup.ECONOMY, "Resource price: most a value moves per epoch")
    price_floor: int = rule(10, 0, 100, RuleGroup.ECONOMY, "Resource price: plenty never pushes the value below this")
    demand_population: int = rule(25000, 1, 100000000, RuleGroup.ECONOMY, "Depletion: every this much owner population puts one unit of demand on a resource")
    depletion_demand: int = rule(2, 0, 1000, RuleGroup.ECONOMY, "Depletion: least demand for a resource to run out")
    depletion_abundance: int = rule(8, 0, 100, RuleGroup.ECONOMY, "Depletion: a resource at or below this abundance (with enough demand) starts running out")
    depletion_chance: int = rule(25, 0, 100, RuleGroup.ECONOMY, "Depletion: chance a running-out resource is exhausted this epoch (%)")
    depletion_loss: int = rule(8, 0, 100, RuleGroup.ECONOMY, "Depletion: prosperity and wealth its owners lose when a resource is exhausted")
    depleted_clawback: int = rule(
        3, 0, 100, RuleGroup.ECONOMY, "Exhausted resource: abundance taken back from the general regrowth (the rest is its refill speed)"
    )
    refill_abundance: int = rule(30, 1, 100, RuleGroup.ECONOMY, "An exhausted resource is usable again once it refills to this abundance")
    bondage_share_pct: int = rule(3, 0, 100, RuleGroup.ECONOMY, "Debt law of bondage: share of a defaulting debtor's free people bound into serfdom (%)")
    bondage_labour_gain: int = rule(4, 0, 100, RuleGroup.ECONOMY, "Debt law of bondage: prosperity the creditor gains from the bound labour")
    prison_unrest: int = rule(6, 0, 100, RuleGroup.ECONOMY, "Debt law of prison: unrest in the debtor's settlement when its notable is jailed for the debt")
    jubilee_relation: int = rule(
        5, 0, 100, RuleGroup.ECONOMY, "Debt law of jubilee: relation the debtor gains toward the creditor when the jubilee wipes the debt"
    )
    currency_trust_pct: int = rule(50, 0, 100, RuleGroup.ECONOMY, "Share of a debt's weight lost when the coin it is counted in has lost all trust (%)")

    @property
    def credit_term(self) -> int:
        return self.epochs(self.credit_term_years)

    @property
    def debt_patience(self) -> int:
        return self.epochs(self.debt_patience_years)

    @property
    def debt_expiry(self) -> int:
        return self.epochs(self.debt_expiry_years)
