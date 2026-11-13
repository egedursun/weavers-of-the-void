from dataclasses import dataclass

from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.intrigue import BeliefSource, FavourOrigin, HookDemand, HookSource, IdentityReason, IntrigueSecret, PlotKind, SchemePhase
from aerona.domain.enums.mind import ActKind


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
}
HOOK_DEMAND_LABELS: dict[HookDemand, str] = {
    HookDemand.MARRIAGE: "Agree to a marriage",
    HookDemand.STEP_DOWN: "Step down",
    HookDemand.SUPPORT: "Lend support",
    HookDemand.VOTE: "Vote as told on the laws under debate",
    HookDemand.LAW: "Back the holder's laws with the weight of rule",
}
FAVOUR_LABELS: dict[FavourOrigin, str] = {
    FavourOrigin.GIFT: "A gift",
    FavourOrigin.RESCUE: "A rescue",
    FavourOrigin.WAR_SUPPORT: "Support in a war",
    FavourOrigin.SUCCESSION_SUPPORT: "Support in a succession",
    FavourOrigin.SCHEME_AID: "Aid in a scheme",
    FavourOrigin.VOTE: "A vote that carried a law",
    FavourOrigin.RELIEF: "Aid in a stricken hour",
}
IDENTITY_LABELS: dict[IdentityReason, str] = {
    IdentityReason.SPY: "A spy's cover",
    IdentityReason.BLOOD_CURSE: "A blood-cursed one's mask",
    IdentityReason.EXILE: "An exile's new name",
    IdentityReason.IMPOSTOR: "An impostor's guise",
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
BELIEF_SOURCE_LABELS: dict[BeliefSource, str] = {
    BeliefSource.OBSERVATION: "Seen with their own eyes",
    BeliefSource.MESSAGE: "Told in a message",
    BeliefSource.RUMOUR: "Heard as rumour",
    BeliefSource.SPY: "Reported by spies",
    BeliefSource.SCOUT: "Reported by scouts",
    BeliefSource.RECORDS: "Read in records",
    BeliefSource.DECEPTION: "Planted by a deceiver",
}
PRICE_PREFIX = "price."


def belief_label(attribute: str) -> str:
    if attribute.startswith(PRICE_PREFIX):
        return f"Price of {attribute.removeprefix(PRICE_PREFIX).replace('_', ' ')}"
    return BELIEF_ATTRIBUTE_LABELS.get(attribute, attribute.replace("_", " ").capitalize())


BELIEF_CHOICES: dict[str, str] = {
    **{key: label for key, label in BELIEF_ATTRIBUTE_LABELS.items()},
    **{f"{PRICE_PREFIX}{commodity.value}": belief_label(f"{PRICE_PREFIX}{commodity.value}") for commodity in CommodityKind},
}
