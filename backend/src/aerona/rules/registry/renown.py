from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

G = RuleGroup.REPUTATION


@dataclass(frozen=True)
class LocalRenownRules:
    act_magnitude: int = rule(12, 0, 100, G, "Reputation a witnessed act moves where it is seen, before the community's ethics weigh it")
    contest_magnitude: int = rule(10, 0, 100, G, "Reputation a contest of wit wins where it is held")
    masterwork_magnitude: int = rule(12, 0, 100, G, "Renown for a skill a masterwork wins where it is made")
    brawl_magnitude: int = rule(4, 0, 100, G, "Troublemaking a brawl earns where it happens")
    hearsay_pct: int = rule(60, 0, 100, G, "Share of a deed's reputation a community gains when the rumour reaches it, before fidelity (%)")
    fade: int = rule(2, 0, 20, G, "Reputation that fades each epoch where nothing renews it")
    account_slow_pct: int = rule(50, 0, 100, G, "Share of the fading of a reputation that an account told of its subject holds back (%)")
    aggregate_pct: int = rule(100, 0, 400, G, "How strongly local reputations raise global renown and infamy (%)")
    opinion_pct: int = rule(30, 0, 200, G, "How much a community's view of a subject's glory and infamy feeds its opinion (%)")


@dataclass(frozen=True)
class CurrencyRules:
    prestige_pct: int = rule(100, 0, 400, G, "How strongly renown among one's own realm sets prestige (%)")
    piety_pct: int = rule(100, 0, 400, G, "How strongly standing with the realm's faith sets piety (%)")
    dread_execution: int = rule(8, 0, 100, G, "Dread an execution, maiming or torture by a ruler adds")
    dread_victory: int = rule(6, 0, 100, G, "Dread a victory in battle adds to the victor's ruler")
    dread_fade: int = rule(3, 0, 50, G, "Dread that fades each epoch")
    tyranny_act: int = rule(6, 0, 100, G, "Tyranny an act the realm's own people condemn adds to its ruler")
    tyranny_fade: int = rule(1, 0, 50, G, "Tyranny that fades each epoch")
    prestige_fade: int = rule(1, 0, 50, G, "Prestige that fades each epoch a ruler wins no new renown")
    amends_pct: int = rule(50, 0, 400, G, "How much faster tyranny fades for each act of mercy or restitution of the epoch (%)")
    dread_suppress_pct: int = rule(60, 0, 100, G, "How much full dread suppresses faction challenges (%)")
    tyranny_pressure_pct: int = rule(60, 0, 400, G, "How much full tyranny raises faction pressure (%)")
    opinion_pct: int = rule(30, 0, 200, G, "How much dread and tyranny lower the opinion of the ruled (%)")
    law_cost: int = rule(15, 0, 100, G, "Prestige a ruler spends to win acceptance of a law")
    law_bonus_pct: int = rule(60, 0, 400, G, "How much spent prestige raises the chance a law is accepted (%)")
    clergy_cost: int = rule(15, 0, 100, G, "Piety a ruler spends to win the clergy's support")
    clergy_loyalty: int = rule(15, 0, 100, G, "Loyalty a priesthood gains when its ruler spends piety")
    clergy_below: int = rule(40, 0, 100, G, "Loyalty under which a ruler spends piety on the clergy")
    silence_cost: int = rule(25, 0, 100, G, "Dread a ruler spends to silence dissent")
    silence_epochs: int = rule(3, 1, 20, G, "Epochs spent dread silences dissent")
    silence_pressure: int = rule(2, 1, 20, G, "Hostile factions in a realm at which its ruler spends dread to silence them")


@dataclass(frozen=True)
class LoreTradeRules:
    trade_pct: int = rule(20, 0, 100, G, "Chance each epoch a seeker of lore trades for a piece it wants from a neighbour (%)")
    base_value: int = rule(40, 0, 100, G, "Value of a piece of lore wanted by its seeker that no one else holds")
    wealth_per_value: int = rule(10, 1, 100, G, "Value that buys one unit of wealth")
    favour_friendship: int = rule(10, 0, 100, G, "Friendship a mortal gains toward one who tells them a wanted secret, at full value")
    renown_per_value: int = rule(10, 1, 100, G, "Value that wins one point of wisdom where the lore is given")
    confide_pct: int = rule(30, 0, 100, G, "Chance a confidence between mortals passes on a technique their place keeps secret (%)")


@dataclass(frozen=True)
class ClaimRules:
    claim_pct: int = rule(15, 0, 100, G, "Chance a vain and deceitful mortal who shares a place claims another's great deed (%)")
    claim_at: int = rule(20, 0, 100, G, "Size of a deed worth claiming falsely")
    vanity_pct: int = rule(100, 0, 400, G, "How strongly vanity and deceit drive a false claim (%)")
    shared_pct: int = rule(50, 0, 100, G, "Share of a deed's reputation each comrade in a shared deed gains (%)")
    verify_pct: int = rule(10, 0, 100, G, "Chance each epoch a false claim is tested, before witnesses and tokens (%)")
    witness_pct: int = rule(10, 0, 100, G, "How much each witnessing community raises the chance a false claim is tested (%)")
    token_pct: int = rule(40, 0, 100, G, "How much a token held by the true doer raises the chance a false claim is tested (%)")
    exposure_shame: int = rule(15, 0, 100, G, "Trickery an exposed false claimant earns everywhere their claim was believed")
    punish_pct: int = rule(50, 0, 100, G, "Chance an exposed impostor is punished as the law punishes theft (%)")
    exposure_memory: int = rule(-50, -100, 0, G, "Memory the true doer keeps of an exposed impostor")
