from collections.abc import Callable

from aerona.catalog.terrain import TERRAIN
from aerona.catalog.units import UNITS
from aerona.catalog.weather import WEATHER
from aerona.core.random import RandomKey, SeededRandom
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import ArmyProfileRow, ArmyUnitRow
from aerona.domain.enums.demography import MartialStyle
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import TerrainKind, WeatherKind
from aerona.domain.enums.military import ArmourType, OutcomeClass, ShieldType, Stance, Tactic, UnitFamily, UnitKind
from aerona.engine.military.battle import (
    Field,
    Side,
    Stack,
    call_fog,
    crossing_factor,
    make_stacks,
    outflank,
    raise_dead,
    resist,
    resolve,
    terrain_factor,
    treat,
    weather_factor,
)
from aerona.engine.military.tables import defender_cell, matchup, terrain_cell, unit_terrain, weather_cell
from aerona.rules.registry import Rules

RULES = Rules()


def stream(key: str) -> SeededRandom:
    return SeededRandom(RandomKey(7, 1, key))


def seeded(seed: int) -> Callable[[str], SeededRandom]:
    def make(key: str) -> SeededRandom:
        return SeededRandom(RandomKey(seed, 1, key))

    return make


def unit(kind: UnitKind, count: int, *, ident: int, army: int = 1, armour: ArmourType = ArmourType.NONE, weapons: list[str] | None = None) -> ArmyUnitRow:
    return ArmyUnitRow(
        id=ident,
        army_entity_id=army,
        kind=kind,
        count=count,
        quality=50,
        armour=armour,
        shield=ShieldType.NONE,
        helmet=False,
        weapons=weapons or [],
        experience=10,
        morale=60,
        fatigue=0,
        wounded=0,
        condition=100,
        locked=[],
    )


def side(name: str, rows: list[ArmyUnitRow], *, defending: bool = False, ident: int = 1) -> Side:
    entity = EntityRow(id=ident, name=name, entity_type=EntityType.PEOPLE)
    profile = ArmyProfileRow(army_entity_id=ident, stance=Stance.MARCH, doctrine=MartialStyle.SHIELDWALL, entrenchment=0, baggage=100, loot=50, locked=[])
    return Side(entity=entity, army=entity, profile=profile, stacks=make_stacks(rows), edge=1.0, defending=defending, skill=0, traits=set())


def test_rule_tables_start_equal_to_the_old_catalog() -> None:
    for terrain, spec in TERRAIN.items():
        for family, value in spec.unit_factors(RULES).items():
            assert terrain_cell(RULES, terrain, family) == value / 100
        for kind, value in spec.unit_kinds(RULES).items():
            assert unit_terrain(RULES, kind, terrain) == value / 100
        assert defender_cell(RULES, terrain) == spec.defender(RULES) / 100
    assert terrain_cell(RULES, TerrainKind.MOUNTAINS, UnitFamily.MOUNTED) == 0.3
    assert terrain_cell(RULES, TerrainKind.PLAIN, UnitFamily.INFANTRY) == 1.0
    assert defender_cell(RULES, TerrainKind.MOUNTAINS) == 1.5 and defender_cell(RULES, TerrainKind.PLAIN) == 1.0
    assert unit_terrain(RULES, UnitKind.LIGHT_INFANTRY, TerrainKind.FOREST) == 1.2
    assert unit_terrain(RULES, UnitKind.PARTISANS, TerrainKind.FOREST) == 1.3
    assert unit_terrain(RULES, UnitKind.PARTISANS, TerrainKind.DESERT) == 1.0
    for weather, weather_spec in WEATHER.items():
        for family, value in weather_spec.unit_factors(RULES).items():
            assert weather_cell(RULES, weather, family) == value / 100
    assert weather_cell(RULES, WeatherKind.STORM, UnitFamily.AIR) == RULES.battle_weather.storm_air_pct / 100
    assert matchup(RULES, Tactic.HOLD_LINE, Tactic.FRONTAL_ASSAULT) == RULES.tactic_matchups.hold_line_vs_frontal_assault_pct / 100
    assert matchup(RULES, Tactic.HOLD_LINE, Tactic.AMBUSH) == 1.0


def test_flyers_ignore_terrain_and_engines_stay_out_of_mountains() -> None:
    sky = side("Sky", [unit(UnitKind.SKY_RIDERS, 100, ident=1)])
    walkers = side("Feet", [unit(UnitKind.SIEGE_CREW, 100, ident=2)])
    mountains = Field(TerrainKind.MOUNTAINS, None, night=False)
    assert terrain_factor(RULES, sky.stacks[0], sky, mountains) == RULES.battle_terrain.sky_terrain_pct / 100
    assert terrain_factor(RULES, walkers.stacks[0], walkers, mountains) == 0.0


def test_rain_spoils_bows_more_than_crossbows_and_burrowers_thrive_underground() -> None:
    archers = side("Bows", [unit(UnitKind.ARCHERS, 100, ident=1), unit(UnitKind.CROSSBOW_INFANTRY, 100, ident=2)])
    bows, crossbows = archers.stacks
    assert weather_factor(RULES, bows, WeatherKind.RAIN) < weather_factor(RULES, crossbows, WeatherKind.RAIN)
    diggers = side("Diggers", [unit(UnitKind.SAPPERS, 100, ident=3)])
    deep = Field(TerrainKind.UNDERGROUND, None, night=False)
    plain = Field(TerrainKind.PLAIN, None, night=False)
    assert terrain_factor(RULES, diggers.stacks[0], diggers, deep) > terrain_factor(RULES, diggers.stacks[0], diggers, plain)


def test_marsh_drags_heavy_armour_and_bridges_ease_crossings() -> None:
    plate = side("Plate", [unit(UnitKind.HEAVY_INFANTRY, 100, ident=1, armour=ArmourType.PLATE)])
    marsh = Field(TerrainKind.MARSH, None, night=False)
    bare = Field(TerrainKind.MARSH, None, night=False)
    assert terrain_factor(RULES, plate.stacks[0], plate, marsh) < 1.0
    assert crossing_factor(RULES, plate, Field(None, None, False, river=True)) < crossing_factor(
        RULES, plate, Field(None, None, False, river=True, bridge=True)
    )
    assert bare.terrain is TerrainKind.MARSH


def test_willpower_blunts_terror_and_medicine_saves_the_wounded() -> None:
    brave = side("Brave", [unit(UnitKind.LINE_INFANTRY, 100, ident=1)])
    brave.willpower = 80
    craven = side("Craven", [unit(UnitKind.LINE_INFANTRY, 100, ident=2)])
    assert resist(RULES, brave, 20) < resist(RULES, craven, 20)
    healers = side("Healers", [unit(UnitKind.SUPPORT_CASTERS, 10, ident=3)])
    healers.medicine = 100
    plain = side("Plain", [unit(UnitKind.LEVY, 10, ident=4)])
    assert treat(RULES, healers, 40, 60) > treat(RULES, plain, 40, 60)
    assert treat(RULES, plain, 40, 0) == 40


def test_war_mages_call_fog_and_necromancers_raise_the_fallen() -> None:
    mages = side("Mages", [unit(UnitKind.BATTLE_CASTERS, 50, ident=1)])
    archers = side("Archers", [unit(UnitKind.ARCHERS, 500, ident=2)], ident=2)
    rules = Rules()
    called = [call_fog(rules, seeded(seed), mages, archers) for seed in range(20)]
    assert any(called)
    dead = side("Dead", [unit(UnitKind.SUMMONERS, 5, ident=3)])
    assert raise_dead(RULES, dead, 1000) == min(round(1000 * RULES.battle_magic.raise_dead_pct / 100), 5 * RULES.battle_magic.raise_per_necromancer)


def test_swift_wings_turn_a_short_line() -> None:
    riders = side("Riders", [unit(UnitKind.LIGHT_CAVALRY, 800, ident=1)])
    foot = side("Foot", [unit(UnitKind.LEVY, 200, ident=2)], defending=True, ident=2)
    log = outflank(RULES, riders, foot, Field(TerrainKind.PLAIN, None, night=False))
    assert log is not None and riders.flanking and riders.tactic_factor > 1.0


def test_the_phased_battle_decides_and_records_baggage_and_factors() -> None:
    attacker = side("Host", [unit(UnitKind.HEAVY_CAVALRY, 600, ident=1, weapons=["spear"]), unit(UnitKind.LINE_INFANTRY, 600, ident=2)])
    defender = side("Town", [unit(UnitKind.LEVY, 300, ident=3, army=2)], defending=True, ident=2)
    result = resolve(RULES, stream, attacker, defender, Field(TerrainKind.PLAIN, WeatherKind.CLEAR, night=False))
    assert result.winner is not None and result.outcome is not OutcomeClass.REFUSED
    assert set(result.factors) >= {"attacker", "defender"}
    assert result.winner.baggage_taken >= 0
    again = resolve(
        RULES,
        stream,
        side("Host", [unit(UnitKind.HEAVY_CAVALRY, 600, ident=1, weapons=["spear"]), unit(UnitKind.LINE_INFANTRY, 600, ident=2)]),
        side("Town", [unit(UnitKind.LEVY, 300, ident=3, army=2)], defending=True, ident=2),
        Field(TerrainKind.PLAIN, WeatherKind.CLEAR, night=False),
    )
    assert again.attacker.lost == result.attacker.lost


def test_stack_specs_follow_the_unit_catalog() -> None:
    stacks = make_stacks([unit(UnitKind.SKY_RIDERS, 10, ident=1)])
    assert isinstance(stacks[0], Stack) and stacks[0].flying and stacks[0].spec is UNITS[UnitKind.SKY_RIDERS]
    assert stacks[0].spec.family is UnitFamily.MOUNTED


def test_every_kind_of_unit_fights_on_every_ground_in_every_weather() -> None:
    kinds = sorted(UnitKind, key=lambda kind: kind.value)
    assert {UNITS[kind].family for kind in kinds} == set(UnitFamily)
    for kind in kinds:
        alone = resolve(
            RULES,
            stream,
            side("Host", [unit(kind, 200, ident=1)]),
            side("Town", [unit(UnitKind.LEVY, 200, ident=2, army=2)], defending=True, ident=2),
            Field(TerrainKind.PLAIN, WeatherKind.CLEAR, night=False),
        )
        assert alone.outcome is not None, kind
    for terrain in TerrainKind:
        for weather in WeatherKind:
            host = side("Host", [unit(kind, 100, ident=index + 1) for index, kind in enumerate(kinds)])
            town = side("Town", [unit(kind, 100, ident=len(kinds) + index + 1, army=2) for index, kind in enumerate(kinds)], defending=True, ident=2)
            mixed = resolve(RULES, stream, host, town, Field(terrain, weather, night=terrain is TerrainKind.UNDERGROUND))
            assert mixed.outcome is not None, (terrain, weather)
