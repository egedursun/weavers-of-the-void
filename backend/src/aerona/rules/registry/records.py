from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class RecordsRules:
    witness_radius: int = rule(1, 0, 10, RuleGroup.CHRONICLE, "Hops of travel within which those present become witnesses of a happening")
    fidelity_saw: int = rule(90, 0, 100, RuleGroup.CHRONICLE, "How true the account of a witness who saw a happening is (percent)")
    fidelity_heard: int = rule(60, 0, 100, RuleGroup.CHRONICLE, "How true the account of a witness who heard of a happening nearby is (percent)")
    fidelity_told: int = rule(40, 0, 100, RuleGroup.CHRONICLE, "How true the account of one who was told of a happening is (percent)")
    distortion_per_hop_pct: int = rule(10, 0, 100, RuleGroup.CHRONICLE, "Chance that each retelling of an account changes one of its facts or steps")
    naming_magnitude: int = rule(70, 0, 100, RuleGroup.CHRONICLE, "Magnitude from which a happening is given a name of its own")
    checkpoint_epochs: int = rule(5, 1, 100, RuleGroup.CHRONICLE, "Epochs between checkpoints of the recorded state of the world")
    moment_spread_instant_pct: int = rule(100, 0, 100, RuleGroup.CHRONICLE, "Share of the epoch over which single happenings are spread by their own moment")
    moment_spread_phase_pct: int = rule(0, 0, 100, RuleGroup.CHRONICLE, "Share of the epoch over which the unexplained writes of an engine step are spread")
    moment_spread_march_pct: int = rule(100, 0, 100, RuleGroup.CHRONICLE, "Share of the epoch over which marches begin")
    moment_spread_voyage_pct: int = rule(100, 0, 100, RuleGroup.CHRONICLE, "Share of the epoch over which voyages and journeys begin")
    moment_spread_course_pct: int = rule(100, 0, 100, RuleGroup.CHRONICLE, "Share of the epoch over which the courses of sicknesses and other processes begin")
    moment_spread_building_pct: int = rule(100, 0, 100, RuleGroup.CHRONICLE, "Share of the epoch over which works of building begin")
    moment_spread_rounds_pct: int = rule(100, 0, 100, RuleGroup.CHRONICLE, "Share of the epoch over which contests fought in rounds take place")
    moment_spread_season_pct: int = rule(100, 0, 100, RuleGroup.CHRONICLE, "Share of the epoch over which seasonal happenings begin")
    moment_spread_year_pct: int = rule(100, 0, 100, RuleGroup.CHRONICLE, "Share of the epoch over which yearly happenings begin")
    moment_spread_life_pct: int = rule(100, 0, 100, RuleGroup.CHRONICLE, "Share of the epoch over which happenings of a whole life begin")
