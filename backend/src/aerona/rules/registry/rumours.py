from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

C = RuleGroup.CIVILIZATION


@dataclass(frozen=True)
class RumoursRules:
    min_magnitude: int = rule(30, 0, 100, C, "Weight a happening needs before word of it travels")
    hop_loss: int = rule(8, 0, 100, C, "Fidelity a rumour loses at each telling")
    distance_loss: int = rule(3, 0, 100, C, "Fidelity a rumour loses for each region it crosses")
    barrier_loss: int = rule(30, 0, 100, C, "Fidelity lost crossing a tongue nobody shares, scaled by how little is understood")
    written_pct: int = rule(50, 0, 100, C, "Share of the garbling spared where the hearers read and write a settled tongue (%)")
    floor: int = rule(10, 0, 100, C, "Fidelity below which nobody bothers to pass a rumour on")
    max_hops: int = rule(6, 1, 100, C, "Most tellings a rumour survives")
    route_chance: int = rule(60, 0, 100, C, "Word passes along a trade road in an epoch (%)")
    pilgrimage_chance: int = rule(30, 0, 100, C, "Word passes between pilgrims of one faith in an epoch (%)")
    journey_chance: int = rule(50, 0, 100, C, "Travellers carry word to where they arrive (%)")
    spy_chance: int = rule(80, 0, 100, C, "Spies report what is said in the land they watch (%)")
    spy_bonus: int = rule(15, 0, 100, C, "Fidelity spies keep in what they report")
    linger_decay: int = rule(2, 0, 100, C, "Fidelity an old rumour loses each epoch it lingers")
    atrocity_hatred: int = rule(20, 0, 100, C, "Ill will a community holds for the doer of an atrocity it heard of, at full fidelity")
    alarm_regions: int = rule(2, 0, 20, C, "Regions within which word of an enemy army alarms a community")
    alarm_defense: int = rule(5, 0, 100, C, "Defence a frightened town raises on hearing that an enemy army is near")
    ally_call: int = rule(10, 0, 100, C, "Goodwill and hostility allies show when a community calls on them against a coming army")
    legend_fidelity: int = rule(40, 0, 100, C, "Fidelity below which a lingering rumour hardens into legend")
    legend_epochs: int = rule(3, 0, 100, C, "Epochs a garbled rumour must linger before it becomes a legend")
    legend_tellers: int = rule(2, 1, 100, C, "Communities that must carry a rumour before it becomes a legend")
    context_lines: int = rule(8, 0, 100, C, "Rumours a mortal keeps in mind when it thinks and acts")
    backfill_epochs: int = rule(3, 0, 100, C, "Epochs of past happenings an old world remembers as rumour when the rumour mill first turns")
    cap: int = rule(600, 0, 100000, C, "Most rumours passed on in one epoch")
