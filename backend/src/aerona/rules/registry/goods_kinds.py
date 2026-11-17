from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

M = RuleGroup.MARKETS_AND_MONEY


@dataclass(frozen=True)
class GoodsRules:
    licensed_demand_pct: int = rule(85, 0, 100, M, "Demand left for a good that may be sold only under licence (%)")
    restricted_demand_pct: int = rule(50, 0, 100, M, "Demand left for a restricted good (%)")
    forbidden_demand_pct: int = rule(15, 0, 100, M, "Demand left for a forbidden good, bought only in secret (%)")
    taboo_pct: int = rule(60, 0, 100, M, "Share of a good's taboo that removes demand for it (%)")
    prestige_demand_pct: int = rule(80, 0, 300, M, "How far a good's prestige lifts demand in wealthy markets and lowers it in poor ones (%)")
    sacred_demand_pct: int = rule(60, 0, 300, M, "How far a good's sacredness lifts demand in pious markets (%)")
    exempt_tariff_pct: int = rule(0, 0, 300, M, "Share of a tariff that falls on untaxed goods (%)")
    staple_tariff_pct: int = rule(50, 0, 300, M, "Share of a tariff that falls on goods taxed at the staple rate (%)")
    ordinary_tariff_pct: int = rule(100, 0, 300, M, "Share of a tariff that falls on goods taxed at the ordinary rate (%)")
    luxury_tariff_pct: int = rule(150, 0, 300, M, "Share of a tariff that falls on goods taxed at the luxury rate (%)")
    strategic_tariff_pct: int = rule(125, 0, 300, M, "Share of a tariff that falls on goods taxed at the strategic rate (%)")
