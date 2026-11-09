from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

G = RuleGroup.THE_DIVINE


@dataclass(frozen=True)
class DomainRules:
    major_hook_pct: int = rule(20, 0, 200, G, "Strength a god's main domain hook gives its faithful (%)")
    minor_hook_pct: int = rule(10, 0, 200, G, "Strength a god's lesser domain hook gives its faithful (%)")
    synergy_pct: int = rule(15, 0, 200, G, "Strength a fitting pair of domains adds to their shared hook (%)")
    hook_cap_pct: int = rule(60, 0, 300, G, "Most any one hook can strengthen or ease a thing (%)")
    morale_points_pct: int = rule(50, 0, 300, G, "Morale points a percent of levy morale or frenzy is worth (%)")
    harvest_floor_per_pct: int = rule(3, 0, 20, G, "Share of a normal harvest each percent of the harvest floor guarantees")
    quality_points_pct: int = rule(50, 0, 300, G, "Quality points a percent of craft skill adds to works (%)")
    cold_share_pct: int = rule(150, 0, 500, G, "Share of the winter march slowdown a percent of cold endurance removes (%)")
    madness_below: int = rule(30, 0, 100, G, "Sanity below which a thing counts as mad for a god of madness")
    harvest_units_per_count: int = rule(200, 1, 100000, G, "Harvested units that count as one harvest for a god of harvest")
    activity_essence_max: int = rule(6, 0, 100, G, "Most essence a domain's activity gives a god in an epoch")
    activity_half: int = rule(5, 1, 10000, G, "Domain activity at which a god earns half the most essence")
    foreign_power_pct: int = rule(20, 0, 200, G, "Share of domain essence a foreign god takes as power (%)")


@dataclass(frozen=True)
class SonGoalRules:
    choose_chance: int = rule(40, 0, 100, G, "Chance a god without an aim takes a new one each epoch (%)")
    max_epochs: int = rule(12, 1, 200, G, "Epochs after which an engine-chosen aim fails")
    done_xp: int = rule(60, 0, 10000, G, "Experience a son gains on reaching an aim")
    done_fame: int = rule(20, 0, 10000, G, "Fame a son gains on reaching an aim")
    foreign_power: int = rule(5, 0, 100, G, "Power a foreign god gains on reaching an aim")
    foreign_ambition: int = rule(50, 0, 100, G, "Ambition a foreign god is weighed with when it chooses an aim")
    worship_gain: int = rule(3, 1, 1000, G, "More worshippers a god aims for than it has")
    spread_amount: int = rule(3, 1, 1000, G, "Faithful places a god aims to spread its domain to")
    base_weight: int = rule(10, 1, 1000, G, "Weight of an ordinary aim in a god's choice")
    rival_weight_pct: int = rule(30, 0, 500, G, "Weight per point of ambition over mercy of aiming to destroy a rival (%)")
    scan_limit: int = rule(5, 1, 100, G, "Faithful places a god looks at for wars worth winning")
    reconcile_loyalty: int = rule(70, 0, 100, G, "Loyalty at which a son has reconciled with the Creator")
    rebel_loyalty: int = rule(30, 0, 100, G, "Loyalty below which a son may aim to rebel")
    attention_drift_chance: int = rule(40, 0, 100, G, "Chance a son's attention drifts to the world of its aim each epoch (%)")
    manual_attention_epochs: int = rule(3, 0, 100, G, "Epochs a son stays where the Creator placed it before its aims draw it away")


@dataclass(frozen=True)
class DivineStandingRules:
    act_awe: int = rule(6, 0, 100, G, "Awe a god's act on a people adds")
    presence_awe: int = rule(2, 0, 100, G, "Awe a god's presence in a people's world adds each epoch")
    answer_love: int = rule(8, 0, 100, G, "Love an answered prayer adds")
    kind_love: int = rule(6, 0, 100, G, "Love a kind act of a god adds")
    stern_fear: int = rule(8, 0, 100, G, "Fear a stern act of a god adds")
    unanswered_neglect: int = rule(5, 0, 100, G, "Neglect an unanswered prayer adds")
    absence_neglect: int = rule(3, 0, 100, G, "Neglect a god's absence from a people's world adds each epoch")
    answer_relief: int = rule(4, 0, 100, G, "Neglect an answered prayer takes away")
    decay_pct: int = rule(10, 0, 100, G, "Share of each standing that fades each epoch (%)")
    neglect_conversion_pct: int = rule(100, 0, 500, G, "How much a people's neglect speeds its turning to another god (%)")
    neglect_existence_pct: int = rule(20, 0, 100, G, "Existence a son loses per hundred points of mean neglect")
    creator_turn_pct: int = rule(20, 0, 100, G, "Chance per hundred points of love over fear that an estranged people turns to the Creator")


@dataclass(frozen=True)
class DivineWoundRules:
    wound_chance: int = rule(25, 0, 100, G, "Chance a god beaten in a duel or a war of gods takes a divine wound (%)")
    chance_per_margin: float = rule(0.5, 0, 10, G, "Further chance of a divine wound per point of the winning margin (%)")
    severed_weight: int = rule(30, 0, 100, G, "Weight of a severed domain among divine wounds")
    shattered_weight: int = rule(40, 0, 100, G, "Weight of a shattered manifestation among divine wounds")
    name_weight: int = rule(30, 0, 100, G, "Weight of a stolen true name among divine wounds")
    base_severity: int = rule(40, 1, 100, G, "Severity of a divine wound at no margin")
    severity_per_margin: int = rule(2, 0, 20, G, "Further severity per point of the winning margin")
    faith_per_heal: int = rule(10, 1, 10000, G, "Faith that heals one point of a divine wound each epoch")
    rite_heal: int = rule(3, 0, 100, G, "Healing each successful rite of a god's faithful gives its wounds")
    base_heal: int = rule(2, 0, 100, G, "Healing a divine wound takes each epoch on its own")
    avatar_severity: int = rule(50, 1, 100, G, "Severity of the wound a god takes when its avatar is killed")
    void_floor_pct: int = rule(60, 0, 100, G, "Share of a wound of the void's severity that lowers the god's highest sanity (%)")
    name_exposure_pct: int = rule(40, 0, 100, G, "Share of a stolen name's severity a god loses from its strength in duels and wars (%)")


@dataclass(frozen=True)
class AvatarRules:
    essence_cost: int = rule(30, 0, 10000, G, "Essence a son spends to take a mortal form")
    max_per_god: int = rule(1, 1, 10, G, "Most mortal forms one god walks in at once")
    hp: int = rule(80, 1, 1000, G, "Health of a god's mortal form")
    age: int = rule(30, 0, 1000, G, "Apparent age of a god's mortal form")
    lifespan: int = rule(300, 1, 100000, G, "Lifespan of a god's mortal form")
    presence_awe: int = rule(6, 0, 100, G, "Awe a god's mortal form adds to the people it walks among each epoch")
    presence_love: int = rule(4, 0, 100, G, "Love a god's mortal form adds to the people it walks among each epoch")
    preach_chance: int = rule(15, 0, 100, G, "Chance a god's mortal form wins its people over to the god each epoch (%)")
    inheritance_deviation: int = rule(8, 0, 50, G, "Most a son's child's stats stray from the mean of its parents")


@dataclass(frozen=True)
class GodRelationRules:
    theft_memory: int = rule(25, 0, 100, G, "Grudge a god keeps against one who took its faithful")
    aid_memory: int = rule(15, 0, 100, G, "Gratitude a god keeps toward one who aided its chosen")
    son_relation_pct: int = rule(50, 0, 200, G, "Share of such a memory that moves the relation between sons (%)")
    shared_domain: int = rule(4, 0, 100, G, "Friendship a foreign god loses each epoch toward a god of a shared domain")
    stance_pct: int = rule(10, 0, 100, G, "Share of a foreign god's stance toward the pantheon that moves its friendship with each son (%)")
    common_cause: int = rule(4, 0, 100, G, "Friendship foreign gods hostile to the pantheon gain toward each other each epoch")
    neighbour: int = rule(2, 0, 100, G, "Further friendship or enmity between gods of the same world each epoch")
    league_stance: int = rule(40, 0, 100, G, "Hostility to the pantheon at which a foreign god joins a league against it")
    league_friendship: int = rule(30, 0, 100, G, "Friendship two hostile foreign gods need to league together")
    league_share_pct: int = rule(50, 0, 200, G, "Share of an ally's strength that joins a god's war (%)")
    pact_friendship: int = rule(40, 0, 100, G, "Friendship a foreign god needs toward a son to seal a divine pact")
    pact_epochs: int = rule(10, 1, 200, G, "Epochs a divine pact holds")
    pact_stance: int = rule(10, 0, 100, G, "Stance toward the pantheon a foreign god gains on sealing a pact")
    pact_cap: int = rule(2, 0, 100, G, "Most divine pacts sealed in an epoch")


@dataclass(frozen=True)
class NaturalLawRules:
    start_strength: int = rule(60, 1, 100, G, "Strength of a new natural law")
    start_stability: int = rule(80, 1, 100, G, "Stability of a new natural law")
    upkeep_essence: int = rule(2, 0, 1000, G, "Essence a law's author pays each epoch at full strength to keep it")
    author_existence_floor: int = rule(20, 0, 100, G, "Existence (or power) below which an author cannot keep its laws")
    stability_decay: int = rule(10, 0, 100, G, "Stability a law loses each epoch its author cannot keep it")
    strength_decay: int = rule(15, 0, 100, G, "Strength a law with no stability loses each epoch")
    contest_erosion: int = rule(10, 0, 100, G, "Stability the weaker of two contradicting laws loses each epoch")
    stalemate_margin: int = rule(10, 0, 100, G, "Strength gap within which two contradicting laws hold each other off")
    clash_leak: int = rule(3, 0, 100, G, "Leakage two deadlocked laws tear in their world each epoch")
    blood_per_power: int = rule(4, 0, 100, G, "Blood a rite costs per point of power where magic requires blood")
    night_harvest_pct: int = rule(40, 0, 100, G, "Share of a harvest that ripens under eternal night (%)")
    reversed_harvest_pct: int = rule(80, 0, 100, G, "Share of a harvest that ripens when the seasons run backwards (%)")
    heavy_march_pct: int = rule(70, 0, 100, G, "Share of a march an army makes where weight has shifted (%)")
    heavy_build_pct: int = rule(70, 0, 100, G, "Share of the building work done where weight has shifted (%)")
    real_dream_pct: int = rule(200, 100, 1000, G, "How much more often mortals dream where dreams are real (%)")
    rust_wear_pct: int = rule(300, 100, 1000, G, "How much faster metal wears where it rusts fast (%)")


@dataclass(frozen=True)
class OuterBeingRules:
    size_per_region: int = rule(25, 1, 100, G, "Size of an outer being for each further land it reaches")
    bite_per_interest: int = rule(5, 0, 100, G, "What an outer being consumes each epoch per hundred points of interest")
    memory_bite: int = rule(5, 0, 100, G, "Credence a legend loses to an outer being that feeds on memories")
    influence_per_meal: int = rule(1, 0, 100, G, "Influence an outer being gains each epoch it feeds")
    breach_strength: int = rule(30, 1, 100, G, "Strength of a new breach point")
    breach_leak_pct: int = rule(5, 0, 100, G, "Leakage a breach point tears in its world each epoch per hundred points of strength (%)")
    breach_sanity_pct: int = rule(10, 0, 100, G, "Sanity lost each epoch in a land with a breach point per hundred points of strength (%)")
    communion_sanity: int = rule(3, 0, 100, G, "Sanity an outer cult of void communion and its home lose each epoch")
    communion_leak: int = rule(1, 0, 100, G, "Leakage void communion tears in its world each epoch")
    followers_per_offering: int = rule(50, 1, 100000, G, "Followers of an outer cult for each offering that feeds its being")
    whisper_progress: int = rule(10, 0, 100, G, "Progress toward forbidden knowledge whispered secrets give a cult's home each epoch")
    price_severity: int = rule(60, 1, 100, G, "Severity of the wound a son takes when it pays an outer bargain with a domain or its name")
    price_sanity: int = rule(15, 0, 100, G, "Sanity a world's peoples lose when a son pays an outer bargain with it")
    might_gain: int = rule(5, 0, 100, G, "Might a son gains from an outer bargain for might")
    oppose_cost_pct: int = rule(60, 0, 1000, G, "Essence per hundred points of size it costs to ward against an outer being (%)")
    oppose_sanity: int = rule(5, 0, 100, G, "Sanity a son loses warding against an outer being")
    ward_interest: int = rule(20, 0, 100, G, "Interest an outer being loses when a son wards against it")
    ward_breach: int = rule(15, 0, 100, G, "Strength each breach point of an outer being loses when a son wards against it")
