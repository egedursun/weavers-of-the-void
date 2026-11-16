from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

G = RuleGroup.MORTALS


@dataclass(frozen=True)
class StandingRules:
    renown_decay_pct: int = rule(8, 0, 100, G, "Share of a mortal's renown that fades each epoch (%)")
    glory_renown: int = rule(10, 0, 100, G, "Renown a mortal wins from glory in battle")
    honour_kept_oath: int = rule(5, 0, 100, G, "Honour a mortal gains for each oath kept")
    honour_broken_oath: int = rule(15, 0, 100, G, "Honour a mortal loses for each oath broken")
    infamy_atrocity: int = rule(15, 0, 100, G, "Infamy a mortal gains for an atrocity")
    infamy_decay: int = rule(2, 0, 100, G, "Infamy that fades each epoch")
    wealth_drift_pct: int = rule(20, 0, 100, G, "How fast personal wealth moves toward what a mortal's class earns (%)")
    wealth_status_pct: int = rule(80, 0, 200, G, "Personal wealth a calling brings, as a share of the standing it holds (%)")
    office_legitimacy: int = rule(50, 0, 100, G, "Legitimacy an office holder starts from")
    patronage_wealth: int = rule(40, 0, 100, G, "Wealth above which a mortal funds works and artists")
    patronage_cost: int = rule(10, 0, 100, G, "Wealth a patron spends on one work")
    patronage_renown: int = rule(4, 0, 100, G, "Renown a patron wins from a funded work")
    bribe_cost: int = rule(8, 0, 100, G, "Wealth a mortal spends on one bribe")
    bribe_effect: int = rule(15, 0, 100, G, "How much a bribe sways its taker")
    legitimacy_honour_pct: int = rule(30, 0, 100, G, "How much honour shapes an office holder's legitimacy (%)")
    legitimacy_infamy_pct: int = rule(30, 0, 100, G, "How much infamy erodes an office holder's legitimacy (%)")
    legitimacy_renown_pct: int = rule(20, 0, 100, G, "How much renown lifts an office holder's legitimacy (%)")
    glorious_death_prestige: int = rule(6, 0, 100, G, "House prestige gained when a member dies gloriously")
    shameful_death_prestige: int = rule(8, 0, 100, G, "House prestige lost when a member is executed or dies in shame")
    decapitation_exposure_pct: int = rule(300, 100, 1000, G, "How much more a commander is struck when the enemy seeks to cut off the head (%)")


@dataclass(frozen=True)
class PunishmentRules:
    fine_wealth: int = rule(20, 0, 100, G, "Wealth a fine takes")
    branding_infamy: int = rule(10, 0, 100, G, "Infamy a branding marks a mortal with")
    mutilation_severity: int = rule(5, 1, 5, G, "Severity of a mutilation by law")
    death_for_treason: int = rule(1, 0, 1, G, "Treason can be punished by death")
    death_for_blasphemy: int = rule(0, 0, 1, G, "Blasphemy can be punished by death")
    cruelty_infamy: int = rule(5, 0, 100, G, "Infamy a ruler gains for each mutilation their law orders")
    blasphemy_chance: int = rule(3, 0, 100, G, "Chance each epoch a heretic in a zealous land is tried for blasphemy (%)")
    treason_chance: int = rule(30, 0, 100, G, "Chance a discovered plotter is tried for treason (%)")
    exile_chance: int = rule(40, 0, 100, G, "Chance a mild law exiles rather than maims (%)")


@dataclass(frozen=True)
class SentenceRules:
    severity_infamy_pct: int = rule(10, 0, 100, G, "Infamy a conviction marks per point of the crime's severity (%)")
    restitution_wealth: int = rule(15, 0, 100, G, "Wealth a sentence of restitution makes the culprit restore")
    compensation_wealth: int = rule(30, 0, 100, G, "Wealth a culprit pays the wronged and their kin")
    labour_term: int = rule(3, 1, 50, G, "Epochs a sentence of penal labour lasts")
    reeducation_term: int = rule(2, 1, 50, G, "Epochs a sentence of reeducation keeps a culprit")
    reeducation_loyalty: int = rule(10, 0, 100, G, "Loyalty a reeducation instils")
    outlawry_infamy: int = rule(20, 0, 100, G, "Infamy outlawry marks a culprit with")
    excommunication_piety: int = rule(15, 0, 100, G, "Piety lost by one cast out of the faith")
    penance_piety: int = rule(5, 0, 100, G, "Piety a penance gives")
    work_stress: int = rule(8, 0, 100, G, "Stress a sentence of work, penance or arrest lays on a culprit")
    work_gain: int = rule(2, 0, 100, G, "Sanitation a sentence of community work gives the town")
    arrest_renown: int = rule(3, 0, 100, G, "Renown lost under house arrest")
    probation_infamy: int = rule(3, 0, 100, G, "Infamy probation marks a culprit with")
    deterrence_pct: int = rule(5, 0, 100, G, "Crime a sentence takes from its town per point of deterrence above recidivism (%)")
    cost_coin: int = rule(1, 0, 100, G, "Treasury each point of a sentence's cost takes from the polity")
    legitimacy_step: int = rule(5, 0, 100, G, "Legitimacy a sentence gains or loses where local values favour or oppose it")


@dataclass(frozen=True)
class EquipmentRules:
    mount_mobility_pct: int = rule(140, 100, 400, G, "Mobility of a mounted mortal (%)")
    mount_melee_pct: int = rule(115, 100, 400, G, "Fighting strength of a mounted mortal (%)")
    focus_magic_pct: int = rule(130, 100, 400, G, "Spellcraft of a mortal with a magic focus (%)")
    off_hand_melee_pct: int = rule(110, 100, 400, G, "Fighting strength from a second weapon or shield (%)")
