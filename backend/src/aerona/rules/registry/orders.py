from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule, span

E = RuleGroup.ECONOMY
P = RuleGroup.POLITY


@dataclass(frozen=True)
class SavingRules:
    base_share: int = rule(10, 0, 100, E, "Share of what a household earns beyond its costs that it saves before patience moves it (%)")
    patience_pct: int = rule(20, 0, 100, E, "Share of saving a head of the greatest patience adds, or the least takes away (%)")
    insecure_from: int = rule(50, 0, 100, E, "Insecurity of a town from which its households bury what they save")
    war_insecurity: int = rule(40, 0, 100, E, "Insecurity a war adds to a town")
    find_chance: int = rule(5, 0, 100, E, "Chance each epoch that the lost hoards of a town are found by those who dig there (%)")
    goods_spoil_pct: int = rule(5, 0, 100, E, "Share of goods kept as savings that spoil or die each epoch (%)")
    land_rent_pct: int = rule(5, 0, 100, E, "Rent land kept as savings earns each epoch (%)")
    land_war_loss_pct: int = rule(20, 0, 100, E, "Share of land savings lost each epoch its town is at war (%)")
    dearth_gain_pct: int = rule(50, 0, 400, E, "Extra worth stored goods fetch when they are sold in a hungry town (%)")
    rural_from: int = rule(40, 0, 100, E, "Share of farmers from which a town's households save in land (%)")


@dataclass(frozen=True)
class ExchangeRules:
    base_spread: int = rule(4, 0, 100, E, "Spread a money changer asks on an exchange between two coins of full trust (%)")
    trust_spread: int = rule(10, 0, 100, E, "Spread added for each half the trust of the weaker coin falls below full (%)")
    balance_pct: int = rule(20, 0, 100, E, "Share of the goods its users sell beyond what they buy that lifts the worth of a coin (%)")
    supply_pct: int = rule(1, 0, 100, E, "Share by which each coin issued lowers a coin's worth, in hundredths (%)")
    shock_pct: int = rule(20, 0, 100, E, "Rise of a rate in one epoch from which it is a shock to debtors in that coin (%)")
    shock_cap: int = rule(500, 0, 10000, E, "Most a debt in foreign coin grows in one shock (%)")
    unconvertible_pct: int = rule(25, 0, 100, E, "Cost of trading across a coin that cannot be changed (%)")
    changer_skill: int = rule(3, 0, 10, E, "Accounting a merchant needs to change money at a market")
    changer_share: int = rule(50, 0, 100, E, "Share of the spread on a market's exchanges the changer keeps as coin (%)")
    bill_amount: int = rule(
        20, 0, 100000, E, "Coin a bill of exchange between two markets that know banking is drawn for, for each thousand people of the smaller market"
    )
    bill_loss_pct: int = rule(30, 0, 100, E, "Share of a road's losses a bill of exchange between its markets spares, since no coin travels (%)")
    bills_per_route: int = rule(1, 0, 20, E, "Unsettled bills of exchange a road between markets that know banking holds at once")


@dataclass(frozen=True)
class EconomicOrderRules(Spanned):
    redistribution_upkeep: int = rule(2, 0, 1000, E, "Treasury the clerks and stores of a redistributing centre cost each epoch for every town it serves")
    redistribution_storage_loss_pct: int = rule(10, 0, 100, E, "Share of the goods sent to a centre that its storage loses before they are given out (%)")
    command_efficiency_floor: int = rule(30, 0, 100, E, "Output a commanded economy keeps at no planning capacity (%)")
    planning_per_official: int = rule(2, 0, 20, E, "Planning capacity each official of a realm adds")
    transition_stage_years: int = span(10, 1, 500, P, "Years each stage of a change of economic order takes")
    uncompensated_grievance: int = rule(40, 0, 100, P, "Grievance the losers of an uncompensated change of order gather")
    flight_per_grievance_pct: int = rule(10, 0, 100, P, "Chance a loser flees a change of order for each tenth of grievance (%)")
    centre_collapse_spread_pct: int = rule(60, 0, 100, E, "Share of a redistributing realm's prosperity its towns lose when the centre falls (%)")
    planning_per_record: int = rule(5, 0, 20, E, "Planning capacity each level of writing at a realm's capital adds")
    holding_price: int = rule(20, 0, 100000, P, "Coin a realm pays the loser of a holding under full compensation")
    transfers_per_stage: int = rule(50, 0, 100, P, "Share of the realm's holdings a change of economic order moves at each stage (%)")
    transfers_to_finish: int = rule(90, 1, 100, P, "Share of the realm's holdings a change of economic order moves before it is done (%)")
    resistance_pct: int = rule(25, 0, 100, P, "Share of each loser's grievance that adds to the resistance to a change of order (%)")
    fail_from: int = rule(80, 0, 100, P, "Resistance from which a change of economic order breaks")
    demand_support: int = rule(40, 0, 100, P, "Support a movement for abolition or land reform needs before its realm feels its demand")
    demand_chance_pct: int = rule(10, 0, 100, P, "Chance in an epoch that a realm pressed toward a new economic order begins the change (%)")
    creed_hold_pct: int = rule(50, 0, 100, P, "Share of a realm's towns a creed must hold before its teaching presses the realm's economic order (%)")
    failure_stability: int = rule(15, 0, 100, P, "Stability a realm loses when its change of economic order breaks")
    redistribution_share: int = rule(20, 0, 100, E, "Share of its goods a town sends to its centre each epoch under redistribution (%)")
    dues_share: int = rule(10, 0, 100, E, "Share of its goods a town owes in dues each epoch under obligation (%)")
    class_shift: int = rule(5, 0, 100, E, "Satisfaction a class gains or loses each epoch as the order's distribution favours or spares it")

    @property
    def transition_stage_epochs(self) -> int:
        return self.epochs(self.transition_stage_years)

    lottery_calm: int = rule(3, 0, 100, E, "Unrest each town of a realm that shares out its stores by lot loses each epoch, as quarrels over rank fade")


@dataclass(frozen=True)
class PuttingOutRules:
    found_chance: int = rule(10, 0, 100, E, "Chance each epoch that a merchant body puts work out to a village near its town (%)")
    volume: int = rule(100, 0, 100000, E, "Raw goods a putting-out arrangement hands to its village each epoch for every thousand villagers")
    merchant_margin: int = rule(20, 0, 100, E, "Share of the worth of the work put out the merchant keeps as coin (%)")
    village_pay: int = rule(2, 0, 100, E, "Prosperity a village gains each epoch from the work put out to it, in tenths")
    chain_chance: int = rule(5, 0, 100, E, "Chance each epoch that a merchant body buys into a step of a chain in a town it trades with (%)")
    chain_share: int = rule(20, 0, 100, E, "Share of a step's output its holder draws home (%)")
    proto_progress: int = rule(2, 0, 100, E, "Progress toward making in factories each epoch of work put out gives the merchant's town")


@dataclass(frozen=True)
class TourismRules:
    wealthy_from: int = rule(70, 0, 100, E, "Prosperity of a town from which its wealthy travel for pleasure")
    visitors: int = rule(50, 0, 100000, E, "Visitors a wealthy town sends to a sight each epoch for every thousand of its people")
    spend: int = rule(2, 0, 1000, E, "Coin each visitor spends at the town of a sight")
    renown: int = rule(1, 0, 100, E, "Renown a sight's keeper gains for each hundred visitors")
    word_chance: int = rule(20, 0, 100, E, "Chance the travellers of a flow carry the ways of the land they saw home (%)")
    sickness_chance: int = rule(5, 0, 100, E, "Chance the travellers of a flow carry an outbreak of the sight's land home (%)")
