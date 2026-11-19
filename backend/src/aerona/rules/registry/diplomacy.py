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
        "Base of the most spontaneous hostility declarations per epoch, shared by every path (grudge, wonder envy, espionage, tribute, betrayal, independence, rivalry, schism, invasion), grown by the number of communities; uprisings are separate",
    )
    cap_community_divisor: int = rule(
        5,
        0,
        1000,
        RuleGroup.WAR_AND_DIPLOMACY,
        "Communities per extra unit of every per-epoch diplomacy cap and of the world war cap (0: the caps stay at their base)",
    )
    peace_cap: int = rule(
        3, 0, 200, RuleGroup.WAR_AND_DIPLOMACY, "Base of the most neighbour peaces per epoch (by oath or truce), grown by the number of communities"
    )
    exhaustion_peace_cap: int = rule(
        3,
        0,
        200,
        RuleGroup.WAR_AND_DIPLOMACY,
        "Base of the most exhaustion peaces per epoch (long wars; counted separately from neighbour peace), grown by the number of communities",
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
    grudge_fade_cap: int = rule(6, 0, 1000, RuleGroup.WAR_AND_DIPLOMACY, "Base of the most fading grudges per epoch, grown by the number of communities")
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
    alliance_cap: int = rule(2, 0, 200, RuleGroup.WAR_AND_DIPLOMACY, "Base of the most alliances per epoch, grown by the number of communities")
    community_war_cap: int = rule(3, 0, 50, RuleGroup.WAR_AND_DIPLOMACY, "Maximum simultaneous ongoing wars of one community (war event)")
    world_war_cap: int = rule(
        6,
        0,
        1000,
        RuleGroup.WAR_AND_DIPLOMACY,
        "Base of the most simultaneous ongoing community wars in the world, grown by the number of communities (war event; hostility links fade separately)",
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
    neighbor_hops: int = rule(
        1, 0, 20, RuleGroup.WAR_AND_DIPLOMACY, "Maximum map hop distance between top regions at which two communities count as neighbours"
    )
    cap_close_idle_epochs: int = rule(
        2, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "A war closed by the war caps is described as idle when its last clash is at least this many epochs old"
    )
    blood_feud: int = rule(30, 0, 200, RuleGroup.WAR_AND_DIPLOMACY, "Relation reduced by a blood feud (points)")
    exhaustion_peace_relation: int = rule(15, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Relation bonus of an exhaustion peace (points)")
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
    betrayal_cap: int = rule(1, 0, 200, RuleGroup.WAR_AND_DIPLOMACY, "Base of the most betrayals per epoch, grown by the number of communities")
    traitor_default_strength: int = rule(40, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Strength assumed in a betrayal for a party with unknown sway or strength")
    betrayal_war_collapse_chance: int = rule(40, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "A war the betrayed ally is fighting collapses into defeat (%)")
    betrayal_relation: int = rule(30, 0, 200, RuleGroup.WAR_AND_DIPLOMACY, "Relation reduced by betrayal (points)")
    alliance_lifetime: int = rule(
        8, 0, 1000, RuleGroup.WAR_AND_DIPLOMACY, "An alliance whose oath is not renewed for this many epochs may lapse (0: alliances are permanent)"
    )
    alliance_end_chance: int = rule(
        15, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Chance per epoch an alliance past its lifetime ends (%; allies with a common enemy renew the oath)"
    )
    alliance_end_cap: int = rule(
        4, 0, 1000, RuleGroup.WAR_AND_DIPLOMACY, "Base of the most alliances lapsing on their own per epoch, grown by the number of communities"
    )
    coalition_threshold: int = rule(
        50, 0, 100, RuleGroup.WAR_AND_DIPLOMACY, "Threat a realm's neighbours must feel before they band into a coalition against it"
    )
