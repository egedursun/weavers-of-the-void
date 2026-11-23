from dataclasses import dataclass

from aerona.domain.enums.environment import SeasonWarmth, SeasonWater, TerrainKind, WeatherKind
from aerona.domain.enums.world import WorldType
from aerona.engine.environment.season_shape import apportion, position_at_fraction, rebalanced, season_of_index, season_phase
from aerona.engine.environment.seasons import season_count_for, season_drafts
from aerona.engine.environment.weather import WeatherInputs, weather_weights
from aerona.engine.recording.moments import Calendar
from aerona.rules.registry import Rules

RULES = Rules()


@dataclass(frozen=True)
class Season:
    position: int
    temperature_shift: int
    rain_shift: int
    share_pct: int = 0


def test_a_world_of_high_tilt_keeps_eight_seasons_whose_shares_fill_the_year() -> None:
    count = season_count_for(RULES, WorldType.ORDINARY, 85)
    drafts = season_drafts(RULES, WorldType.ORDINARY, count, 85)
    assert count == 8
    assert sum(draft.share_pct for draft in drafts) == 100
    phases = season_phase(drafts)
    turning = [draft for draft in drafts if phases[draft.position].warmth in (SeasonWarmth.WARMING, SeasonWarmth.COOLING)]
    assert turning and all(draft.share_pct == RULES.seasons.transition_share_pct for draft in turning)
    assert {phases[draft.position].warmth for draft in drafts} >= {SeasonWarmth.WARMEST, SeasonWarmth.COLDEST}


def test_season_drafts_carry_no_fixed_names() -> None:
    drafts = season_drafts(RULES, WorldType.ORDINARY, 4, 30)
    assert not hasattr(drafts[0], "name")


def test_water_reads_against_the_other_seasons() -> None:
    phases = season_phase([Season(0, 0, -80), Season(1, 0, 0), Season(2, 0, 80)])
    assert phases[0].water is SeasonWater.ARID and phases[2].water is SeasonWater.DELUGE


def test_shares_rebalance_around_a_fixed_and_a_held_season() -> None:
    shares = rebalanced({0: 25, 1: 25, 2: 25, 3: 25}, {0: 40}, frozenset({1}))
    assert shares[0] == 40 and shares[1] == 25 and sum(shares.values()) == 100
    assert apportion([1.0, 1.0, 1.0]) == [34, 33, 33]


def test_a_long_season_is_picked_more_often_by_its_share() -> None:
    seasons = [Season(0, 0, 0, 80), Season(1, 0, 0, 20)]
    picks = [season_of_index(seasons, index) for index in range(200)]
    assert sum(1 for pick in picks if pick is not None and pick.position == 0) > 140
    assert position_at_fraction([80, 20], 0.79) == 0 and position_at_fraction([80, 20], 0.81) == 1


def test_moments_fall_in_seasons_by_their_shares() -> None:
    calendar = Calendar(100, 2, 24, (80, 20))
    assert calendar.place(1, 0.5).season == 0
    assert calendar.place(1, 0.9).season == 1


def ground(temperature: int, rainfall: int, warmth: SeasonWarmth = SeasonWarmth.EVEN) -> WeatherInputs:
    return WeatherInputs(region_id=1, temperature=temperature, rainfall=rainfall, latitude=50, magic_density=0, terrain=TerrainKind.PLAIN, season_warmth=warmth)


def test_frost_and_ice_storm_are_drawn_near_the_cold_threshold() -> None:
    cold = RULES.weather.cold_threshold
    dry = ground(cold + 2, 10, SeasonWarmth.WARMING)
    wet = ground(cold, 90)
    hot = ground(95, 10)
    assert weather_weights(RULES, dry)[WeatherKind.FROST] > 0
    assert weather_weights(RULES, wet)[WeatherKind.ICE_STORM] > 0
    assert weather_weights(RULES, hot)[WeatherKind.FROST] == 0 and weather_weights(RULES, hot)[WeatherKind.ICE_STORM] == 0
    turning = weather_weights(RULES, dry)[WeatherKind.FROST]
    plain = weather_weights(RULES, WeatherInputs(region_id=1, temperature=cold + 2, rainfall=10, latitude=50, magic_density=0, terrain=TerrainKind.PLAIN))[
        WeatherKind.FROST
    ]
    assert turning > plain
