from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule, span

C = RuleGroup.RELIGION_AND_LANGUAGE
S = RuleGroup.POPULATION_AND_GROWTH
J = RuleGroup.POLITY


@dataclass(frozen=True)
class RevivalRules(Spanned):
    pressure_from: int = rule(
        30, 0, 1000, C, "Culture drift a people suffers from rulers, conquerors and neighbours within the memory of a movement before it answers with one"
    )
    memory_years: int = span(30, 1, 1250, C, "Years back a people counts the drift pressed on it")
    restore_from: int = rule(20, -100, 100, C, "Tradition from which a people answers pressure by restoring its old ways")
    adopt_from: int = rule(20, -100, 100, C, "Love of the foreign from which a people answers pressure by adopting the ways pressed on it")
    stage_gain: int = rule(15, 0, 100, C, "Strength a movement gains each epoch; a stage passes each time it fills")
    language_gain: int = rule(5, 0, 100, C, "Standing a movement to revive its language gives the language each epoch")
    value_pull_pct: int = rule(10, 0, 100, C, "Share of the gap to the old or the pressed values that a movement closes each epoch (%)")
    expel_opinion: int = rule(5, 0, 100, C, "Opinion a movement to expel foreigners takes from its people of those who press on it")
    restore_chance: int = rule(20, 0, 100, C, "Chance each epoch that a movement to restore its old god brings its people back to that god (%)")
    suppress_chance: int = rule(10, 0, 100, C, "Chance each epoch that the realm pressing on a people puts down its movement before it settles (%)")

    @property
    def memory_epochs(self) -> int:
        return self.epochs(self.memory_years)


@dataclass(frozen=True)
class IntoxicationRules:
    customs_per_people: int = rule(2, 0, 7, C, "Intoxicant customs a people holds when first read")
    habit_chance: int = rule(3, 0, 100, C, "Chance each epoch a mortal of a people that takes an intoxicant daily forms a habit (%)")
    brawl_chance: int = rule(10, 0, 100, C, "Chance a gathering of a people that drinks at feasts ends in a brawl (%)")
    brawl_damage: int = rule(8, 0, 100, C, "Harm a brawl at a gathering deals the one hurt")
    vision_chance: int = rule(10, 0, 100, C, "Chance a mystic of a people that takes an intoxicant in rites has a vision (%)")
    brew_per_100: int = rule(2, 0, 100, C, "Brew base a town of a people that drinks daily or at feasts consumes for each hundred folk")
    brew_cheer: int = rule(3, 0, 100, C, "Satisfaction every class of a town gains each epoch when it has all the brew it drinks")
    mourning_calm: int = rule(6, 0, 100, C, "Stress a mourner of a people that drinks in mourning loses each epoch")
    forbidden_pct: int = rule(30, 0, 100, C, "Share of the usual chance of a habit that a forbidden intoxicant still breeds in secret (%)")
    forbidden_infamy: int = rule(5, 0, 100, C, "Infamy one who forms a habit of a forbidden intoxicant gains")


@dataclass(frozen=True)
class MarkRules:
    customs_per_people: int = rule(3, 0, 8, C, "Kinds of body mark a people gives meaning to when first read")
    renown_per_deed: int = rule(2, 0, 100, C, "Renown a mark of deeds adds where it is read")
    calm_per_charm: int = rule(3, 0, 100, C, "Stress a protective mark takes off its bearer each epoch")
    belonging_per_mark: int = rule(3, 0, 100, C, "Loyalty to their community a mark of clan, marriage or age-set gives its bearer")
    shame_per_brand: int = rule(5, 0, 100, C, "Honour a brand of crime takes from its bearer where it is read")


@dataclass(frozen=True)
class TimeBudgetRules:
    output_pct: int = rule(100, 0, 400, S, "Scale of output a class's share of work sets against the usual share (%)")
    usual_work: int = rule(55, 1, 100, S, "Share of a year that is the usual share of work")
    leisure_satisfaction: int = rule(20, 0, 100, S, "Satisfaction a class gains for each ten points of leisure above the usual")
    usual_leisure: int = rule(10, 0, 100, S, "Share of a year that is the usual share of leisure")
    usual_rest: int = rule(20, 0, 100, S, "Share of a year that is the usual share of rest")
    rest_calm: int = rule(1, 0, 100, S, "Unrest a town loses each epoch for each ten points of rest above the usual")
    travel_trade: int = rule(
        1, 0, 100, S, "Prosperity a town gains or loses each epoch for each ten points of travel its folk make above or below the usual, in tenths"
    )
    service_defense: int = rule(
        1, 0, 100, S, "Defence a town gains or loses each epoch for each ten points of service its folk give above or below the usual, in tenths"
    )
    worship_piety: int = rule(2, 0, 100, S, "Piety a town gains or loses each epoch for each ten points of worship its folk give above or below the usual")
    usual_worship: int = rule(10, 0, 100, S, "Share of a year that is the usual share of worship")
    usual_travel: int = rule(3, 0, 100, S, "Share of a year that is the usual share of travel")
    usual_service: int = rule(2, 0, 100, S, "Share of a year that is the usual share of service")
    rest_fertility_pct: int = rule(20, 0, 100, S, "Share by which each ten points of rest above or below the usual raise or lower the chance of children (%)")
    leisure_attendance: int = rule(2, 0, 100, S, "Chance of joining a gathering gained or lost for each ten points of leisure above or below the usual")


@dataclass(frozen=True)
class NamingCustomRules(Spanned):
    secret_chance: int = rule(40, 0, 100, C, "Chance a people that names is one that also gives a secret name (%)")
    taboo_years: int = span(20, 0, 1250, C, "Years the names of the dead go unspoken where a people keeps such a taboo")
    rename_chance: int = rule(30, 0, 100, C, "Chance a people renames its folk at each turn of life it marks (%)")

    @property
    def taboo_epochs(self) -> int:
        return self.epochs(self.taboo_years)


@dataclass(frozen=True)
class AgeSetRules(Spanned):
    from_tradition: int = rule(30, -100, 100, S, "Tradition from which a people binds its folk in age-sets")
    span_years: int = span(7, 1, 1250, S, "Years of initiation one age-set gathers before the next opens")
    grade_years: int = span(15, 1, 1250, S, "Years an age-set spends in a grade before it is promoted")
    warrior_levy_pct: int = rule(20, 0, 100, S, "Share added to a town's mobilisation by an age-set in the warrior grade (%)")
    mates_bond: int = rule(5, 0, 100, S, "Friendship age-mates gain with one another when their set is promoted")

    @property
    def span_epochs(self) -> int:
        return self.epochs(self.span_years)

    @property
    def grade_epochs(self) -> int:
        return self.epochs(self.grade_years)


@dataclass(frozen=True)
class TavernRules(Spanned):
    patrons_pct: int = rule(10, 0, 100, S, "Share of a town's folk who keep a tavern each epoch (%)")
    rumour_pct: int = rule(20, 0, 100, S, "Chance added to a rumour reaching a town that keeps a tavern (%)")
    brawl_chance: int = rule(5, 0, 100, S, "Chance each epoch a busy tavern sees a brawl (%)")
    keeper_renown: int = rule(2, 0, 100, S, "Most renown the keeper of a tavern gains each epoch from the rumours that pass through it")
    lodging_per_inn: int = rule(20, 0, 100000, S, "Travellers an inn lodges each year")


@dataclass(frozen=True)
class WelfareRules:
    inmates_per_house: int = rule(10, 0, 1000, S, "Poor, orphans and maimed a house of welfare takes in for each thousand townsfolk at full poverty")
    poverty_relief: int = rule(5, 0, 100, S, "Poverty pressure each house of welfare takes off its town each epoch")
    upkeep_per_inmate: int = rule(
        50,
        0,
        1000,
        S,
        "Upkeep in coin a house of welfare needs for each hundred it takes in, paid by its patron or else its town; unpaid, it turns its poor away",
    )
    patron_renown: int = rule(1, 0, 100, S, "Renown the patron of a house of welfare gains each epoch")
    beggars_insecurity: int = rule(10, 0, 100, S, "Insecurity beggars in the streets add to a poor town with no house of welfare")
    beggars_from: int = rule(50, 0, 100, S, "Poverty in a town with no house of welfare from which beggars fill its streets and its insecurity rises")


@dataclass(frozen=True)
class CommuteRules:
    district_distance: int = rule(8, 0, 100, S, "Distance each district beyond the first adds to the way to work")
    road_relief: int = rule(10, 0, 100, S, "Distance a town's roads and bridges take off the way to work")
    lost_per_distance_pct: int = rule(40, 0, 100, S, "Share of labour lost for each point of distance, in hundredths (%)")
    camp_from: int = rule(50, 0, 100, S, "Distance from which a town keeps a worker camp that wins back half the labour lost")


@dataclass(frozen=True)
class CooperativeRules:
    found_from: int = rule(40, 0, 100, S, "Poverty in a town from which its folk pool their means in a cooperative")
    dues: int = rule(1, 0, 100, S, "Coin each member pays into the pool each epoch")
    relief: int = rule(3, 0, 100, S, "Poverty pressure a cooperative takes off its town each epoch while its pool holds")
    payout: int = rule(1, 0, 100, S, "Coin a cooperative that relieves its members pays each member out of its pool each epoch while the pool lasts")


@dataclass(frozen=True)
class EvidenceRules:
    decay: int = rule(5, 0, 100, J, "Reliability evidence loses each epoch before its case is tried")
    trace_reliability: int = rule(60, 0, 100, J, "Reliability of a trace found where a crime was done")
    witness_weight_pct: int = rule(100, 0, 400, J, "Scale of the weight evidence adds to a case (%)")
    forged_reliability: int = rule(50, 0, 100, J, "Reliability a forged document claims")
    confession_chance: int = rule(15, 0, 100, J, "Chance the true culprit of a case confesses when it is opened (%)")
    confession_reliability: int = rule(85, 0, 100, J, "Reliability of a confession")
    divination_reliability: int = rule(40, 0, 100, J, "Reliability of a seer's reading of who did a crime")


@dataclass(frozen=True)
class CitizenshipRules(Spanned):
    residence_years: int = span(10, 1, 2500, J, "Years a foreigner lives in a realm before they may be naturalised")
    naturalise_chance: int = rule(20, 0, 100, J, "Chance each epoch a foreigner who has lived long enough is naturalised (%)")
    purchase_cost: int = rule(20, 0, 100000, J, "Coin a foreigner pays to buy citizenship")
    rightless_court_bias: int = rule(15, 0, 100, J, "Weight a judge's verdict leans against one without the right to the courts")
    rightless_office: int = rule(1, 0, 1, J, "Whether a realm keeps those without the right of office out of office")

    @property
    def residence_epochs(self) -> int:
        return self.epochs(self.residence_years)


@dataclass(frozen=True)
class BorderRules(Spanned):
    delay_pct: int = rule(10, 0, 100, J, "Trade a route into a realm loses for each epoch of delay at its border at full enforcement (%)")
    fee_per_100: int = rule(5, 0, 1000, J, "Coin a realm takes at its border for each hundred goods carried in at full fee, in hundredths of the fee")
    forged_pass_pct: int = rule(50, 0, 100, J, "Share of corruption at a border by which forged passes slip past its fees (%)")
    war_enforcement: int = rule(60, 0, 100, J, "Enforcement a realm at war sets at its border when it first closes it")
    war_delay_years: int = span(1, 0, 500, J, "Years of delay a realm at war sets at its border when it first closes it")

    @property
    def war_delay(self) -> int:
        return self.epochs(self.war_delay_years)


@dataclass(frozen=True)
class PoorReliefRules:
    relief_per_coin: int = rule(
        1, 0, 100, J, "Poverty pressure each ten coin of relief for every thousand people of the realm takes off the towns it reaches each epoch"
    )
    adopt_from: int = rule(50, 0, 100, J, "Mean poverty of its towns from which a realm takes up poor relief")
    adopt_budget: int = rule(50, 0, 100000, J, "Coin for every thousand of its people a realm sets aside for poor relief each epoch when it takes it up")
    adopt_reach: int = rule(40, 0, 100, J, "Share of its poor that a realm's relief reaches when it takes it up (%)")
    theft_pct: int = rule(30, 0, 100, J, "Share by which full relief lowers theft among the poor (%)")


@dataclass(frozen=True)
class MeasureRules:
    trade_pct: int = rule(10, 0, 100, J, "Trade a realm with standard measures gains (%)")
    tax_pct: int = rule(5, 0, 100, J, "Taxes a realm with standard measures collects more (%)")
    adopt_members: int = rule(3, 1, 100, J, "Towns a realm holds before it sets standard weights and measures, unless its people already reach the count below")
    adopt_population: int = rule(
        10000, 0, 1000000000, J, "People of its towns at which a realm sets standard weights and measures whatever the number of its towns"
    )
    adopt_fraud: int = rule(10, 0, 100, J, "Fraud with false measures in a realm when it first sets its standard")
    fraud_chance: int = rule(20, 0, 100, J, "Chance at full fraud that a merchant of the realm is tried for false measures each epoch (%)")
