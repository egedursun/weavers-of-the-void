from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule, span

G = RuleGroup.MARKETS_AND_MONEY


@dataclass(frozen=True)
class AccessRules:
    base_pct: int = rule(35, 0, 100, G, "Share of its output a place with no roads or routes still brings to market (%)")
    per_road: int = rule(8, 0, 100, G, "Market access each level of roads adds (%)")
    per_route: int = rule(10, 0, 100, G, "Market access each open trade route adds (%)")
    per_10_capacity: int = rule(2, 0, 100, G, "Market access each ten loads of route capacity add (%)")
    danger_pct: int = rule(60, 0, 100, G, "How much the danger of its routes takes from a place's market access (%)")
    unsold_pct: int = rule(40, 0, 100, G, "Value output that never reaches a market still fetches, eaten or bartered at home (%)")


@dataclass(frozen=True)
class TradePolicyRules:
    tariff_rate: int = rule(20, 0, 100, G, "Tariff a realm lays on a good its own works make when imports undercut them (%)")
    tariff_chance: int = rule(25, 0, 100, G, "Chance each epoch a realm whose owners press for it lays a tariff (%)")
    import_share_pct: int = rule(30, 0, 100, G, "Share of a good imported that makes its owners press for a tariff (%)")
    subsidy_rate: int = rule(15, 0, 100, G, "Subsidy a realm pays on food its members grow when they go hungry (%)")
    subsidy_hunger: int = rule(40, 0, 100, G, "Hunger at which a realm subsidises the food of its members")
    subsidy_treasury: int = rule(100, 0, 100000, G, "Treasury a realm needs before it pays subsidies")
    embargo_chance: int = rule(30, 0, 100, G, "Chance each epoch a realm at war embargoes its enemy (%)")
    treaty_embargo_chance: int = rule(40, 0, 100, G, "Chance each epoch a realm joins the embargo of an ally it is bound to by treaty (%)")
    lift_chance: int = rule(25, 0, 100, G, "Chance each epoch a realm lifts a tariff, subsidy or embargo whose cause has passed (%)")
    smuggle_gap_pct: int = rule(150, 100, 1000, G, "Price gap between two markets that tempts smugglers past a ban or embargo (%)")
    smuggle_share_pct: int = rule(30, 0, 100, G, "Share of a blocked trade smugglers carry (%)")
    smuggle_premium_pct: int = rule(50, 0, 400, G, "Premium smuggled goods fetch over the lawful price (%)")
    crime_per_10_units: int = rule(1, 0, 50, G, "Crime ten smuggled units add to the market that buys them")


@dataclass(frozen=True)
class CreditRules(Spanned):
    base_interest: int = rule(6, 0, 100, G, "Interest a borrower of perfect credit pays (%)")
    spread_pct: int = rule(25, 0, 200, G, "Interest each point of credit below perfect adds, in hundredths (%)")
    supply_pct: int = rule(10, 0, 100, G, "Interest a scarce money supply adds at most (%)")
    supply_per_1000: int = rule(40, 1, 10000, G, "Coin a thousand people's money supply needs before it counts as plentiful")
    strained_debt_pct: int = rule(150, 0, 1000, G, "Debt against treasury past which a borrower is strained (%)")
    restructure_years: int = span(5, 1, 1250, G, "Years a borrower spends restructuring after a default")
    default_loss: int = rule(30, 0, 100, G, "Credit a default costs")
    repay_gain: int = rule(4, 0, 100, G, "Credit each repaid loan earns")
    treasury_per_point: int = rule(40, 1, 10000, G, "Treasury that earns one point of credit")
    war_chance: int = rule(20, 0, 100, G, "Chance a realm whose bank a realm defaulted on goes to war over the debt (%)")
    reserve_per_1000: int = rule(20, 1, 1000, G, "Gold and silver a thousand people's coin needs as full backing")
    reserve_trust: int = rule(4, 0, 50, G, "Trust a coin gains or loses each epoch by its backing in reserves")

    @property
    def restructure_epochs(self) -> int:
        return self.epochs(self.restructure_years)


@dataclass(frozen=True)
class SpeculationRules(Spanned):
    greed_at: int = rule(25, -50, 50, G, "Greed facet from which a merchant speculates")
    chance_pct: int = rule(20, 0, 100, G, "Chance each epoch a greedy merchant buys up a rising good (%)")
    rise_pct: int = rule(10, 0, 400, G, "Rise in price over an epoch that tempts speculators (%)")
    hoard_share_pct: int = rule(20, 0, 100, G, "Share of a market's stock of a good a speculator buys up (%)")
    sell_rise_pct: int = rule(25, 0, 400, G, "Rise over the buying price at which a speculator sells (%)")
    bust_fall_pct: int = rule(15, 0, 100, G, "Fall under the buying price at which a speculation busts (%)")
    hold_years: int = span(3, 1, 1250, G, "Years a speculator holds a hoard before selling at any price")
    famine_hunger: int = rule(40, 0, 100, G, "Hunger at which speculators hoard food")
    unrest_per_hoard: int = rule(5, 0, 50, G, "Unrest a hoard of food raises in a hungry market")
    spike_unrest_pct: int = rule(40, 0, 400, G, "How much of that unrest any other hoard raises as prices spike (%)")
    wealth_per_value: int = rule(60, 1, 1000, G, "Value that moves a speculator's wealth by one point")

    @property
    def hold_epochs(self) -> int:
        return self.epochs(self.hold_years)


@dataclass(frozen=True)
class ElasticityRules:
    staple_pct: int = rule(50, 0, 400, G, "How strongly the price of staple food answers supply and demand (%)")
    goods_pct: int = rule(100, 0, 400, G, "How strongly the price of everyday goods answers supply and demand (%)")
    luxury_pct: int = rule(160, 0, 400, G, "How strongly the price of luxuries answers supply and demand (%)")
    income_pct: int = rule(60, 0, 400, G, "How strongly a market's prosperity raises its demand for luxuries (%)")


@dataclass(frozen=True)
class ArbitrageRules:
    merchant_pct: int = rule(100, 0, 400, G, "How much a full share of merchants at either end raises what a route carries (%)")
    guild_pct: int = rule(25, 0, 400, G, "How much a merchant guild at either end raises what a route carries (%)")
    belief_pct: int = rule(50, 0, 400, G, "How much a community's confident knowledge of its neighbours raises what its routes carry, at full confidence (%)")
