from collections.abc import Callable
from dataclasses import replace

from aerona.core.random import RandomKey, SeededRandom
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import ArmyProfileRow, ArmyUnitRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import PlaceCover, TerrainKind
from aerona.domain.enums.military import ArmourType, Formation, MoraleState, ShieldType, Stance, Tactic, TargetClass, UnitKind
from aerona.engine.military.battle import (
    MISSILE_FAMILIES,
    Field,
    Side,
    battle_width,
    classify_losses,
    command,
    deal,
    deploy,
    disorganise,
    feint,
    hard_guard,
    hide,
    make_stacks,
    missiles,
    outflank,
    rally,
    refill,
    salvage,
    settle,
    spot,
    target_class,
)
from aerona.rules.registry import Rules

RULES = Rules()


def seeded(seed: int = 1) -> Callable[[str], SeededRandom]:
    def make(key: str) -> SeededRandom:
        return SeededRandom(RandomKey(seed, 1, key))

    return make


def unit(
    kind: UnitKind,
    count: int,
    *,
    ident: int,
    discipline: int = 40,
    armour: ArmourType = ArmourType.NONE,
    formation: Formation = Formation.LINE,
    ammunition: int = 0,
    morale: int = 60,
) -> ArmyUnitRow:
    return ArmyUnitRow(
        id=ident,
        army_entity_id=1,
        kind=kind,
        count=count,
        quality=50,
        armour=armour,
        shield=ShieldType.NONE,
        helmet=False,
        weapons=[],
        experience=10,
        morale=morale,
        fatigue=0,
        wounded=0,
        condition=60,
        organisation=100,
        discipline=discipline,
        ammunition=ammunition,
        formation=formation,
        morale_state=MoraleState.STEADY,
        missing=0,
        locked=[],
    )


def side(name: str, rows: list[ArmyUnitRow], *, ident: int = 1, defending: bool = False, skill: int = 50) -> Side:
    entity = EntityRow(id=ident, name=name, entity_type=EntityType.PEOPLE)
    profile = ArmyProfileRow(army_entity_id=ident, stance=Stance.MARCH, doctrine="shieldwall", entrenchment=0, baggage=100, loot=0, locked=[])
    return Side(entity=entity, army=entity, profile=profile, stacks=make_stacks(rows), edge=1.0, defending=defending, skill=skill, traits=set())


def test_discipline_spares_organisation_and_a_disorganised_stack_routs() -> None:
    drilled = side("Drilled", [unit(UnitKind.SPEARMEN, 100, ident=1, discipline=100)]).stacks[0]
    raw = side("Raw", [unit(UnitKind.LEVY, 100, ident=2, discipline=0)]).stacks[0]
    disorganise(RULES, drilled, 50)
    disorganise(RULES, raw, 50)
    assert drilled.row.organisation > raw.row.organisation
    disorganise(RULES, raw, 500)
    assert raw.row.organisation == 0 and raw.routed and raw.row.morale_state is MoraleState.ROUTING


def test_missile_stacks_spend_ammunition_and_fall_silent_when_it_runs_out() -> None:
    archers = side("Bows", [unit(UnitKind.ARCHERS, 200, ident=1, formation=Formation.LOOSE, ammunition=3)])
    foes = side("Foes", [unit(UnitKind.LEVY, 400, ident=2)], ident=2)
    ground = Field(TerrainKind.PLAIN, None, night=False)
    for item in (archers, foes):
        deploy(RULES, item, ground)
    first = missiles(RULES, seeded(), archers, foes, ground, families=MISSILE_FAMILIES)
    assert first > 0 and archers.stacks[0].row.ammunition == 0 and archers.stacks[0].spent == 3
    assert missiles(RULES, seeded(2), archers, foes, ground, families=MISSILE_FAMILIES) == 0


def test_morale_falls_through_the_ladder_and_a_standard_helps_rally() -> None:
    rows = [unit(UnitKind.SPEARMEN, 100, ident=index, morale=morale) for index, morale in ((1, 70), (2, 50), (3, 30), (4, 15), (5, 5))]
    host = side("Host", rows)
    states = [settle(RULES, stack) for stack in host.stacks]
    assert states == [MoraleState.STEADY, MoraleState.SHAKEN, MoraleState.WAVERING, MoraleState.ROUTING, MoraleState.BROKEN]
    host.leadership, host.standard = 100, True
    rules = replace(RULES, battle_depth=replace(RULES.battle_depth, rally_chance=100))
    assert rally(rules, seeded(), host, "test") == 1
    assert host.stacks[3].row.morale_state is MoraleState.RALLIED and not host.stacks[3].routed
    assert host.stacks[4].routed


def test_a_narrow_pass_leaves_most_of_a_host_in_reserve_until_the_front_breaks() -> None:
    host = side("Host", [unit(UnitKind.SPEARMEN, 200, ident=1), unit(UnitKind.LEVY, 300, ident=2), unit(UnitKind.LEVY, 300, ident=3)])
    plain, pass_ = Field(TerrainKind.PLAIN, None, night=False), Field(TerrainKind.HIGH_PASS, None, night=False)
    assert battle_width(RULES, pass_, False) < battle_width(RULES, plain, False)
    deploy(RULES, host, pass_)
    front = [stack for stack in host.stacks if not stack.reserve]
    assert len(front) == 1 and sum(stack.reserve for stack in host.stacks) == 2
    front[0].routed = True
    assert refill(host) >= 200 and len([stack for stack in host.stacks if stack.engaged]) == 1


def test_a_weak_commander_cannot_direct_every_stack_and_night_halves_his_span() -> None:
    rows = [unit(UnitKind.LEVY, 100 + index, ident=index) for index in range(1, 9)]
    able = side("Able", rows, skill=100)
    poor = side("Poor", [unit(UnitKind.LEVY, 100 + index, ident=index) for index in range(1, 9)], skill=0)
    day, night = Field(TerrainKind.PLAIN, None, night=False), Field(TerrainKind.PLAIN, None, night=True)
    assert command(RULES, seeded(), able, day)["span"] > command(RULES, seeded(), poor, day)["span"]
    assert command(RULES, seeded(), able, night)["span"] < command(RULES, seeded(), able, day)["span"]
    poor.babel, poor.wits = 20, 10
    orders = command(RULES, seeded(), poor, day)
    assert orders["delayed"] >= 5 and orders["misread"] >= 1


def test_cover_and_night_hide_stacks_that_spring_as_a_trap() -> None:
    hunters = side("Hunters", [unit(UnitKind.SKIRMISHERS, 300, ident=1, formation=Formation.LOOSE), unit(UnitKind.SPEARMEN, 50, ident=2)])
    blind = side("Blind", [unit(UnitKind.HEAVY_INFANTRY, 300, ident=3)], ident=2, skill=0)
    ground = Field(TerrainKind.FOREST, None, night=True, cover=PlaceCover.HEAVY)
    seen = spot(RULES, hunters, blind, ground)
    assert seen["attacker_concealment"] > 0 and hunters.trap and hunters.stacks[1].hidden
    assert hide(blind) == 0


def test_hard_targets_shrug_off_blows_that_cannot_pierce() -> None:
    plate = side("Plate", [unit(UnitKind.HEAVY_INFANTRY, 100, ident=1, armour=ArmourType.PLATE)]).stacks[0]
    levy = side("Levy", [unit(UnitKind.LEVY, 100, ident=2)], ident=2)
    crossbows = side("Bolts", [unit(UnitKind.CROSSBOWMEN, 100, ident=3)], ident=3)
    assert target_class(RULES, plate) is TargetClass.HARD
    assert hard_guard(RULES, plate, crossbows.stacks) > hard_guard(RULES, plate, levy.stacks)


def test_a_square_turns_a_charge_that_breaks_a_loose_line() -> None:
    square = side("Square", [unit(UnitKind.PIKEMEN, 200, ident=1, formation=Formation.SQUARE)])
    loose = side("Loose", [unit(UnitKind.SKIRMISHERS, 200, ident=2, formation=Formation.LOOSE)], ident=2)
    assert deal(square.stacks, 500, RULES, mode="charge") < deal(loose.stacks, 500, RULES, mode="charge")


def test_losses_split_into_their_classes_and_broken_stacks_shed_deserters() -> None:
    host = side("Host", [unit(UnitKind.LEVY, 1000, ident=1)])
    stack = host.stacks[0]
    stack.row.count, stack.lost, stack.routed = 600, 400, True
    stack.row.morale, stack.row.morale_state = 2, MoraleState.BROKEN
    host.captives = 40
    walking, stretcher = classify_losses(RULES, host)
    assert stack.killed + stack.walking + stack.stretcher + stack.captured + stack.missing == stack.lost
    assert stack.missing > 0 and stack.captured == 40 and walking == stack.walking and stretcher == stack.stretcher
    assert stack.deserted > 0 and stack.row.count == 0 and stack.lost == 1000 - stack.deserted and stack.row.missing == stack.missing


def test_the_victor_salvages_arms_and_a_feint_pins_the_reserves() -> None:
    winner = side("Winner", [unit(UnitKind.SPEARMEN, 500, ident=1)])
    loser = side("Loser", [unit(UnitKind.LEVY, 100, ident=2)], ident=2)
    loser.stacks[0].lost = 400
    before = winner.stacks[0].row.condition
    assert salvage(RULES, winner, loser) == 400 and winner.stacks[0].row.condition > before
    attacker = side("Feinting", [unit(UnitKind.SKIRMISHERS, 100, ident=3)], ident=3)
    attacker.tactic = Tactic.FEINT
    defender = side("Waiting", [unit(UnitKind.SPEARMEN, 2000, ident=4), unit(UnitKind.LEVY, 2000, ident=5)], ident=4, defending=True)
    deploy(RULES, defender, Field(TerrainKind.HIGH_PASS, None, night=False))
    rules = replace(RULES, battle_depth=replace(RULES.battle_depth, feint_reserve_pct=100))
    assert feint(rules, seeded(), attacker, defender) and refill(defender) >= 0


def test_a_broken_stack_scatters_and_does_not_fight_on() -> None:
    host = side("Host", [unit(UnitKind.LEVY, 100, ident=1, morale=2)])
    stack = host.stacks[0]
    stack.row.morale_state = MoraleState.BROKEN
    stack.routed = True
    classify_losses(RULES, host)
    assert stack.row.count == 0 and stack.deserted + stack.missing == 100 and stack.row.missing == stack.missing


def test_a_turned_flank_throws_the_line_into_disorder() -> None:
    riders = side("Riders", [unit(UnitKind.LIGHT_CAVALRY, 400, ident=1)])
    line = side("Line", [unit(UnitKind.LEVY, 100, ident=2)], ident=2, defending=True)
    before = line.stacks[0].row.organisation
    assert outflank(RULES, riders, line, Field(TerrainKind.PLAIN, None, night=False)) is not None
    assert line.stacks[0].row.organisation < before
