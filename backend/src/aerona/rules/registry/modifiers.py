from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class ModifiersRules:
    decayed_add_drop_below: float = rule(0.5, 0, 100, RuleGroup.INTERCONNECTION, "An additive modifier is removed once decay shrinks it below this size")
    decayed_multiplier_drop_within_pct: int = rule(
        1, 0, 100, RuleGroup.INTERCONNECTION, "A multiplying modifier is removed once decay brings it this close to no effect (%)"
    )
    wonder_prosperity: int = rule(6, 0, 100, RuleGroup.INTERCONNECTION, "Prosperity a standing wonder adds to the community that holds it")
    wonder_piety: int = rule(4, 0, 100, RuleGroup.INTERCONNECTION, "Piety a standing wonder adds to the community that holds it")
    illness_strength_pct: int = rule(85, 0, 100, RuleGroup.INTERCONNECTION, "Strength and agility a lingering illness leaves (%)")
    withered_strength_pct: int = rule(80, 0, 100, RuleGroup.INTERCONNECTION, "Strength a withered limb leaves (%)")
    melancholy_intellect: int = rule(8, 0, 100, RuleGroup.INTERCONNECTION, "Intellect melancholy takes away")
    rage_strength: int = rule(6, 0, 100, RuleGroup.INTERCONNECTION, "Strength fits of rage lend")
    rage_intellect: int = rule(8, 0, 100, RuleGroup.INTERCONNECTION, "Intellect fits of rage take away")
    paranoia_charisma: int = rule(10, 0, 100, RuleGroup.INTERCONNECTION, "Charisma paranoia takes away")
    hunger_charisma: int = rule(10, 0, 100, RuleGroup.INTERCONNECTION, "Charisma an endless hunger takes away")
    void_taint_charisma: int = rule(15, 0, 100, RuleGroup.INTERCONNECTION, "Charisma the taint of the void takes away")
    chosen_charisma: int = rule(12, 0, 100, RuleGroup.INTERCONNECTION, "Charisma the mark of the chosen lends")
    brand_charisma: int = rule(6, 0, 100, RuleGroup.INTERCONNECTION, "Charisma a god's brand lends")
    nightmares_willpower: int = rule(6, 0, 100, RuleGroup.INTERCONNECTION, "Willpower recurring nightmares wear away")
    law_standing_army_defense: int = rule(8, 0, 100, RuleGroup.INTERCONNECTION, "Defence a fully enforced standing-army law lends each community under it")
    law_serfdom_prosperity: int = rule(5, 0, 100, RuleGroup.INTERCONNECTION, "Prosperity a fully enforced serfdom law takes from each community under it")
    law_serfdom_wealth: int = rule(4, 0, 100, RuleGroup.INTERCONNECTION, "Wealth a fully enforced serfdom law gathers for each community under it")
    law_tolls_wealth: int = rule(4, 0, 100, RuleGroup.INTERCONNECTION, "Wealth fully enforced tolls bring each community under them")
    law_land_tenure_prosperity: int = rule(3, 0, 100, RuleGroup.INTERCONNECTION, "Prosperity a fully enforced land-tenure law lends each community under it")
    tradition_effect_pct: int = rule(100, 0, 500, RuleGroup.INTERCONNECTION, "How strongly a tradition's listed effects reach the communities that keep it (%)")
    artwork_prosperity: int = rule(5, 0, 100, RuleGroup.INTERCONNECTION, "Prosperity a renowned artwork (renown 100) brings the community that holds it")
    doctrine_proselytism_influence: int = rule(6, 0, 100, RuleGroup.INTERCONNECTION, "Influence a proselytising faith gains")
    doctrine_exclusivity_zeal: int = rule(6, 0, 100, RuleGroup.INTERCONNECTION, "Zeal an exclusive faith gains")
    doctrine_exclusivity_influence_pct: int = rule(90, 0, 200, RuleGroup.INTERCONNECTION, "Influence an exclusive faith keeps (%)")
    doctrine_syncretic_influence: int = rule(5, 0, 100, RuleGroup.INTERCONNECTION, "Influence a syncretic, open faith gains")
    doctrine_syncretic_zeal: int = rule(4, 0, 100, RuleGroup.INTERCONNECTION, "Zeal a syncretic, open faith gives up")
    doctrine_holy_war_zeal: int = rule(5, 0, 100, RuleGroup.INTERCONNECTION, "Zeal a faith preaching holy war gains")
    doctrine_celibate_zeal: int = rule(3, 0, 100, RuleGroup.INTERCONNECTION, "Zeal a faith with a celibate clergy gains")
    doctrine_fanaticism_zeal: int = rule(8, 0, 100, RuleGroup.INTERCONNECTION, "Zeal a faith gripped by fanaticism gains")
    treaty_peace_stability: int = rule(4, 0, 100, RuleGroup.INTERCONNECTION, "Stability a peace treaty in force lends each party")
    treaty_non_aggression_stability: int = rule(2, 0, 100, RuleGroup.INTERCONNECTION, "Stability a non-aggression pact lends each party")
    treaty_alliance_stability: int = rule(3, 0, 100, RuleGroup.INTERCONNECTION, "Stability an alliance lends each party")
    treaty_alliance_legitimacy: int = rule(2, 0, 100, RuleGroup.INTERCONNECTION, "Legitimacy an alliance lends each party")
    treaty_guarantee_stability: int = rule(3, 0, 100, RuleGroup.INTERCONNECTION, "Stability a guarantee lends each party")
    treaty_marriage_legitimacy: int = rule(3, 0, 100, RuleGroup.INTERCONNECTION, "Legitimacy a marriage pact lends each party")
    treaty_vassal_legitimacy: int = rule(6, 0, 100, RuleGroup.INTERCONNECTION, "Legitimacy a vassalage treaty costs the vassal")
    treaty_tribute_stability: int = rule(4, 0, 100, RuleGroup.INTERCONNECTION, "Stability paying tribute costs the payer")
    treaty_trade_wealth: int = rule(4, 0, 100, RuleGroup.INTERCONNECTION, "Wealth a trade pact brings each party that holds wealth")
    structure_temple_piety: int = rule(4, 0, 100, RuleGroup.INTERCONNECTION, "Piety a fully working temple adds to its community")
    structure_wall_defense: int = rule(6, 0, 100, RuleGroup.INTERCONNECTION, "Defence a fully working wall adds to its community")
    structure_learning_prosperity: int = rule(3, 0, 100, RuleGroup.INTERCONNECTION, "Prosperity a fully working house of learning adds to its community")
    curse_stat_pct: int = rule(
        90,
        0,
        100,
        RuleGroup.INTERCONNECTION,
        "Share of a cursed record's prosperity, fertility, abundance, strength and wealth the curse leaves while it lasts (%)",
    )
    blessing_mortal: int = rule(6, 0, 100, RuleGroup.INTERCONNECTION, "Strength and charisma a god's blessing lends a mortal")
    blessing_community: int = rule(5, 0, 100, RuleGroup.INTERCONNECTION, "Prosperity and piety a god's blessing lends a community")
    terrain_rough_defense: int = rule(
        6,
        0,
        100,
        RuleGroup.INTERCONNECTION,
        "Defence rough ground (mountains, passes, hills, canyons, marsh, jungle, forest, islands, caverns) lends a settlement",
    )
    terrain_water_prosperity: int = rule(4, 0, 100, RuleGroup.INTERCONNECTION, "Prosperity a river valley or coast lends a community")
    terrain_harsh_prosperity: int = rule(
        4, 0, 100, RuleGroup.INTERCONNECTION, "Prosperity harsh ground (desert, tundra, ice, flesh, the void shore) takes from a community"
    )
    terrain_crystal_magic: int = rule(5, 0, 100, RuleGroup.INTERCONNECTION, "Magic a crystal field lends the people living on it")
    season_prosperity_pct: int = rule(10, 0, 100, RuleGroup.INTERCONNECTION, "Prosperity the harshest seasons (seasonality 100) take from a community (%)")
    weather_prosperity_pct: int = rule(
        25, 0, 200, RuleGroup.INTERCONNECTION, "How strongly the epoch's growing-season weather moves a community's prosperity (% of its growth effect)"
    )
    weather_morale_pct: int = rule(
        50, 0, 200, RuleGroup.INTERCONNECTION, "How strongly the weather over an army moves its morale (% of the weather's morale, cold and heat)"
    )
    god_corpse_magic: int = rule(10, 0, 100, RuleGroup.INTERCONNECTION, "Magic a god's corpse lends the region it lies in")
    god_corpse_fertility: int = rule(5, 0, 100, RuleGroup.INTERCONNECTION, "Fertility a god's corpse lends the region it lies in")
    phenomenon_epochs: int = rule(1, 0, 20, RuleGroup.INTERCONNECTION, "Epochs a magic storm keeps weighing on its region after it broke")
    phenomenon_region_magic: int = rule(6, 0, 100, RuleGroup.INTERCONNECTION, "Magic a recent magic storm leaves in its region")
    phenomenon_prosperity: int = rule(4, 0, 100, RuleGroup.INTERCONNECTION, "Prosperity a recent magic storm takes from communities in its region")


@dataclass(frozen=True)
class IncidentRules:
    thread_chain_min: int = rule(4, 2, 50, RuleGroup.INTERCONNECTION, "Length of a chain of causes at which the engine opens a story")
    chain_depth: int = rule(12, 2, 200, RuleGroup.INTERCONNECTION, "Most links of a cause chain followed back from an incident")
    threads_per_epoch: int = rule(2, 0, 20, RuleGroup.INTERCONNECTION, "Most stories the engine opens from cause chains in one epoch")
