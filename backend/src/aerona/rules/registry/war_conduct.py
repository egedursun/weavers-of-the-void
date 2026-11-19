from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule, span

W = RuleGroup.WAR_AND_DIPLOMACY


@dataclass(frozen=True)
class WarConductRules(Spanned):
    justify_gain: int = rule(15, 0, 100, W, "Justification a casus belli gains each epoch it is held")
    justified_at: int = rule(50, 0, 100, W, "Justification a casus belli needs before a war on it counts as justified")
    casus_belli_years: int = span(50, 1, 12500, W, "Years an unused casus belli lasts before it lapses")
    claim_strength: int = rule(30, 0, 100, W, "Strength a claim needs to give its backers a casus belli")
    vendetta_magnitude: int = rule(20, 0, 100, W, "Weight a memory of killed kin needs to give a casus belli")
    liberation_share: int = rule(1, 0, 100, W, "Communities of one's own people ruled by another realm that give a casus belli of liberation")
    toll_dispute_pct: int = rule(40, 0, 100, W, "Tariff on a partner's goods that gives the partner a casus belli of trade dispute (%)")
    hunger_food: int = rule(
        20, 0, 100000, W, "Food stock per thousand people below which a community may claim the land of a neighbour holding three times as much out of need"
    )
    unjustified_tyranny: int = rule(15, 0, 100, W, "Tyranny the ruler of an unjustified attacker gains")
    unjustified_threat: int = rule(15, 0, 100, W, "Threat every other realm sees in an unjustified attacker")
    unjustified_support: int = rule(20, 0, 100, W, "War support an unjustified attacker starts without")
    support_start: int = rule(60, 0, 100, W, "War support a side starts with")
    defence_support: int = rule(20, 0, 100, W, "War support a side defending its own lands gains")
    justification_support_pct: int = rule(30, 0, 100, W, "War support a fully justified casus belli adds (%)")
    opinion_support_pct: int = rule(30, 0, 100, W, "War support public opinion of the war adds or takes, at its extremes (%)")
    propaganda_support: int = rule(4, 0, 100, W, "War support each propaganda work and each herald of the side adds")
    propaganda_cap: int = rule(20, 0, 100, W, "Most war support propaganda can add")
    casualty_support_pct: int = rule(150, 0, 1000, W, "War support lost per share of the population killed, weighted by how much the side values kinship (%)")
    tax_support_pct: int = rule(50, 0, 300, W, "War support lost per point of war taxes (%)")
    maimed_support: int = rule(1, 0, 100, W, "War support lost per hundred maimed brought home")
    occupation_support: int = rule(8, 0, 100, W, "War support lost per home region under occupation")
    support_drift_pct: int = rule(35, 0, 100, W, "Share of the gap to its aim that war support closes each epoch (%)")
    support_neutral: int = rule(50, 0, 100, W, "War support below which a side leans toward peace")
    support_peace_pct: int = rule(60, 0, 300, W, "Peace pressure from each point of war support below neutral (%)")
    assembly_peace_pct: int = rule(150, 100, 400, W, "How much more peace pressure weighs in realms ruled by assembly or council (%)")
    low_support_desertion_pct: int = rule(50, 0, 300, W, "Extra desertion from a side with no war support at all (%)")
    low_support_levy_pct: int = rule(40, 0, 100, W, "Levies a side with no war support fails to raise (%)")
    peace_movement_weariness: int = rule(10, 0, 100, W, "Weariness a rising peace movement forces on its realm's wars")
    score_unit: int = rule(10, 1, 1000, W, "Demand cost one point of war score pays for")
    base_budget: int = rule(10, 0, 1000, W, "Demand cost a victor may claim even with no war score")
    cession_pop_per_cost: int = rule(500, 1, 100000, W, "People in a ceded land per point of its demand cost")
    tribute_amount_per_cost: int = rule(20, 1, 100000, W, "Tribute per epoch per point of its demand cost")
    tribute_cost_per_epoch: int = rule(2, 0, 100, W, "Demand cost of each epoch of tribute")
    fight_on_support: int = rule(55, 0, 100, W, "War support a beaten side needs to refuse the peace and fight on")
    fight_on_weariness: int = rule(50, 0, 100, W, "Weariness above which a beaten side can no longer refuse the peace")
    refusal_weariness: int = rule(15, 0, 100, W, "Weariness a side gains each time it refuses a peace")
    separate_peace_at: int = rule(70, 0, 100, W, "Weariness at which an ally makes a separate peace and leaves the war")
    dread_morale: int = rule(10, 0, 100, W, "Morale the armies of a fearful people lose to a sack or massacre")
    dread_support: int = rule(10, 0, 100, W, "War support a fearful people loses to a sack or massacre")
    harden_support: int = rule(10, 0, 100, W, "War support a hardened people gains from a sack or massacre")
    harden_resistance: int = rule(10, 0, 100, W, "Resistance a hardened people raises in its occupied lands after a sack or massacre")
    atrocity_cruelty: int = rule(8, 0, 100, W, "Cruelty renown a sack or massacre earns its perpetrator among onlookers")
    atrocity_dread: int = rule(10, 0, 100, W, "Dread the ruler behind a sack or massacre gains")
    atrocity_mercy_pct: int = rule(100, 0, 300, W, "How much more onlookers who value mercy hold a sack or massacre against its perpetrator (%)")
    atrocity_threat: int = rule(8, 0, 100, W, "Threat other realms see in the perpetrator of a sack or massacre")
    efficiency_gain: int = rule(10, 0, 100, W, "Efficiency a war production line gains each epoch it keeps making the same thing (%)")
    efficiency_cap: int = rule(50, 0, 300, W, "Highest efficiency a war production line reaches (%)")
    civilian_cut_pct: int = rule(25, 0, 100, W, "Civilian goods a community at war production fails to make (%)")

    @property
    def casus_belli_epochs(self) -> int:
        return self.epochs(self.casus_belli_years)
