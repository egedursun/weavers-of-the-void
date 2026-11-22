from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule, span

S = RuleGroup.MARKETS_AND_MONEY


@dataclass(frozen=True)
class CompetitionRules(Spanned):
    price_per_concentration_pct: int = rule(30, 0, 300, S, "How far prices rise at full concentration of sellers (%)")
    barrier_price_pct: int = rule(20, 0, 300, S, "How far prices rise when every barrier to entry stands at full strength (%)")
    buyer_power_pct: int = rule(20, 0, 100, S, "How far a single buyer lowers the prices it pays (%)")
    cartel_price_pct: int = rule(30, 0, 300, S, "How far a fully disciplined cartel fixing prices raises them (%)")
    cartel_discipline_decay: int = rule(5, 0, 50, S, "Discipline a cartel loses in an epoch")
    cheat_gain_threshold: int = rule(20, 0, 100, S, "Discipline under which a member's gain from cheating breaks its cartel")
    cartel_fine_pct: int = rule(20, 0, 100, S, "Share of its worth each member of an exposed cartel is fined (%)")
    cartel_trust_loss: int = rule(15, 0, 100, S, "Reputation each member of an exposed cartel loses")
    cartel_form_chance_pct: int = rule(10, 0, 100, S, "Chance in an epoch that the largest sellers of a market with few sellers form a cartel (%)")
    price_war_floor_pct: int = rule(50, 0, 100, S, "Lowest share of its price a price war drives a market to (%)")
    price_war_chance_pct: int = rule(
        5, 0, 100, S, "Chance in an epoch that the largest seller of a market with few sellers, set on growth, starts a price war (%)"
    )
    default_cut_pct: int = rule(20, 0, 100, S, "Cut below the usual price a price war started by an organisation's course makes (%)")
    war_cost_per_cut: int = rule(5, 0, 1000, S, "Treasury the aggressor of a price war spends in an epoch for each point of its cut")
    war_target_cost_pct: int = rule(60, 0, 300, S, "Share of the aggressor's spending each target of a price war loses in an epoch (%)")
    war_max_years: int = span(10, 1, 500, S, "Years after which a price war that has no winner is called off")
    barrier_decay_per_epoch: int = rule(3, 0, 50, S, "Strength a barrier to entry loses in an epoch once what raised it is gone")
    shop_weight: int = rule(10, 1, 100, S, "Weight of each shop that sells a good when the sellers of its market are counted")
    workshop_weight: int = rule(10, 1, 100, S, "Weight of each level of a workshop owned by a seller when the sellers of its market are counted")
    small_sellers_pct: int = rule(40, 0, 100, S, "Share of a market held by small sellers too many to name where common supply runs (%)")
    one_seller_share: int = rule(90, 50, 100, S, "Share at which one seller holds a market alone (%)")
    few_sellers_concentration: int = rule(25, 0, 100, S, "Concentration at which a market has few sellers")
    few_buyers_population: int = rule(500, 0, 100000, S, "Population under which a market has few buyers")
    licence_barrier_pct: int = rule(100, 0, 300, S, "How strongly a licence limit of the law becomes a barrier to entry (%)")
    guild_right_barrier: int = rule(80, 0, 100, S, "Barrier a guild's right to its market raises")
    secret_barrier: int = rule(50, 0, 100, S, "Barrier a secret technique of the leading seller raises")
    route_barrier: int = rule(40, 0, 100, S, "Barrier the leading seller's control of a trade route raises")
    network_barrier: int = rule(40, 0, 100, S, "Barrier the leading seller's control of a network reaching the market raises")
    favour_barrier: int = rule(30, 0, 100, S, "Barrier a god's blessing on the leading seller raises")

    @property
    def war_max_epochs(self) -> int:
        return self.epochs(self.war_max_years)
