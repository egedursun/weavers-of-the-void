from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule, span

P = RuleGroup.POLITY


@dataclass(frozen=True)
class AffairsRules(Spanned):
    task_skill_pct: int = rule(100, 0, 300, P, "How much an officer's skill scales the work of a council task (%)")
    relations_gain: int = rule(4, 0, 100, P, "Relation a chancellor wins with a neighbour each epoch at full skill and diligence")
    drill_gain: int = rule(4, 0, 100, P, "Cohesion a marshal drills into the realm's armies each epoch at full skill and diligence")
    collect_gain: int = rule(6, 0, 1000, P, "Treasury a treasurer gathers per land each epoch at full skill and diligence")
    disrupt_gain: int = rule(15, 0, 100, P, "Progress a spymaster strips from schemes against the realm each epoch at full skill and diligence")
    convert_gain: int = rule(6, 0, 100, P, "Piety a chaplain kindles in a land of another faith each epoch at full skill and diligence")
    purge_gain: int = rule(8, 0, 100, P, "Corruption a judge purges each epoch at full skill and diligence")
    leak_below: int = rule(25, 0, 100, P, "Diligence below which a spymaster leaks the ruler's secrets")
    election_years: int = span(5, 1, 1250, P, "Years between elections in a realm with an assembly")
    seats: int = rule(9, 1, 1000, P, "Fewest seats in a realm's elected council; a larger realm seats as many as the cube root of its people")
    estate_appeal_pct: int = rule(100, 0, 300, P, "How strongly an estate draws the votes of its own class (%)")
    party_appeal_pct: int = rule(100, 0, 300, P, "How strongly a party draws the votes of those who back its cause (%)")
    purse_appeal_pct: int = rule(20, 0, 300, P, "How much a faction's spending at the polls buys votes (%)")
    hook_votes_pct: int = rule(30, 0, 300, P, "Share of a land's votes a candidate wins by a hook over its lord (%)")
    opinion_votes_pct: int = rule(50, 0, 300, P, "How much a land's approval of a candidate sways its votes (%)")
    seat_weight_pct: int = rule(60, 0, 300, P, "How much a council seat weighs on the laws before the realm (%)")
    corruption_drift_pct: int = rule(25, 0, 100, P, "How fast corruption moves toward what the realm breeds (%)")
    overreach_pct: int = rule(30, 0, 200, P, "How much administrative overreach breeds corruption (%)")
    greed_corruption: int = rule(10, 0, 100, P, "Corruption each greedy officer breeds")
    honest_corruption: int = rule(6, 0, 100, P, "Corruption each honest officer holds back")
    farm_corruption: int = rule(12, 0, 100, P, "Corruption each farmed-out tax breeds")
    creed_corruption: int = rule(10, 0, 100, P, "Corruption a creed of law or restraint holds back")
    skim_pct: int = rule(40, 0, 100, P, "Share of the taxes corruption skims at full corruption (%)")
    enforcement_loss_pct: int = rule(30, 0, 100, P, "Share of the laws' enforcement corruption erodes at full corruption (%)")
    disapproval_pct: int = rule(20, 0, 100, P, "How much corruption sours the people's approval of their ruler (%)")
    farm_take_pct: int = rule(40, 0, 200, P, "Extra take a farmed-out tax brings (%)")
    farm_unrest: int = rule(3, 0, 100, P, "Unrest each farmed-out tax stirs in every land each epoch")
    tax_burden: int = rule(1, 0, 100, P, "Satisfaction a class loses per five points of a tax that falls on it")
    land_take: int = rule(3, 0, 1000, P, "Treasury a land tax of ten draws per ten points of prosperity held by farmers and nobles")
    poll_take: int = rule(2, 0, 1000, P, "Treasury a poll tax of ten draws per thousand people")
    trade_take: int = rule(30, 0, 1000, P, "Treasury a trade tax of ten draws per trade route or market")
    consumption_take: int = rule(3, 0, 1000, P, "Treasury a tax on luxuries of ten draws per ten points of prosperity held by nobles and merchants")
    mandate_years: int = span(5, 1, 500, P, "Years a mandate gives before it is judged met or failed")
    famine_hunger: int = rule(60, 0, 100, P, "Hunger at which a ruler orders relief from the state granaries")
    relief_food: int = rule(40, 0, 10000, P, "Food a famine relief mandate moves from the capital's granaries for every thousand people of the town in famine")
    curfew_unrest: int = rule(60, 0, 100, P, "Unrest at which a ruler orders a curfew")
    curfew_calm: int = rule(6, 0, 100, P, "Unrest a curfew stills each epoch")
    curfew_mood: int = rule(3, 0, 100, P, "Satisfaction a curfew costs every class each epoch")
    ban_below: int = rule(30, 0, 10000, P, "Food in the capital's store, per thousand of its people, below which a ruler bans its export")
    produce_amount: int = rule(20, 0, 10000, P, "Weapons a production order asks of a land at war for every thousand of its people")
    mandate_legitimacy: int = rule(4, 0, 100, P, "Legitimacy a ruler loses when a mandate fails")
    demand_years: int = span(2, 1, 500, P, "Years a noble waits on a demand before souring")
    demand_grudge: int = rule(6, 0, 100, P, "Regard for the ruler a noble loses each epoch a demand goes unmet")
    honour_wanted: int = rule(40, 0, 100, P, "Honour a noble expects")
    policy_drift_pct: int = rule(20, 0, 100, P, "How far a class's satisfaction moves toward its approval of the realm's policies (%)")
    constitution_pct: int = rule(40, 0, 100, P, "How fast a change to the fundamental law moves compared with other laws (%)")
    revolution_at: int = rule(80, 0, 100, P, "Support at which a movement for the franchise overturns the fundamental law where stability fails")
    revolution_stability: int = rule(30, 0, 100, P, "Stability below which a franchise movement can overturn the fundamental law")
    resolution_pct: int = rule(25, 0, 100, P, "Chance each epoch an interworld assembly brings a resolution to the vote (%)")
    resolution_years: int = span(10, 1, 1250, P, "Years a passed resolution binds its members")
    resolution_breach_trust: int = rule(10, 0, 100, P, "Trust the other members lose in one that breaks a resolution")
    route_safety: int = rule(5, 0, 100, P, "Danger a route-security resolution strips from routes between members each epoch")
    void_ban_level: int = rule(80, 0, 100, P, "Restriction on rites a ban on void rites lays in every member's realm")
    court_dwelling_pct: int = rule(40, 0, 100, P, "Weight of the ruler's dwelling in a court's grandeur (%)")
    court_artwork: int = rule(5, 0, 100, P, "Grandeur each artwork at the capital lends the court")
    court_goods: int = rule(2, 0, 100, P, "Grandeur each ten fine goods at the capital lend the court")
    court_courtier: int = rule(3, 0, 100, P, "Grandeur each courtier lends the court")
    revels_grandeur: int = rule(10, 0, 100, P, "Grandeur a master of revels lends the court")
    court_renown_pct: int = rule(5, 0, 100, P, "Renown a ruler wins each epoch per point of grandeur (%)")
    court_trust_pct: int = rule(3, 0, 100, P, "Trust other realms gain each epoch per point of grandeur (%)")
    talent_pct: int = rule(20, 0, 100, P, "Chance each epoch a grand court draws a skilled mortal to the capital at full grandeur (%)")
    steward_gain: int = rule(5, 0, 1000, P, "Treasury a court steward saves each epoch")
    champion_honour: int = rule(2, 0, 100, P, "Honour a court champion wins the ruler each epoch")
    physician_heal: int = rule(5, 0, 100, P, "Health a court physician restores to the ruler each epoch")
    tutor_gain: int = rule(1, 0, 100, P, "Intellect a court tutor adds to the heir each epoch")
    chronicler_renown: int = rule(2, 0, 100, P, "Renown a court chronicler wins the ruler each epoch")
    separatism_cohesion_pct: int = rule(50, 0, 200, P, "How much a distinct people's cohesion feeds its wish to break away (%)")
    separatism_grievance_pct: int = rule(50, 0, 200, P, "How much grievance toward the realm feeds separatism (%)")
    separatism_autonomy_pct: int = rule(50, 0, 200, P, "How much autonomy soothes separatism (%)")
    separatism_privilege: int = rule(10, 0, 100, P, "Separatism each privilege of a people's estate soothes")

    @property
    def mandate_epochs(self) -> int:
        return self.epochs(self.mandate_years)

    @property
    def demand_epochs(self) -> int:
        return self.epochs(self.demand_years)

    @property
    def resolution_epochs(self) -> int:
        return self.epochs(self.resolution_years)

    @property
    def election_epochs(self) -> int:
        return self.epochs(self.election_years)
