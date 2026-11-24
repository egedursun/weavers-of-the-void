from collections.abc import Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.intrigue import BeliefSource, FavourOrigin, HookDemand, HookSource, IdentityReason, IntrigueSecret, PlotKind, SchemePhase
from aerona.domain.enums.mind import ActKind
from aerona.domain.enums.records import StepAction


@dataclass(frozen=True)
class SecretSpec:
    kind: IntrigueSecret
    label: str
    severity: int
    act: ActKind | None = None


SECRETS: dict[IntrigueSecret, SecretSpec] = {
    spec.kind: spec
    for spec in (
        SecretSpec(IntrigueSecret.AFFAIR, "An affair", 45, ActKind.ADULTERY),
        SecretSpec(IntrigueSecret.ILLEGITIMATE_CHILD, "A child born outside a marriage", 40),
        SecretSpec(IntrigueSecret.MURDER, "A murder", 85, ActKind.KILLING_OUTSIDER),
        SecretSpec(IntrigueSecret.HERESY, "A heresy", 50),
        SecretSpec(IntrigueSecret.SECRET_CULT_MEMBERSHIP, "Membership of a hidden cult", 45),
        SecretSpec(IntrigueSecret.DEBT, "A hidden debt", 25),
        SecretSpec(IntrigueSecret.CRIME, "A crime", 55, ActKind.THEFT),
        SecretSpec(IntrigueSecret.COWARDICE_IN_BATTLE, "Cowardice in battle", 50, ActKind.COWARDICE),
        SecretSpec(IntrigueSecret.HIDDEN_CONDITION, "A hidden illness or madness", 35),
        SecretSpec(IntrigueSecret.FALSE_IDENTITY, "A false identity", 60),
        SecretSpec(IntrigueSecret.DEAL_WITH_OUTER_BEING, "A deal with an outer being", 75, ActKind.VOID_MAGIC),
        SecretSpec(IntrigueSecret.TRUE_PARENTAGE, "A true parentage", 55),
        SecretSpec(IntrigueSecret.BROKEN_OATH, "A broken oath", 50, ActKind.OATHBREAKING),
        SecretSpec(IntrigueSecret.ECOSABOTAGE, "A sabotage of the land", 70),
        SecretSpec(IntrigueSecret.BROKEN_CIPHER, "A broken cipher", 65),
        SecretSpec(IntrigueSecret.TRUE_HISTORY, "The true history behind an official account", 55),
        SecretSpec(IntrigueSecret.HIDDEN_POWER, "A concealed innate power", 60),
        SecretSpec(IntrigueSecret.FORGERY, "A forgery made or used", 60, ActKind.THEFT),
        SecretSpec(IntrigueSecret.ILLNESS, "A hidden illness", 50),
    )
}


@dataclass(frozen=True)
class SchemeSpec:
    kind: PlotKind
    label: str
    difficulty: int
    secrecy: int
    agents: int
    secret: IntrigueSecret | None = None
    act: ActKind | None = None
    needs_target: bool = True


PLOT_STEPS: Mapping[PlotKind, StepAction] = {
    PlotKind.SWAY: StepAction.PERSUADE,
    PlotKind.FABRICATE_CLAIM: StepAction.FORGE_RECORD,
    PlotKind.FABRICATE_HOOK: StepAction.DECEIVE,
    PlotKind.FRAME: StepAction.DECEIVE,
    PlotKind.FORGE_LETTER: StepAction.FORGE_RECORD,
    PlotKind.FORGE_WORK: StepAction.DECEIVE,
}
SCHEMES: dict[PlotKind, SchemeSpec] = {
    spec.kind: spec
    for spec in (
        SchemeSpec(PlotKind.MURDER, "Murder", 60, 50, 2, IntrigueSecret.MURDER, ActKind.KILLING_OUTSIDER),
        SchemeSpec(PlotKind.ABDUCT, "Abduction", 55, 45, 2, IntrigueSecret.CRIME, ActKind.TAKING_CAPTIVES),
        SchemeSpec(PlotKind.SEDUCE, "Seduction", 35, 60, 0, IntrigueSecret.AFFAIR, ActKind.ADULTERY),
        SchemeSpec(PlotKind.SWAY, "Swaying", 25, 70, 0),
        SchemeSpec(PlotKind.FABRICATE_CLAIM, "Fabricated claim", 50, 55, 1, IntrigueSecret.CRIME),
        SchemeSpec(PlotKind.FABRICATE_HOOK, "Fabricated hook", 45, 55, 1, IntrigueSecret.CRIME),
        SchemeSpec(PlotKind.STEAL_RELIC, "Theft of a relic", 50, 50, 1, IntrigueSecret.CRIME, ActKind.THEFT),
        SchemeSpec(PlotKind.COUP, "Coup", 75, 40, 3, IntrigueSecret.CRIME, ActKind.TREASON),
        SchemeSpec(PlotKind.POISON_WELL, "Poisoned well", 55, 45, 1, IntrigueSecret.CRIME),
        SchemeSpec(PlotKind.FRAME, "Framing", 45, 55, 1, IntrigueSecret.CRIME),
        SchemeSpec(PlotKind.ELOPE, "Elopement", 30, 50, 0),
        SchemeSpec(PlotKind.CONVERT_SECRETLY, "Secret conversion", 35, 60, 0, IntrigueSecret.SECRET_CULT_MEMBERSHIP),
        SchemeSpec(PlotKind.SABOTAGE_WEDDING, "Sabotaged wedding", 40, 55, 1),
        SchemeSpec(PlotKind.FREE_PRISONER, "Freeing a prisoner", 55, 45, 2, IntrigueSecret.CRIME),
        SchemeSpec(PlotKind.ECOSABOTAGE, "Sabotage of the land", 50, 50, 1, IntrigueSecret.ECOSABOTAGE, ActKind.DESECRATION),
        SchemeSpec(PlotKind.LEARN_TRUE_NAME, "Learning a true name", 70, 60, 1),
        SchemeSpec(PlotKind.FORGE_LETTER, "Forged letter", 50, 55, 1, IntrigueSecret.CRIME),
        SchemeSpec(PlotKind.GEAS_TRAP, "Geas trap", 60, 50, 1, IntrigueSecret.CRIME),
        SchemeSpec(PlotKind.HIDE_FLEET, "Hidden fleet", 55, 60, 1, IntrigueSecret.CRIME),
        SchemeSpec(PlotKind.FORGE_WORK, "Forged work", 45, 60, 0, IntrigueSecret.CRIME),
        SchemeSpec(PlotKind.FIX_CONTEST, "Fixed contest", 40, 55, 1, IntrigueSecret.CRIME, ActKind.FIXING_CONTESTS),
        SchemeSpec(PlotKind.INCITE_CROWD, "Stirred crowd", 50, 40, 2, IntrigueSecret.CRIME),
    )
}

SECRET_LABELS: dict[IntrigueSecret, str] = {kind: spec.label for kind, spec in SECRETS.items()}
SCHEME_LABELS: dict[PlotKind, str] = {kind: spec.label for kind, spec in SCHEMES.items()}
PHASE_LABELS: dict[SchemePhase, str] = {
    SchemePhase.RECRUIT: "Recruiting agents",
    SchemePhase.PREPARE: "Preparing",
    SchemePhase.EXECUTE: "Striking",
    SchemePhase.SUCCEEDED: "Succeeded",
    SchemePhase.FAILED: "Failed",
    SchemePhase.EXPOSED: "Exposed",
    SchemePhase.ABANDONED: "Abandoned",
}
HOOK_SOURCE_LABELS: dict[HookSource, str] = {
    HookSource.SECRET: "A secret",
    HookSource.DEBT: "A debt",
    HookSource.FAVOUR: "A favour",
    HookSource.HOSTAGE: "A hostage",
    HookSource.TRUE_NAME: "A true name",
    HookSource.DEPENDENCE: "Dependence",
    HookSource.AFFECTION: "Affection",
}
HOOK_DEMAND_LABELS: dict[HookDemand, str] = {
    HookDemand.MARRIAGE: "Agree to a marriage",
    HookDemand.STEP_DOWN: "Step down",
    HookDemand.SUPPORT: "Lend support",
    HookDemand.VOTE: "Vote as told on the laws under debate",
    HookDemand.LAW: "Back the holder's laws with the weight of rule",
    HookDemand.APPOINTMENT: "Appoint the holder to an office",
    HookDemand.SILENCE: "Keep silent before a court",
    HookDemand.PAYMENT: "Pay the holder",
    HookDemand.RELEASE: "Let someone go",
    HookDemand.INFORMATION: "Tell what it knows",
}
FAVOUR_LABELS: dict[FavourOrigin, str] = {
    FavourOrigin.GIFT: "A gift",
    FavourOrigin.RESCUE: "A rescue",
    FavourOrigin.WAR_SUPPORT: "Support in a war",
    FavourOrigin.SUCCESSION_SUPPORT: "Support in a succession",
    FavourOrigin.SCHEME_AID: "Aid in a scheme",
    FavourOrigin.VOTE: "A vote that carried a law",
    FavourOrigin.RELIEF: "Aid in a stricken hour",
    FavourOrigin.HOSPITALITY: "Shelter given",
    FavourOrigin.RANSOM: "A ransom paid",
    FavourOrigin.HEALING: "A healing",
    FavourOrigin.TEACHING: "Teaching",
}
IDENTITY_LABELS: dict[IdentityReason, str] = {
    IdentityReason.SPY: "A spy's cover",
    IdentityReason.BLOOD_CURSE: "A blood-cursed one's mask",
    IdentityReason.EXILE: "An exile's new name",
    IdentityReason.IMPOSTOR: "An impostor's guise",
    IdentityReason.HIDDEN_POWER: "A name kept apart from one's powers",
    IdentityReason.FUGITIVE: "A fugitive's other name",
    IdentityReason.HIDDEN_FAITH: "A believer's hidden faith",
    IdentityReason.PASSING_KIND: "A being passing as another kind",
    IdentityReason.PROTECTION: "A name worn to protect kin",
}

BELIEF_ATTRIBUTES: tuple[str, ...] = ("wealth", "defense", "population", "prosperity")
BELIEF_ATTRIBUTE_LABELS: dict[str, str] = {
    "wealth": "Wealth",
    "defense": "Defences",
    "population": "Population",
    "prosperity": "Prosperity",
    "soldiers": "Soldiers in the field",
    "secret_severity": "Weight of a secret",
}
BELIEF_SOURCE_LABELS: Mapping[BeliefSource, str] = total(
    BeliefSource,
    {
        BeliefSource.OBSERVATION: "Seen with their own eyes",
        BeliefSource.MESSAGE: "Told in a message",
        BeliefSource.RUMOUR: "Heard as rumour",
        BeliefSource.SPY: "Reported by spies",
        BeliefSource.SCOUT: "Reported by scouts",
        BeliefSource.RECORDS: "Read in records",
        BeliefSource.DECEPTION: "Planted by a deceiver",
        BeliefSource.NETWORK: "Passed along a network",
        BeliefSource.FORESIGHT: "Foreseen",
        BeliefSource.MIND_READING: "Read in a mind",
        BeliefSource.INTRUSION: "Taken by intrusion",
        BeliefSource.SURVEILLANCE: "Reported by watchers",
        BeliefSource.MADE_MIND_REPORT: "Reported by a made mind",
        BeliefSource.DREAM: "Seen in a dream",
        BeliefSource.OMEN: "Read in an omen",
    },
)
PRICE_PREFIX = "price."


def belief_label(attribute: str) -> str:
    if attribute.startswith(PRICE_PREFIX):
        return f"Price of {attribute.removeprefix(PRICE_PREFIX).replace('_', ' ')}"
    return BELIEF_ATTRIBUTE_LABELS.get(attribute, attribute.replace("_", " ").capitalize())


BELIEF_CHOICES: dict[str, str] = {
    **{key: label for key, label in BELIEF_ATTRIBUTE_LABELS.items()},
    **{f"{PRICE_PREFIX}{commodity.value}": belief_label(f"{PRICE_PREFIX}{commodity.value}") for commodity in CommodityKind},
}
SCHEME_DONE: Mapping[PlotKind, str] = total(
    PlotKind,
    {
        PlotKind.MURDER: "murdered {target}",
        PlotKind.ABDUCT: "abducted {target}",
        PlotKind.SEDUCE: "seduced {target}",
        PlotKind.SWAY: "swayed {target}",
        PlotKind.FABRICATE_CLAIM: "fabricated a claim against {target}",
        PlotKind.FABRICATE_HOOK: "fabricated a hold over {target}",
        PlotKind.STEAL_RELIC: "stole a relic from {target}",
        PlotKind.COUP: "carried out a coup against {target}",
        PlotKind.POISON_WELL: "poisoned a well of {target}",
        PlotKind.FRAME: "framed {target}",
        PlotKind.ELOPE: "eloped with {target}",
        PlotKind.CONVERT_SECRETLY: "converted {target} in secret",
        PlotKind.SABOTAGE_WEDDING: "sabotaged the wedding of {target}",
        PlotKind.FREE_PRISONER: "freed a prisoner held by {target}",
        PlotKind.ECOSABOTAGE: "sabotaged the land of {target}",
        PlotKind.LEARN_TRUE_NAME: "learned the true name of {target}",
        PlotKind.FORGE_LETTER: "forged a letter against {target}",
        PlotKind.GEAS_TRAP: "caught {target} in a geas trap",
        PlotKind.HIDE_FLEET: "hid a fleet from {target}",
        PlotKind.FORGE_WORK: "forged a work to deceive {target}",
        PlotKind.FIX_CONTEST: "fixed a contest against {target}",
        PlotKind.INCITE_CROWD: "stirred a crowd against {target}",
    },
)
SCHEME_PLOTTED: Mapping[PlotKind, str] = total(
    PlotKind,
    {
        PlotKind.MURDER: "to murder them",
        PlotKind.ABDUCT: "to abduct them",
        PlotKind.SEDUCE: "to seduce them",
        PlotKind.SWAY: "to sway them",
        PlotKind.FABRICATE_CLAIM: "to fabricate a claim against them",
        PlotKind.FABRICATE_HOOK: "to fabricate a hold over them",
        PlotKind.STEAL_RELIC: "to steal a relic from them",
        PlotKind.COUP: "to overthrow them",
        PlotKind.POISON_WELL: "to poison their well",
        PlotKind.FRAME: "to frame them",
        PlotKind.ELOPE: "to elope with them",
        PlotKind.CONVERT_SECRETLY: "to convert them in secret",
        PlotKind.SABOTAGE_WEDDING: "to sabotage their wedding",
        PlotKind.FREE_PRISONER: "to free a prisoner they held",
        PlotKind.ECOSABOTAGE: "to sabotage their land",
        PlotKind.LEARN_TRUE_NAME: "to learn their true name",
        PlotKind.FORGE_LETTER: "to forge a letter against them",
        PlotKind.GEAS_TRAP: "to catch them in a geas trap",
        PlotKind.HIDE_FLEET: "to hide a fleet from them",
        PlotKind.FORGE_WORK: "to forge a work to deceive them",
        PlotKind.FIX_CONTEST: "to fix a contest against them",
        PlotKind.INCITE_CROWD: "to stir a crowd against them",
    },
)
SECRET_TOLD: Mapping[IntrigueSecret, str] = total(
    IntrigueSecret,
    {
        IntrigueSecret.AFFAIR: "an affair",
        IntrigueSecret.ILLEGITIMATE_CHILD: "a child born outside a marriage",
        IntrigueSecret.MURDER: "a murder",
        IntrigueSecret.HERESY: "a heresy held in private",
        IntrigueSecret.SECRET_CULT_MEMBERSHIP: "membership of a hidden cult",
        IntrigueSecret.DEBT: "a hidden debt",
        IntrigueSecret.CRIME: "a crime",
        IntrigueSecret.COWARDICE_IN_BATTLE: "cowardice in battle",
        IntrigueSecret.HIDDEN_CONDITION: "a hidden illness or madness",
        IntrigueSecret.FALSE_IDENTITY: "a false identity",
        IntrigueSecret.DEAL_WITH_OUTER_BEING: "a deal with an outer being",
        IntrigueSecret.TRUE_PARENTAGE: "their true parentage",
        IntrigueSecret.BROKEN_OATH: "a broken oath",
        IntrigueSecret.ECOSABOTAGE: "a sabotage of the land",
        IntrigueSecret.BROKEN_CIPHER: "a broken cipher",
        IntrigueSecret.TRUE_HISTORY: "the true history behind an official account",
        IntrigueSecret.HIDDEN_POWER: "a power they were born with and kept hidden",
        IntrigueSecret.FORGERY: "a forgery they made or used",
        IntrigueSecret.ILLNESS: "an illness they kept hidden",
    },
)
