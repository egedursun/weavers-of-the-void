from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

P = RuleGroup.POLITY
W = RuleGroup.WAR_AND_DIPLOMACY
D = RuleGroup.THE_DIVINE


@dataclass(frozen=True)
class LegalSystemRules:
    adopt_pct: int = rule(20, 0, 100, P, "Chance each epoch a realm changes its legal system to the one its learning and faith now favour (%)")
    compurgator_weight: int = rule(12, 0, 100, P, "Evidence each friend who swears for the accused takes away under customary law")
    lawspeaker_pct: int = rule(20, 0, 200, P, "Share of the lawspeaker's intelligence added to the evidence under customary law (%)")
    code_bonus: int = rule(10, 0, 100, P, "Evidence a written code adds, since judges apply it and not their whims")
    clergy_bonus: int = rule(20, 0, 100, P, "Evidence a religious court adds against blasphemy")
    piety_pct: int = rule(20, 0, 200, P, "Share of the accused's piety a religious court takes off the evidence (%)")
    follow_pct: int = rule(80, 0, 100, P, "Chance a court follows a precedent at full authority (%)")
    oracle_truth_pct: int = rule(60, 0, 100, P, "Chance an oracle left unanswered by its god names the truth (%)")


@dataclass(frozen=True)
class PrecedentRules:
    authority: int = rule(30, 0, 100, P, "Authority a new ruling has as a precedent")
    court_step: int = rule(20, 0, 100, P, "Authority each court above the local one adds to its rulings")
    follow_gain: int = rule(5, 0, 100, P, "Authority a precedent gains each time a court follows it")
    decay: int = rule(2, 0, 100, P, "Authority a precedent loses each epoch")
    drift_pct: int = rule(10, 0, 100, P, "Chance each epoch a judge whose beliefs oppose a precedent sets it aside (%)")


@dataclass(frozen=True)
class AppealRules:
    fee: int = rule(20, 0, 100000, P, "Coin an appeal to the next court costs")
    fee_step: int = rule(20, 0, 100000, P, "Coin each further court adds to the fee")
    delay: int = rule(1, 0, 100, P, "Epochs an appeal waits before it is heard")
    reversal_pct: int = rule(20, 0, 100, P, "Chance an appeal is upheld at no evidence (%)")
    evidence_pct: int = rule(50, 0, 200, P, "Share of the evidence that weighs against an appeal (%)")
    advocate_pct: int = rule(40, 0, 200, P, "Share of an advocate's skill in law and oratory taken off the evidence (%)")
    advocate_fee: int = rule(10, 0, 100000, P, "Coin an advocate charges for a trial")


@dataclass(frozen=True)
class RegistryRules:
    title_pct: int = rule(30, 0, 100, P, "Chance each epoch a town under a written code registers its ruler's title (%)")
    enforce_pct: int = rule(40, 0, 100, P, "Share of a registered debt a court makes the debtor pay each epoch (%)")
    unregistered_pct: int = rule(30, 0, 100, P, "Chance an unregistered debt is paid when the lender is stronger (%)")
    dispute_unrest: int = rule(5, 0, 100, P, "Unrest a land dispute raises in its town")
    dispute_grudge: int = rule(20, 0, 100, P, "Grudge the loser of a land dispute holds against the winner")


@dataclass(frozen=True)
class JurisdictionRules:
    claim_pct: int = rule(15, 0, 100, P, "Chance each epoch a church, guild or foreign realm claims its own courts in a realm (%)")
    growth: int = rule(4, 0, 100, P, "Strength a claim gains each epoch")
    struggle_at: int = rule(60, 0, 100, P, "Strength past which a claim becomes a struggle with the crown")
    struggle_unrest: int = rule(5, 0, 100, P, "Unrest a struggle over courts raises in the realm's seat each epoch")
    struggle_relation: int = rule(5, 0, 100, P, "Regard the realm and the claimant lose each epoch of the struggle")
    crown_pct: int = rule(25, 0, 100, P, "Chance each epoch the crown ends a struggle by force, at the full strength of its stability (%)")
    leniency: int = rule(20, 0, 100, P, "Evidence a claimant's own court takes off a case against one of its members")


@dataclass(frozen=True)
class PardonRules:
    friend_pct: int = rule(25, 0, 100, P, "Chance each epoch a ruler pardons a friend held for a crime (%)")
    friend_at: int = rule(40, 0, 100, P, "Friendship past which a ruler pardons")
    corruption_infamy: int = rule(8, 0, 100, P, "Infamy a ruler earns pardoning a friend")
    mercy_renown: int = rule(5, 0, 100, P, "Renown a ruler earns pardoning one wrongly condemned, or any pardon where mercy is honoured")
    tyranny_infamy: int = rule(5, 0, 100, P, "Infamy a ruler earns pardoning where mercy is scorned")
    amnesty_epochs: int = rule(1, 0, 100, P, "Epochs after a new ruler takes the throne, or a civil war ends, in which an amnesty may be declared")
    amnesty_pct: int = rule(40, 0, 100, P, "Chance a new ruler declares an amnesty (%)")


@dataclass(frozen=True)
class OutlawRules:
    bounty: int = rule(30, 0, 100000, P, "Coin a realm puts on an outlaw who fled its courts")
    hunt_pct: int = rule(25, 0, 100, P, "Chance each epoch a bounty hunter catches an outlaw, at full skill (%)")
    hunter_skill: int = rule(20, 0, 100, P, "Skill in tracking or fighting a mortal needs to hunt bounties")
    escape_renown: int = rule(4, 0, 100, P, "Renown an outlaw gains each epoch they escape the hunt")
    band_at: int = rule(3, 2, 100, P, "Outlaws of one realm who gather into a band")
    hero_at: int = rule(50, 0, 100, P, "Renown past which an outlaw is a folk hero of the folk they spare")
    hero_unrest: int = rule(3, 0, 100, P, "Unrest a folk hero stirs each epoch in the town they are sheltered in")


@dataclass(frozen=True)
class PrisonRules:
    term: int = rule(3, 1, 100, P, "Epochs of a prison sentence")
    capacity: int = rule(10, 1, 10000, P, "Prisoners each level of a prison holds before it is crowded")
    hunger_hp: int = rule(4, 0, 100, P, "Hit points a prisoner loses each epoch when food runs short")
    food_at: int = rule(30, 0, 100, P, "Food below which prisoners go hungry")
    sickness_pct: int = rule(20, 0, 100, P, "Chance each epoch a prisoner in a full prison falls sick (%)")
    sickness_hp: int = rule(3, 0, 100, P, "Hit points sickness takes from a prisoner")
    gang_gain: int = rule(10, 0, 100, P, "Rank a strong prisoner gains in the gangs each epoch")
    escape_pct: int = rule(10, 0, 100, P, "Chance each epoch a prisoner escapes, at full crowding and gang strength (%)")
    stigma: int = rule(6, 0, 100, P, "Infamy a released prisoner carries")
    intrigue_gain: int = rule(8, 0, 100, P, "Skill in intrigue a prisoner learns inside each epoch")


@dataclass(frozen=True)
class SpyDepthRules:
    money_loyalty: int = rule(35, 0, 100, W, "Loyalty of an agent recruited by money")
    ideology_loyalty: int = rule(85, 0, 100, W, "Loyalty of an agent recruited by belief")
    compromise_loyalty: int = rule(45, 0, 100, W, "Loyalty of an agent recruited by a hook")
    ego_loyalty: int = rule(55, 0, 100, W, "Loyalty of an agent recruited by vanity or grievance")
    belief_fit: int = rule(20, 0, 100, W, "Closeness of values past which a recruit joins for belief")
    double_cross_pct: int = rule(10, 0, 100, W, "Chance each epoch an agent at no loyalty crosses to the other side (%)")
    cell_size: int = rule(3, 1, 20, W, "Agents a cell holds")
    flat_speed_pct: int = rule(30, 0, 200, W, "Extra depth a network without cells gains each epoch (%)")
    cell_exposure: int = rule(20, 0, 100, W, "Exposure a caught agent brings on the rest of their cell")
    flat_exposure: int = rule(15, 0, 100, W, "Exposure a caught agent brings on every agent of a network without cells")
    safe_house_relief: int = rule(10, 0, 100, W, "Exposure a cell's safe house spares its agents when one is caught")


@dataclass(frozen=True)
class MoleHuntRules:
    hunt_pct: int = rule(15, 0, 100, W, "Chance each epoch a spymaster hunts for moles (%)")
    paranoid_pct: int = rule(25, 0, 100, W, "Extra hunt chance and false accusation chance of a paranoid spymaster (%)")
    catch_pct: int = rule(40, 0, 100, W, "Chance a hunt finds a mole who is there, at full skill (%)")
    false_pct: int = rule(10, 0, 100, W, "Chance a hunt accuses an innocent official (%)")
    defect_pct: int = rule(30, 0, 100, W, "Chance a wrongly accused official defects rather than be purged (%)")
    purge_loyalty: int = rule(5, 0, 100, W, "Loyalty the realm's officials lose after a purge of the innocent")
    paranoia_pct: int = rule(30, 0, 100, W, "Chance a spymaster who purged an innocent grows paranoid, and hunts and accuses more (%)")


@dataclass(frozen=True)
class DefectionRules:
    secrets: int = rule(3, 0, 100, W, "Secrets of their old masters a defector brings at most")
    traitor_infamy: int = rule(10, 0, 100, W, "Infamy a defector earns at home")
    hero_renown: int = rule(6, 0, 100, W, "Renown a defector earns abroad")
    reprisal_pct: int = rule(20, 0, 100, W, "Chance each epoch an unprotected defector is killed by the realm they left (%)")


@dataclass(frozen=True)
class ForensicsRules:
    blade_stealth: int = rule(0, 0, 100, W, "How well a death by the blade hides itself")
    poison_stealth: int = rule(40, 0, 100, W, "How well a death by poison hides itself")
    accident_stealth: int = rule(60, 0, 100, W, "How well a staged accident hides itself")
    disease_stealth: int = rule(70, 0, 100, W, "How well a deliberate infection hides itself")
    curse_stealth: int = rule(80, 0, 100, W, "How well a death by a curse hides itself")
    examiner_pct: int = rule(60, 0, 200, W, "Share of the examiner's skill in medicine that sees through a hidden death (%)")
    theory_bonus: int = rule(15, 0, 100, W, "Recognition the medicine of the victim's town adds, at full knowledge")
    investigate_pct: int = rule(50, 0, 100, W, "Chance a death recognised as murder opens a case (%)")


@dataclass(frozen=True)
class DivineSpyRules:
    spy_pct: int = rule(30, 0, 100, D, "Chance each epoch a servitor posted as a spy learns a secret of its post (%)")
    dream_secrets: int = rule(2, 0, 100, D, "Secrets reading a mortal's dreams reveals at most")
    ward_pct: int = rule(70, 0, 100, D, "Chance a ward or a rival god's stronger dominion turns divine spying aside (%)")
