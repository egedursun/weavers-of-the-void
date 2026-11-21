from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule, span

S = RuleGroup.ORGANISATIONS


@dataclass(frozen=True)
class GovernanceRules(Spanned):
    term_years: int = span(10, 1, 500, S, "Years a head of an organisation serves before the selection rule runs again")
    quorum_pct: int = rule(50, 1, 100, S, "Share of the votes of a decision body a motion needs to pass, for a new body (%)")
    head_defiance_trust_loss: int = rule(15, 0, 100, S, "Trust a head loses with the body when it acts against the body's decision")
    removal_trust: int = rule(30, 0, 100, S, "Trust below which a decision body removes its head")
    new_head_trust: int = rule(60, 0, 100, S, "Trust a newly chosen head starts with")
    clique_min_seats: int = rule(3, 1, 100, S, "Seats a decision body needs before cliques form within it")
    clique_form_chance_pct: int = rule(25, 0, 100, S, "Chance in an epoch that a clique forms in a body with enough seats (%)")
    challenge_margin: int = rule(15, 0, 100, S, "Trust above the removal line under which a new clique aims at the headship")
    split_turn_chance_pct: int = rule(30, 0, 100, S, "Chance in an epoch that a clique that lost its vote or its candidate turns to leaving (%)")
    split_clique_threshold: int = rule(35, 0, 100, S, "Strength a clique needs, in votes of the body, to split away and found a rival")
    takeover_premium_pct: int = rule(30, 0, 300, S, "Price above its worth a hostile bid offers, and a resisted bidder must add (%)")
    research_progress_per_staff: int = rule(2, 0, 50, S, "Progress toward its goal each of a research effort's staff adds in an epoch")
    research_cost_per_staff: int = rule(10, 0, 1000, S, "Treasury each of a research effort's staff costs its organisation in an epoch")
    research_first_staff: int = rule(5, 1, 100, S, "Staff a new research effort starts with")
    research_secrecy: int = rule(60, 0, 100, S, "Secrecy a new research effort starts with")
    research_budget: int = rule(300, 0, 100000, S, "Treasury an organisation sets aside when its strategy starts a research effort")
    secret_spread_per_epoch_pct: int = rule(10, 0, 100, S, "Chance in an epoch that a technique an organisation found leaks out, at no secrecy (%)")
    creditor_recovery_floor_pct: int = rule(20, 0, 100, S, "Least share of their claims creditors recover in an insolvency (%)")
    lobby_influence: int = rule(5, 0, 100, S, "Influence over its realm an organisation that lobbies gains in an epoch")
    strategy_bid_chance_pct: int = rule(20, 0, 100, S, "Chance in an epoch that an organisation set to expand or integrate bids for another (%)")
    strategy_treasury_pct: int = rule(100, 0, 300, S, "How strongly an organisation's strategy grows or spends its treasury in an epoch (%)")

    @property
    def term_epochs(self) -> int:
        return self.epochs(self.term_years)
