from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule

S = RuleGroup.MARKETS_AND_MONEY


@dataclass(frozen=True)
class MonetaryRules(Spanned):
    rate_to_interest_pct: int = rule(100, 0, 300, S, "How much of each point of the policy rate above or below the neutral rate reaches lenders' interest (%)")
    price_per_rate_point_pct: int = rule(
        2, 0, 20, S, "How far prices rise for each point the applied rate stands below the neutral rate, and fall for each point above (%)"
    )
    state_issue_trust_loss: int = rule(5, 0, 50, S, "Trust a currency loses in an epoch its authority issues money to fund the state")
    peg_reserve_floor_pct: int = rule(20, 0, 100, S, "Share of the reserves held when a peg was set under which the peg breaks (%)")
    run_spread_pct: int = rule(30, 0, 100, S, "Share of their wealth the other banks of a currency lose when a bank fails with no lender of last resort (%)")
    neutral_rate: int = rule(5, 0, 100, S, "Policy rate at which prices and borrowing are neither pushed up nor held down")
    state_issue_pct: int = rule(10, 0, 100, S, "Share by which issuing money to fund the state raises a currency's supply in an epoch (%)")
    state_issue_coin: int = rule(40, 0, 100000, S, "Coin the state gains in an epoch its authority issues money for it")
    rate_step: int = rule(1, 0, 20, S, "Points an authority moves its policy rate in an epoch toward what its aim asks")
    cheap_rate: int = rule(1, 0, 100, S, "Policy rate an authority aiming at cheap credit moves toward")
    growth_rate_gap: int = rule(2, 0, 50, S, "Points below the neutral rate an authority aiming at growth moves toward")
    trust_rate_pct: int = rule(
        10, 0, 100, S, "Points above the neutral rate an authority aiming at a stable value adds for each ten points of trust its currency lacks below full (%)"
    )
    peg_defence_cost: int = rule(4, 0, 1000, S, "Reserves an authority spends in an epoch for each point its currency strays from its peg")
    peg_shock_rate: int = rule(10, 0, 100, S, "Points the policy rate jumps when a peg breaks")
    peg_shock_trust: int = rule(15, 0, 100, S, "Trust a currency loses when its peg breaks")
    reserve_gain: int = rule(5, 0, 100000, S, "Reserves an authority gathers in an epoch")
    rescue_cost: int = rule(50, 0, 100000, S, "Reserves an authority spends to save a failing bank")
    rescue_wealth: int = rule(30, 0, 100, S, "Wealth a bank saved by a lender of last resort is left with")
    rescue_supply_pct: int = rule(5, 0, 100, S, "Share by which saving a bank raises a currency's supply (%)")
    rescue_trust_loss: int = rule(3, 0, 50, S, "Trust a currency loses when its authority saves a bank")
    borrow_per_rate_point_pct: int = rule(
        5, 0, 50, S, "How far borrowing grows for each point the applied rate stands below the neutral rate, and shrinks for each point above (%)"
    )
    reserve_lending_pct: int = rule(50, 0, 100, S, "How far a full reserve requirement holds banks back from lending (%)")
    run_reserve_step: int = rule(5, 0, 100, S, "Points an authority raises the reserve its banks must hold after a run spreads among them")
    bend_chance_pct: int = rule(
        60, 0, 100, S, "Chance in an epoch that a ruler at war or before an election bends an authority with no independence to fund the state (%)"
    )
    resist_favour_loss: int = rule(5, 0, 100, S, "Standing an independent authority loses with the ruler whose call to issue it refuses")
