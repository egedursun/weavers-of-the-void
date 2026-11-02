from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class DiplomacyRules:
    grudge_threshold: int = rule(-60, -100, 0, RuleGroup.WAR_AND_DIPLOMACY, "Neighbours below this relation may declare war")
    peace_threshold: int = rule(-15, -100, 100, RuleGroup.WAR_AND_DIPLOMACY, "Enemies above this relation may make peace")
    alliance_threshold: int = rule(55, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Neighbours above this relation may become allies")
    declarations_cap: int = rule(
        3,
        0,
        20,
        RuleGroup.WAR_AND_DIPLOMACY,
        "Maximum spontaneous hostility declarations per epoch, shared by every path (grudge, wonder envy, espionage, tribute, betrayal, independence, rivalry, schism, invasion); uprisings are separate",
    )
    peace_cap: int = rule(3, 0, 20, RuleGroup.WAR_AND_DIPLOMACY, "Maximum neighbour peaces per epoch (by oath or truce)")
    exhaustion_peace_cap: int = rule(
        3, 0, 20, RuleGroup.WAR_AND_DIPLOMACY, "Maximum exhaustion peaces per epoch (long wars; counted separately from neighbour peace)"
    )
    grudge_fade_relation: int = rule(
        0,
        -100,
        100,
        RuleGroup.WAR_AND_DIPLOMACY,
        "Fading grudge: community hostility closes when relation has risen to this or above and there is no ongoing war",
    )
    grudge_fade_min_age: int = rule(3, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Fading grudge: minimum age of the hostility (epochs)")
    grudge_forget_epochs: int = rule(
        12,
        0,
        1000,
        RuleGroup.WAR_AND_DIPLOMACY,
        "Forgotten grudge: hostility lasting this many epochs without ever clashing (no ongoing war) closes even if the relation is bad (0: off)",
    )
    grudge_fade_cap: int = rule(6, 0, 1000, RuleGroup.WAR_AND_DIPLOMACY, "Maximum fading grudges per epoch")
    grudge_pool_pct: int = rule(
        300,
        100,
        10000,
        RuleGroup.WAR_AND_DIPLOMACY,
        "Grudge pool: when community hostilities (pair count) exceed this percentage of the world's war cap, old grudges lock diplomacy; the excess enlarges the fading-grudge cap",
    )
    grudge_overflow_share_pct: int = rule(
        25, 0, 1000, RuleGroup.WAR_AND_DIPLOMACY, "Share of hostility pairs exceeding the grudge pool added to the per-epoch fading-grudge cap (%)"
    )
    truce_without_war: int = rule(
        0,
        0,
        1,
        RuleGroup.WAR_AND_DIPLOMACY,
        "When the hostility of two communities that never fought closes (grudge faded, forgotten, peace), is a truce recorded (1: yes, 0: no; pairs that fought always enter a truce)",
    )
    mortal_grudge_forget_epochs: int = rule(
        8,
        0,
        1000,
        RuleGroup.WAR_AND_DIPLOMACY,
        "A mortal's hostility (with a mortal or a community): hostility lasting this many epochs without any new encounter is forgotten (0: off)",
    )
    alliance_cap: int = rule(2, 0, 20, RuleGroup.WAR_AND_DIPLOMACY, "Maximum alliances per epoch")
    community_war_cap: int = rule(2, 0, 10, RuleGroup.WAR_AND_DIPLOMACY, "Maximum simultaneous ongoing wars of one community (war event)")
    world_war_cap: int = rule(
        6, 0, 50, RuleGroup.WAR_AND_DIPLOMACY, "Maximum simultaneous ongoing community wars in the world (war event; hostility links fade separately)"
    )
    truce_epochs: int = rule(3, 0, 20, RuleGroup.WAR_AND_DIPLOMACY, "Truce duration after peace (epochs)")
    exhaustion_start_epoch: int = rule(3, 1, 30, RuleGroup.WAR_AND_DIPLOMACY, "Epoch of a long war at which exhaustion peace begins")
    exhaustion_growth_pct: int = rule(10, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Per-epoch increase of the exhaustion-peace chance (%)")
    exhaustion_cap_pct: int = rule(50, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Cap of the exhaustion-peace chance (%)")
    war_declaration_chance: int = rule(25, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "A grudge turns into a war declaration (%)")
    peace_chance: int = rule(30, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "A softening relation turns into peace (%)")
    alliance_chance: int = rule(20, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Friendly neighbours become allies (%)")
    marriage_alliance_share_pct: int = rule(40, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Share of alliances made through marriage (%)")
    betrayal_chance: int = rule(30, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Betrayal in a breaking alliance (%)")
    betrayal_war_chance: int = rule(50, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Betrayal turns into war (%)")
    relation_history_len: int = rule(12, 1, 500, RuleGroup.CHRONICLE, "Number of recent events kept in a community relation")
    relation_decay_threshold: int = rule(
        50, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Community relation mean reversion: relation beyond this value (\u00b1) fades every epoch"
    )
    relation_decay_pct: int = rule(
        25, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Mean reversion: share of the difference beyond the threshold that fades per epoch (%; 0 disables)"
    )
    neighbor_hops: int = rule(
        1, 0, 20, RuleGroup.WAR_AND_DIPLOMACY, "Maximum map hop distance between top regions at which two communities count as neighbours"
    )
    cap_close_idle_epochs: int = rule(
        2, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "A war closed by the war caps is described as idle when its last clash is at least this many epochs old"
    )
    relation_list_history: int = rule(3, 0, 50, RuleGroup.WAR_AND_DIPLOMACY, "Recent relation events shown per listed community relation")
    initial_shared_god: int = rule(20, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Initial relation: bonus for worshipping the same god (points)")
    initial_different_god: int = rule(5, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Initial relation: penalty for worshipping different gods (points)")
    initial_shared_language: int = rule(15, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Initial relation: bonus for speaking the same language (points)")
    initial_enemy: int = rule(50, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Initial relation: hostility penalty (points)")
    initial_ally: int = rule(45, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Initial relation: alliance bonus (points)")
    initial_trade: int = rule(20, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Initial relation: trade bonus (points)")
    initial_tribute: int = rule(15, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Initial relation: tribute penalty (points)")
    blood_feud: int = rule(30, 0, 200, RuleGroup.WAR_AND_DIPLOMACY, "Relation reduced by a blood feud (points)")
    exhaustion_peace_relation: int = rule(15, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Relation bonus of an exhaustion peace (points)")
    drift_shared_god: int = rule(2, 0, 50, RuleGroup.WAR_AND_DIPLOMACY, "Per-epoch drift: shared-god bonus (points)")
    drift_cult_other_god: int = rule(2, 0, 50, RuleGroup.WAR_AND_DIPLOMACY, "Per-epoch drift: penalty for a cult of a different god (points)")
    drift_shared_language: int = rule(1, 0, 50, RuleGroup.WAR_AND_DIPLOMACY, "Per-epoch drift: shared-language bonus (points)")
    drift_trade: int = rule(3, 0, 50, RuleGroup.WAR_AND_DIPLOMACY, "Per-epoch drift: trade bonus (points)")
    drift_ally: int = rule(2, 0, 50, RuleGroup.WAR_AND_DIPLOMACY, "Per-epoch drift: alliance bonus (points)")
    drift_enemy: int = rule(3, 0, 50, RuleGroup.WAR_AND_DIPLOMACY, "Per-epoch drift: hostility penalty (points)")
    drift_tribute: int = rule(2, 0, 50, RuleGroup.WAR_AND_DIPLOMACY, "Per-epoch drift: tribute penalty (points)")
    drift_blood_feud: int = rule(3, 0, 50, RuleGroup.WAR_AND_DIPLOMACY, "Per-epoch drift: blood-feud penalty (points)")
    neighbor_exhaustion_start: int = rule(
        2, 0, 50, RuleGroup.WAR_AND_DIPLOMACY, "War duration at which exhaustion peace begins between neighbouring enemies (epochs)"
    )
    neighbor_exhaustion_growth_pct: int = rule(
        12, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Per-epoch increase of the exhaustion-peace chance between neighbouring enemies (%)"
    )
    neighbor_exhaustion_cap_pct: int = rule(60, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Cap of the exhaustion-peace chance between neighbouring enemies (%)")
    peace_relation: int = rule(10, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Relation bonus of peace (points)")
    marriage_min_age: int = rule(16, 0, 200, RuleGroup.HEROES_AND_MORTALS, "Minimum age of a hero who can enter a marriage alliance (years)")
    default_hero_age: int = rule(30, 0, 200, RuleGroup.HEROES_AND_MORTALS, "Age assumed for a hero with unknown age (years)")
    marriage_relation: int = rule(10, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Relation bonus of a marriage alliance (points)")
    betrayal_cap: int = rule(1, 0, 20, RuleGroup.WAR_AND_DIPLOMACY, "Maximum betrayals per epoch")
    traitor_default_strength: int = rule(40, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Strength assumed in a betrayal for a party with unknown sway or strength")
    betrayal_relation: int = rule(30, 0, 200, RuleGroup.WAR_AND_DIPLOMACY, "Relation reduced by betrayal (points)")
    alliance_lifetime: int = rule(
        8, 0, 1000, RuleGroup.WAR_AND_DIPLOMACY, "An alliance whose oath is not renewed for this many epochs may lapse (0: alliances are permanent)"
    )
    alliance_end_chance: int = rule(
        15, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Chance per epoch an alliance past its lifetime ends (%; allies with a common enemy renew the oath)"
    )
    alliance_end_cap: int = rule(4, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Most alliances lapsing on their own per epoch")
