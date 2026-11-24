from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule, span

C = RuleGroup.CIVILIZATION


@dataclass(frozen=True)
class RumoursRules(Spanned):
    min_magnitude: int = rule(30, 0, 100, C, "Weight a happening needs before word of it travels")
    hop_loss: int = rule(8, 0, 100, C, "Fidelity a rumour loses at each telling")
    distance_loss: int = rule(3, 0, 100, C, "Fidelity a rumour loses for each region it crosses")
    barrier_loss: int = rule(30, 0, 100, C, "Fidelity lost crossing a tongue nobody shares, scaled by how little is understood")
    written_pct: int = rule(50, 0, 100, C, "Share of the garbling spared where the hearers read and write a settled tongue (%)")
    floor: int = rule(10, 0, 100, C, "Fidelity below which nobody bothers to pass a rumour on")
    inflate_pct: int = rule(20, 0, 100, C, "How much a count of the dead, an army or riches grows at each telling that inflates it (%)")
    motive_opinion: int = rule(3, 0, 50, C, "Regard a community loses for the doer when a telling it hears gives a reason the facts do not hold")
    max_hops: int = rule(20, 1, 1000, C, "Most tellings a rumour survives")
    route_chance: int = rule(60, 0, 100, C, "Word passes along a trade road in an epoch (%)")
    pilgrimage_chance: int = rule(30, 0, 100, C, "Word passes between pilgrims of one faith in an epoch (%)")
    journey_chance: int = rule(50, 0, 100, C, "Travellers carry word to where they arrive (%)")
    spy_chance: int = rule(80, 0, 100, C, "Spies report what is said in the land they watch (%)")
    current_chance: int = rule(15, 0, 100, C, "Wrecks and castaways an ocean current carries bring word to the next coast it reaches (%)")
    spy_bonus: int = rule(15, 0, 100, C, "Fidelity spies keep in what they report")
    linger_decay: int = rule(2, 0, 100, C, "Fidelity an old rumour loses each epoch it lingers")
    atrocity_hatred: int = rule(20, 0, 100, C, "Ill will a community holds for the doer of an atrocity it heard of, at full fidelity")
    alarm_regions: int = rule(2, 0, 20, C, "Regions within which word of an enemy army alarms a community")
    alarm_defense: int = rule(5, 0, 100, C, "Defence a frightened town raises on hearing that an enemy army is near")
    ally_call: int = rule(10, 0, 100, C, "Goodwill and hostility allies show when a community calls on them against a coming army")
    legend_fidelity: int = rule(40, 0, 100, C, "Fidelity below which a lingering rumour hardens into legend")
    legend_years: int = span(50, 0, 2500, C, "Years a garbled rumour must linger before it becomes a legend")
    legend_tellers: int = rule(2, 1, 100, C, "Communities that must carry a rumour before it becomes a legend")
    context_lines: int = rule(8, 0, 100, C, "Rumours a mortal keeps in mind when it thinks and acts")
    backfill_epochs: int = rule(3, 0, 100, C, "Epochs of past happenings an old world remembers as rumour when the rumour mill first turns")
    cap: int = rule(600, 0, 10000000, C, "Most rumours passed on in one epoch, before the number of communities adds more")
    cap_per_community: int = rule(20, 0, 100000, C, "Further rumours passed on in one epoch for each living community")
    renown_spread_pct: int = rule(20, 0, 100, C, "Extra chance, at the full renown of the doer, that word of a deed is passed on (%)")
    contradiction_trust_loss: int = rule(3, 0, 100, C, "Trust in what is told that a community loses on hearing a happening told otherwise than it knew it")

    @property
    def legend_epochs(self) -> int:
        return self.epochs(self.legend_years)
