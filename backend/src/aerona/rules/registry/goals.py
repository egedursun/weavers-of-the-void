from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule

G = RuleGroup.GOALS_AND_ACHIEVEMENTS


@dataclass(frozen=True)
class GoalsRules:
    keep_apocalypse_away_epochs: int = rule(20, 1, 200, RuleGroup.APOCALYPSE, "Scenario: duration to keep the apocalypse away (epochs)")
    keep_apocalypse_away_step: int = rule(5, 0, 200, RuleGroup.APOCALYPSE, "Scenario: epochs added to keep the apocalypse away at each higher tier")
    keep_apocalypse_away_pct: int = rule(80, 1, 100, RuleGroup.APOCALYPSE, "Scenario: point the clock must not reach (% of threshold)")
    score_apocalypse_penalty: int = rule(150, 0, 1000, RuleGroup.APOCALYPSE, "Score: penalty for the apocalypse when the clock is at the threshold")
    keep_apocalypse_away_points: int = rule(300, 0, 10000, G, "Scenario points: keep the apocalypse away")
    one_faith_min_peoples: int = rule(3, 1, 100, G, "Scenario: minimum peoples that must unite in one faith")
    one_faith_step: int = rule(2, 0, 100, G, "Scenario: peoples added to one faith at each higher tier")
    one_faith_points: int = rule(250, 0, 10000, G, "Scenario points: all peoples in one faith")
    lost_star_stars: int = rule(1, 1, 100, G, "Scenario: stars that must be reborn to rekindle the lost star")
    lost_star_step: int = rule(1, 0, 100, G, "Scenario: reborn stars added at each higher tier")
    lost_star_points: int = rule(200, 0, 10000, G, "Scenario points: rekindle the lost star")
    inhabited_worlds: int = rule(5, 1, 100, G, "Scenario: number of worlds with living peoples")
    inhabited_worlds_step: int = rule(3, 0, 100, G, "Scenario: inhabited worlds added at each higher tier")
    multiworld_points: int = rule(250, 0, 10000, G, "Scenario points: multi-world cosmos")
    peace_epochs: int = rule(5, 1, 200, G, "Scenario: consecutive epochs of peace")
    peace_step: int = rule(5, 0, 200, G, "Scenario: peace epochs added at each higher tier")
    peace_points: int = rule(200, 0, 10000, G, "Scenario points: long peace")
    cosmic_stage: int = rule(4, 1, 5, G, "Scenario: stage civilization must reach")
    cosmic_step: int = rule(1, 0, 5, G, "Scenario: civilization stages added at each higher tier")
    cosmic_points: int = rule(300, 0, 10000, G, "Scenario points: civilization reaching for the stars")
    loyal_epochs: int = rule(10, 1, 200, G, "Scenario: epochs that must pass without rebellion")
    loyal_step: int = rule(5, 0, 200, G, "Scenario: loyal epochs added at each higher tier")
    loyal_min_loyalty: int = rule(60, 0, 100, G, "Scenario: loyalty all sons must exceed")
    loyal_points: int = rule(250, 0, 10000, G, "Scenario points: loyal pantheon")
    horizon_lands: int = rule(8, 1, 1000, G, "Scenario: new lands that must be opened (region or place; by exploration, a son or the god's hand)")
    horizon_step: int = rule(4, 0, 1000, G, "Scenario: new lands added at each higher tier")
    horizon_regions: int = rule(2, 0, 1000, G, "Scenario: at least this many of them must be new regions")
    horizon_points: int = rule(250, 0, 10000, G, "Scenario points: new horizons")
    golden_age_count: int = rule(1, 1, 100, G, "Scenario: golden ages that must begin")
    golden_age_step: int = rule(1, 0, 100, G, "Scenario: golden ages added at each higher tier")
    golden_age_points: int = rule(250, 0, 10000, G, "Scenario points: a golden age")
    wonders_count: int = rule(2, 1, 100, G, "Scenario: new wonders that must be raised")
    wonders_step: int = rule(2, 0, 100, G, "Scenario: wonders added at each higher tier")
    wonders_points: int = rule(300, 0, 10000, G, "Scenario points: an age of wonders")
    far_voyages_count: int = rule(1, 1, 100, G, "Scenario: voyages beyond a galaxy that must arrive")
    far_voyages_step: int = rule(2, 0, 100, G, "Scenario: voyages beyond a galaxy added at each higher tier")
    far_voyages_points: int = rule(350, 0, 10000, G, "Scenario points: bridge the galaxies")
    learning_count: int = rule(5, 1, 1000, G, "Scenario: new knowledge and theories that must appear")
    learning_step: int = rule(5, 0, 1000, G, "Scenario: knowledge and theories added at each higher tier")
    learning_points: int = rule(250, 0, 10000, G, "Scenario points: an age of learning")
    teeming_species: int = rule(5, 1, 1000, G, "Scenario: new species that must appear")
    teeming_step: int = rule(5, 0, 1000, G, "Scenario: species added at each higher tier")
    teeming_points: int = rule(200, 0, 10000, G, "Scenario points: teeming life")
    faithful_communities: int = rule(5, 1, 1000, G, "Scenario: communities that must worship the Creator directly")
    faithful_step: int = rule(5, 0, 1000, G, "Scenario: Creator-worshipping communities added at each higher tier")
    faithful_points: int = rule(250, 0, 10000, G, "Scenario points: the Creator's faithful")
    scenario_target_max: int = rule(1000, 1, 1000000, G, "Scenario: highest target a goal may set")
    target_points_cap_pct: int = rule(400, 100, 10000, G, "Scenario: most points a raised target can earn (% of the goal's points)")
    deadline_bonus_pct: int = rule(25, 0, 1000, G, "Scenario: extra points for a goal with a deadline (%)")
    deadline_max_epochs: int = rule(500, 1, 10000, G, "Scenario: longest deadline a goal may set (epochs)")
    custom_points: int = rule(150, 0, 10000, G, "Custom goal: points for a target that doubles the value at the start")
    custom_ratio_cap_pct: int = rule(400, 100, 10000, G, "Custom goal: most points a far target can earn (% of the custom goal points)")
    custom_hold_points: int = rule(10, 0, 1000, G, "Custom goal: points for each epoch the target must be held")
    custom_hold_max_epochs: int = rule(200, 1, 10000, G, "Custom goal: longest hold a custom goal may ask (epochs)")
    custom_max_running: int = rule(5, 1, 50, G, "Custom goal: most custom goals running at once")
    custom_target_max: int = rule(2000000000, 1, 2000000000, G, "Custom goal: highest target a custom goal may set")
    score_population: int = rule(20, 0, 1000, G, "Score: per tenfold of population")
    score_diversity_cap: int = rule(150, 0, 100000, G, "Score: maximum points for record diversity")
    score_language: int = rule(5, 0, 1000, G, "Score: per language")
    score_world: int = rule(25, 0, 1000, G, "Score: per world")
    score_stage: int = rule(20, 0, 1000, G, "Score: per step of the highest civilization stage")
    score_life: int = rule(2, 0, 1000, G, "Score: per species, beast and spirit")
    score_life_cap: int = rule(150, 0, 100000, G, "Score: maximum points for life")
    score_faith: int = rule(5, 0, 1000, G, "Score: per cult and per community worshipping the Creator")
    score_faith_cap: int = rule(200, 0, 100000, G, "Score: maximum points for faith")
    score_culture: int = rule(1, 0, 1000, G, "Score: per artwork, art form, legend and tradition")
    score_culture_cap: int = rule(200, 0, 100000, G, "Score: maximum points for culture")
    score_knowledge: int = rule(2, 0, 1000, G, "Score: per knowledge and theory")
    score_knowledge_cap: int = rule(200, 0, 100000, G, "Score: maximum points for knowledge")
    score_wonder: int = rule(25, 0, 1000, G, "Score: per wonder and museum collection")
    score_wonder_cap: int = rule(300, 0, 100000, G, "Score: maximum points for wonders")
    score_scale: int = rule(15, 0, 1000, G, "Score: per galaxy, galaxy cluster and dimension")
    score_scale_cap: int = rule(300, 0, 100000, G, "Score: maximum points for the scales of the cosmos")
    score_exploration: int = rule(2, 0, 1000, G, "Score: per discovery and arrived journey")
    score_exploration_cap: int = rule(200, 0, 100000, G, "Score: maximum points for exploration")


RENAMED_RULES = {
    ("goals", "default_loyalty"): ("reputation", "default_loyalty"),
    ("goals", "ach_worlds"): ("achievements", "tier_1_second_sky"),
    ("goals", "ach_worlds_points"): ("achievements", "points_second_sky"),
    ("goals", "ach_stars"): ("achievements", "tier_1_constellation"),
    ("goals", "ach_stars_points"): ("achievements", "points_constellation"),
    ("goals", "ach_prophecy_points"): ("achievements", "points_prophecy_fulfilled"),
    ("goals", "ach_resurrection_points"): ("achievements", "points_return_from_death"),
    ("goals", "ach_revolt_points"): ("achievements", "points_creators_hand"),
    ("goals", "ach_languages"): ("achievements", "tier_1_babel"),
    ("goals", "ach_languages_points"): ("achievements", "points_babel"),
    ("goals", "ach_population"): ("achievements", "tier_1_crowded_world"),
    ("goals", "ach_population_points"): ("achievements", "points_crowded_world"),
    ("goals", "ach_first_prayer_points"): ("achievements", "points_first_prayer"),
    ("goals", "ach_cult"): ("achievements", "tier_1_creators_cult"),
    ("goals", "ach_cult_points"): ("achievements", "points_creators_cult"),
    ("goals", "ach_voyager_points"): ("achievements", "points_interstellar_traveller"),
    ("goals", "ach_epic_points"): ("achievements", "points_saga_completed"),
    ("goals", "ach_epochs"): ("achievements", "tier_1_god_of_epochs"),
    ("goals", "ach_epochs_points"): ("achievements", "points_god_of_epochs"),
    ("goals", "ach_ancient_epochs"): ("achievements", "tier_1_ancient"),
    ("goals", "ach_ancient_points"): ("achievements", "points_ancient"),
    ("goals", "ach_sons"): ("achievements", "tier_1_crowded_pantheon"),
    ("goals", "ach_sons_points"): ("achievements", "points_crowded_pantheon"),
    ("goals", "ach_peace_min_peoples"): ("achievements", "tier_1_weapons_silent"),
    ("goals", "ach_peace_points"): ("achievements", "points_weapons_silent"),
    ("goals", "ach_explorers_points"): ("achievements", "points_first_explorers"),
    ("goals", "ach_sensed_world_points"): ("achievements", "points_sensed_world"),
}
