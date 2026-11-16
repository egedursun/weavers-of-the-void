from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

P = RuleGroup.POLITY


@dataclass(frozen=True)
class EnactmentRules:
    progress_pct: int = rule(60, 0, 300, P, "How far a proposal moves toward passage per point of support over opposition (%)")
    ruler_weight: int = rule(60, 0, 100, P, "Weight of the ruler's stance in an autocracy")
    council_weight: int = rule(30, 0, 100, P, "Weight of each council member's stance under a council")
    assembly_weight: int = rule(50, 0, 100, P, "Weight of the people's approval under an assembly")
    church_weight: int = rule(50, 0, 100, P, "Weight of the state church's stance under a divine rule")
    faction_weight_pct: int = rule(50, 0, 200, P, "How much a faction's influence over the realm counts in a stance (%)")
    estate_obstruct_pct: int = rule(80, 0, 200, P, "How much an estate with a council seat blocks a law it opposes (%)")
    stance_threshold: int = rule(15, 0, 100, P, "Distance from a law's values at which a member stands against it")
    stall_epochs: int = rule(3, 1, 20, P, "Epochs a proposal may stall before it fails")
    champion_cost: int = rule(8, 0, 100, P, "Reputation a champion loses when their proposal fails")
    event_pct: int = rule(30, 0, 100, P, "Chance each epoch a debated proposal stirs a debate, riot or compromise (%)")
    riot_unrest: int = rule(8, 0, 100, P, "Unrest a riot over a proposal adds to the capital")
    compromise_support: int = rule(15, 0, 100, P, "Support a compromise wins by softening a proposal")
    debate_progress: int = rule(10, 0, 100, P, "Progress a debate in the assembly adds to a well supported proposal")
    favour_magnitude: int = rule(20, 0, 100, P, "Size of the favour a champion owes each council member who carried the law")
    open_cap: int = rule(3, 1, 20, P, "Proposals a realm may debate at once")


@dataclass(frozen=True)
class TrialRules:
    witnesses: int = rule(3, 0, 20, P, "Witnesses an investigation hears for each crime")
    arbitration_ease: int = rule(5, 0, 100, P, "Evidence an arbiter needs less than a judge to settle against the accused")
    renown_sway_pct: int = rule(30, 0, 100, P, "Share of the accused's renown that sways an assembly to acquit (%)")
    inquisition_stress: int = rule(15, 0, 100, P, "Stress an inquisition lays on the accused")
    inquisition_bias: int = rule(15, 0, 100, P, "Evidence an inquisition presumes against the accused")
    made_judge_precision: int = rule(5, 0, 100, P, "Evidence a made judge reads from the record beyond a mortal judge")
    fitting_evidence: int = rule(8, 0, 100, P, "Evidence each found proof of a kind that fits the crime adds to a case")
    witness_reliability: int = rule(60, 0, 100, P, "Reliability of an unbiased witness")
    speak_pct: int = rule(60, 0, 100, P, "Chance an indifferent witness speaks against the culprit (%)")
    friend_at: int = rule(30, 0, 100, P, "Friendship at which a witness shields the accused")
    foe_at: int = rule(30, 0, 100, P, "Enmity at which a witness speaks against the accused")
    skill_evidence_pct: int = rule(50, 0, 200, P, "How much the investigator's skill at law adds to the evidence (%)")
    testimony_pct: int = rule(40, 0, 200, P, "How much each witness's testimony moves the evidence (%)")
    secret_evidence: int = rule(30, 0, 100, P, "Evidence a known secret about the crime adds")
    torture_reading: int = rule(-40, -100, 100, P, "Ethical reading of torture at or above which an investigator will use it")
    torture_evidence: int = rule(25, 0, 100, P, "Evidence a confession under torture adds, whether true or not")
    torture_hp: int = rule(8, 0, 100, P, "Harm questioning under torture deals")
    name_at: int = rule(35, 0, 100, P, "Evidence at which the investigator names the true culprit")
    scapegoat_pct: int = rule(50, 0, 100, P, "Chance a weak investigation blames a scapegoat rather than dropping the case (%)")
    standard: int = rule(50, 0, 100, P, "Weight of evidence a court needs to convict")
    arbitrary_swing: int = rule(25, 0, 100, P, "How far an arbitrary judge's whim moves a verdict")
    bias_pct: int = rule(25, 0, 100, P, "How much a judge's regard for the accused moves a verdict (%)")
    forged_evidence: int = rule(55, 0, 100, P, "Evidence a forged frame brings to court")
    ordeal_pct: int = rule(50, 0, 100, P, "Chance the innocent survive an ordeal (%)")
    combat_hp: int = rule(10, 0, 100, P, "Harm the loser of a trial by combat takes")
    grievance_grudge: int = rule(30, 0, 100, P, "Enmity the kin of the wrongly convicted feel toward the judge")
    martyr_renown: int = rule(12, 0, 100, P, "Renown the wrongly executed win as martyrs")
    wrongful_unrest: int = rule(6, 0, 100, P, "Unrest a wrongful conviction stirs in its city")
    injustice_epochs: int = rule(4, 1, 50, P, "Epochs a city remembers a wrongful conviction")
    injustice_grievance: int = rule(5, 0, 100, P, "Grievance toward the realm each remembered wrongful conviction causes")
