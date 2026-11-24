from aerona.catalog.means import LIFTS, LOCKS, MINE_PUMPS
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.means import LockKind, WaterLift
from aerona.engine.means.security import best_lock, difficulty
from aerona.engine.means.water import best_lift
from aerona.rules.registry import Rules

RULES = Rules()


def test_seven_locks_and_which_yield_to_picks() -> None:
    assert len(LockKind) == 8 and set(LOCKS) == set(LockKind)
    assert not LOCKS[LockKind.WORKED].picked and LOCKS[LockKind.ELECTRONIC].fails_in_outage
    assert difficulty(RULES, LockKind.WORKED) == RULES.locks.worked_difficulty


def test_an_electronic_lock_needs_its_technique() -> None:
    assert best_lock(RULES, 9, frozenset()) is LockKind.COMBINATION
    assert best_lock(RULES, 9, frozenset({Technique.WARDING})) is LockKind.WORKED


def test_seven_ways_of_lifting_water_and_the_wind_pump_needs_wind() -> None:
    assert len(WaterLift) == 8 and set(LIFTS) == set(WaterLift)
    known = frozenset({Technique.MACHINE_TOOLS, Technique.IRRIGATION})
    assert best_lift(known, mine=False) is WaterLift.WIND_PUMP
    assert best_lift(known, mine=False, windy=False) is WaterLift.SHADUF
    assert LIFTS[WaterLift.ELECTRIC_PUMP].electric and WaterLift.ELECTRIC_PUMP in MINE_PUMPS
