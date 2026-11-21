from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import Spanned, rule

S = RuleGroup.WAR_AND_DIPLOMACY


@dataclass(frozen=True)
class MassWeaponsRules(Spanned):
    deterrence_attack_cut_pct: int = rule(50, 0, 100, S, "Share of attacks on a holder a fully credible posture prevents (%)")
    doom_per_reach: int = rule(5, 0, 100, S, "Doom a use adds for each step of its reach")
    remnant_harm_per_density: int = rule(2, 0, 50, S, "Share of the people of a remnant's land it harms in an epoch at full density, in tenths of a percent")
    remnant_decay_per_epoch: int = rule(3, 0, 50, S, "Density a remnant loses in an epoch")
    clearance_per_budget: int = rule(1, 0, 20, S, "Density cleared for each hundred of treasury spent on clearance")
    stage_visibility_pct: int = rule(30, 0, 100, S, "Chance that rivals see a programme reach a new stage (%)")
    readiness_step: int = rule(20, 0, 100, S, "Readiness a programme gains in an epoch when it is paid for")
    programme_cost: int = rule(100, 0, 100000, S, "Treasury a programme costs in an epoch for each step of its reach")
    test_chance_pct: int = rule(20, 0, 100, S, "Chance in an epoch that a ready weapon is tested (%)")
    test_credibility: int = rule(15, 0, 100, S, "Credibility a test lends the holder's postures")
    bluff_exposure_pct: int = rule(10, 0, 100, S, "Chance in an epoch that a posture with no ready weapon behind it is exposed (%)")
    bluff_loss: int = rule(30, 0, 100, S, "Credibility an exposed bluff loses")
    arms_race_pct: int = rule(25, 0, 100, S, "Chance that a rival who sees a programme begins its own (%)")
    use_kill_pct: int = rule(20, 0, 100, S, "Share of the people within a use's reach a use at full harm kills (%)")
    remnant_density: int = rule(40, 0, 100, S, "Density of the remnant a use or a war leaves")
    clearance_chance_pct: int = rule(20, 0, 100, S, "Chance in an epoch that a realm clears remnants in its land (%)")
    clearance_spend: int = rule(200, 0, 100000, S, "Treasury a realm spends when it clears remnants")
    limit_treaty_chance_pct: int = rule(10, 0, 100, S, "Chance in an epoch that two armed rivals bind their arsenals by treaty (%)")
    resident_harm_chance_pct: int = rule(20, 0, 100, S, "Chance in an epoch that a remnant at full density kills one who lives in its land (%)")
    seek_chance_pct: int = rule(5, 0, 100, S, "Chance in an epoch that a realm with rivals begins a programme whose making it knows (%)")
