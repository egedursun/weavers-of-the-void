from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

H = RuleGroup.HEROES_AND_MORTALS
D = RuleGroup.THE_DIVINE
P = RuleGroup.THE_GODS_POWER


@dataclass(frozen=True)
class HeroquestRules:
    chance_pct: int = rule(3, 0, 100, H, "Chance a mortal of high renown and faith with a fitting legend undertakes a heroquest each epoch (%)")
    per_epoch: int = rule(4, 0, 1000, H, "Heroquests begun each epoch at most")
    renown_min: int = rule(40, 0, 100, H, "Renown a mortal needs before it may undertake a heroquest")
    piety_min: int = rule(40, 0, 100, H, "Piety of its community a quester needs")
    steps_min: int = rule(3, 1, 20, H, "Fewest steps of a heroquest")
    steps_max: int = rule(5, 1, 20, H, "Most steps of a heroquest")
    step_pass: int = rule(50, 0, 200, H, "Score a quester must reach at each step")
    fidelity_bonus: int = rule(20, 0, 100, H, "Score a quester gains at a step by following its people's version of the myth")
    deviation_pct: int = rule(20, 0, 100, H, "Chance a quester who fails a step departs from the myth instead of falling")
    deviation_fidelity: int = rule(25, 0, 100, H, "Fidelity a departure from the myth costs")
    interference: int = rule(15, 0, 100, H, "Interference each servitor of a rival god or outer being in the realm adds")
    member_bonus: int = rule(5, 0, 100, H, "Score each companion of a group heroquest adds at every step")
    trap_pct: int = rule(30, 0, 100, H, "Chance a fallen quester's soul is trapped in the mythic realm (%)")
    break_pct: int = rule(20, 0, 100, H, "Chance a failed heroquest breaks its myth (%)")
    break_credence: int = rule(30, 0, 100, H, "Credence a broken myth loses")
    break_cohesion: int = rule(10, 0, 100, H, "Cohesion the quester's people lose when its myth breaks")
    injury_hp: int = rule(20, 0, 100, H, "Harm a quester who falls takes")
    death_pct: int = rule(10, 0, 100, H, "Chance a quester who falls and is neither trapped, nor breaks the myth, nor goes mad dies of it (%)")
    madness_pct: int = rule(30, 0, 100, H, "Chance a quester who falls and is neither trapped nor breaks the myth returns mad instead of injured (%)")
    party_pct: int = rule(30, 0, 100, H, "Chance a heroquest the engine begins is undertaken by a party (%)")
    party_max: int = rule(3, 0, 12, H, "Companions a party heroquest takes at most")
    rewrite_distortion: int = rule(20, 0, 100, H, "Distortion a returning quester's departure writes into the myth")
    boon_standing: int = rule(10, 0, 100, H, "Awe the quester's community gains for the god of the myth when the quest succeeds")
    boon_dominion: int = rule(10, 0, 100, H, "Dominion the god of the myth gains in the quester's land when the land is renewed")


@dataclass(frozen=True)
class MantlingRules:
    deed_window: int = rule(5, 1, 100, H, "Epochs back a mortal's deeds count toward walking a god's path")
    deeds_min: int = rule(6, 0, 1000, H, "Deeds in a god's domains a mortal needs to walk its path")
    renown_min: int = rule(70, 0, 100, H, "Renown a mortal needs to be a candidate god")
    worship_min: int = rule(2, 0, 1000, H, "Communities that worship the mortal before it may ascend")
    power_min: int = rule(6, 0, 100, H, "Power level a mortal needs to ascend")
    fate_pct: int = rule(30, 0, 100, H, "Chance Fate approves a mortal who meets every condition each epoch (%)")
    weak_existence_max: int = rule(25, 0, 100, H, "Existence below which a god may be replaced")
    weak_faith_share_max: int = rule(20, 0, 100, H, "Share of the pantheon's worshippers below which a god may be replaced (%)")
    weak_standing_max: int = rule(20, 0, 100, H, "Mean awe below which a god may be replaced")
    power_margin_pct: int = rule(10, 0, 200, H, "How much a mortal's might must exceed the weak god's for a replacement (%)")
    inherit_worship_pct: int = rule(50, 0, 100, H, "Share of the slain god's worshippers that follow the mortal who replaced it (%)")
    candidates_max: int = rule(400, 0, 100000, H, "Mortals the mantling step weighs each epoch at most")
    deed_value: int = rule(10, 1, 100, H, "Reputation in a skill of a god's domains that counts as one deed on its path")
    oppose_pct: int = rule(20, 0, 100, H, "Chance a god set on preventing a mantling blocks the mortal each epoch (%)")
    cult_pct: int = rule(25, 0, 100, H, "Chance a community that holds a mortal on a god's path in high regard begins to worship it each epoch (%)")
    cult_reputation: int = rule(60, 0, 100, H, "Reputation a mortal needs in a community before the community may worship it")
    sponsor_pct: int = rule(20, 0, 100, H, "Extra chance Fate approves a mortal whose mantling a god sponsors (%)")


@dataclass(frozen=True)
class ServitorRules:
    make_cost: int = rule(80, 0, 100000, P, "Essence a son spends to make a servitor")
    raise_pct: int = rule(10, 0, 100, D, "Chance the soul of a saint rises as a servitor of its god each epoch (%)")
    loyalty_drift: int = rule(4, 0, 100, D, "Loyalty a servitor moves each epoch toward its god's mean standing")
    fall_at: int = rule(20, 0, 100, D, "Loyalty below which a servitor may fall to another master")
    fall_pct: int = rule(25, 0, 100, D, "Chance a disloyal servitor falls each epoch (%)")
    guard_pct: int = rule(50, 0, 100, D, "Chance a guarding servitor turns back a desecrator of its post (%)")
    host_strength: int = rule(5, 0, 1000, D, "Strength a servitor of the host adds to its god in a divine war")
    herald_dream_pct: int = rule(5, 0, 100, D, "Extra chance each herald gives its god's dreams to win a mortal (%)")
    herald_max_pct: int = rule(20, 0, 100, D, "Most extra chance heralds give a god's dreams (%)")
    command_loyalty: int = rule(3, 0, 100, D, "Loyalty a servitor loses each time its god gives it a new role or post")
    defeat_loyalty: int = rule(8, 0, 100, D, "Loyalty each servitor of the host loses when its god is overcome in a divine battle")
    judge_veneration: int = rule(5, 0, 100, D, "Veneration a judging servitor's god wins among the dead it judges each epoch")
    agent_prosperity: int = rule(2, 0, 100, D, "Prosperity an agent servitor brings the town it is posted to each epoch")
    avenger_scorn: int = rule(25, 0, 100, D, "Love below which a community scorns a god and its avenging servitors bring it fear")
    avenger_fear: int = rule(4, 0, 100, D, "Fear an avenging servitor brings each scornful community of its god each epoch")
    worshipper_awe: int = rule(2, 0, 100, D, "Awe a worshipping servitor adds in each faithful community of its god each epoch")
    warden_order: int = rule(3, 0, 100, D, "Crime and unrest a warden servitor takes from the town it keeps each epoch")
    scribe_love: int = rule(1, 0, 100, D, "Love a scribe servitor keeps alive among peoples who tell accounts of its god each epoch")


@dataclass(frozen=True)
class GeasRules:
    birth_pct: int = rule(4, 0, 100, H, "Chance a newborn among a faithful people has a geas laid on it (%)")
    favour: int = rule(2, 0, 100, H, "Favour and awe a kept geas wins its layer each epoch")
    favour_dominion: int = rule(1, 0, 100, H, "Dominion a kept geas wins its god in the bearer's land each epoch")
    duty_epochs: int = rule(5, 1, 100, H, "Epochs within which a duty geas must be done again")
    trap_pct: int = rule(40, 0, 100, H, "Chance a geas trap forces its target to break the geas (%)")
    bind_pct: int = rule(50, 0, 100, H, "Chance a binding rite cast on a mortal lays a geas on it, witnessed by the caster's god (%)")


@dataclass(frozen=True)
class CosmicOfficeRules:
    income_pct: int = rule(20, 0, 200, P, "Extra essence an office holder draws from the domain activity of its office (%)")
    neglect_gain: int = rule(10, 0, 100, D, "Neglect an office gains each epoch it has no active holder")
    duty_gain: int = rule(10, 0, 100, D, "Duty an active holder fulfils each epoch")
    neglect_effect_pct: int = rule(50, 0, 200, D, "Strength of the world effects of an office at full neglect (%)")
    rite_access: int = rule(10, 0, 100, D, "Extra strength the rites of an office's forms gain in its holder's hands (%)")
    conquest_pct: int = rule(30, 0, 100, D, "Chance a god who overcomes an office holder in a divine battle takes one of its offices (%)")
    spirit_unrest: int = rule(10, 0, 100, D, "Unrest wandering spirits gain each epoch at full neglect of the office of the dead")
    route_danger: int = rule(5, 0, 100, D, "Danger the routes between worlds gain each epoch at full neglect of the office of the gates")
    beast_strength: int = rule(3, 0, 100, D, "Strength wild beasts gain each epoch at full neglect of the office of the hunt")
