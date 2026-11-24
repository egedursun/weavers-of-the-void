from collections.abc import Callable, Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.ecology import BeastTemper, Temperament
from aerona.rules.registry import Rules

T = BeastTemper


@dataclass(frozen=True)
class TemperSpec:
    active: bool
    held: bool
    hostile: bool
    lairbound: bool
    fear: Callable[[Rules], int]


TEMPERS: Mapping[BeastTemper, TemperSpec] = total(
    BeastTemper,
    {
        T.HUNGRY: TemperSpec(active=True, held=False, hostile=False, lairbound=False, fear=lambda rules: 100),
        T.TERRITORIAL: TemperSpec(active=True, held=False, hostile=False, lairbound=False, fear=lambda rules: 100),
        T.SLEEPING: TemperSpec(active=False, held=False, hostile=False, lairbound=True, fear=lambda rules: 50),
        T.ENRAGED: TemperSpec(active=True, held=False, hostile=True, lairbound=False, fear=lambda rules: 150),
        T.BOUND: TemperSpec(active=False, held=True, hostile=False, lairbound=False, fear=lambda rules: 30),
        T.TAMED: TemperSpec(active=False, held=True, hostile=False, lairbound=False, fear=lambda rules: 20),
        T.COMPANION: TemperSpec(active=False, held=True, hostile=False, lairbound=False, fear=lambda rules: 10),
        T.WOUNDED: TemperSpec(active=False, held=False, hostile=True, lairbound=True, fear=lambda rules: 80),
        T.BROODING: TemperSpec(active=False, held=False, hostile=True, lairbound=True, fear=lambda rules: rules.beast_tempers.brooding_fear_pct),
        T.COWED: TemperSpec(active=False, held=False, hostile=False, lairbound=True, fear=lambda rules: 30),
        T.MIGRATING: TemperSpec(active=True, held=False, hostile=False, lairbound=False, fear=lambda rules: rules.beasts.migrating_fear_pct),
        T.FLEEING: TemperSpec(active=True, held=False, hostile=False, lairbound=False, fear=lambda rules: rules.beasts.fleeing_fear_pct),
    },
)
ACTIVE_TEMPERS = frozenset(temper for temper, spec in TEMPERS.items() if spec.active)
HELD_TEMPERS = frozenset(temper for temper, spec in TEMPERS.items() if spec.held)
HOSTILE_TEMPERS = frozenset(temper for temper, spec in TEMPERS.items() if spec.hostile)


@dataclass(frozen=True)
class TemperamentSpec:
    avenges: bool
    gathers: bool
    guards: bool
    drawn: bool = True
    remembers: bool = False
    befriends: bool = False
    honoured: bool = False


TEMPERAMENTS: Mapping[Temperament, TemperamentSpec] = total(
    Temperament,
    {
        Temperament.PLACID: TemperamentSpec(avenges=False, gathers=False, guards=False),
        Temperament.SKITTISH: TemperamentSpec(avenges=False, gathers=False, guards=False),
        Temperament.CURIOUS: TemperamentSpec(avenges=False, gathers=False, guards=False),
        Temperament.FIERCE: TemperamentSpec(avenges=True, gathers=False, guards=False),
        Temperament.CUNNING: TemperamentSpec(avenges=False, gathers=True, guards=False),
        Temperament.SEIZES_PREY: TemperamentSpec(avenges=False, gathers=False, guards=False, drawn=False),
        Temperament.VENGEFUL: TemperamentSpec(avenges=True, gathers=False, guards=False, remembers=True),
        Temperament.ACQUISITIVE: TemperamentSpec(avenges=False, gathers=True, guards=False),
        Temperament.PROTECTIVE: TemperamentSpec(avenges=False, gathers=False, guards=True),
        Temperament.PLAYFUL: TemperamentSpec(avenges=False, gathers=False, guards=False, befriends=True),
        Temperament.PROUD: TemperamentSpec(avenges=True, gathers=False, guards=False, honoured=True),
    },
)
AVENGING = frozenset(kind for kind, spec in TEMPERAMENTS.items() if spec.avenges)
GATHERING = frozenset(kind for kind, spec in TEMPERAMENTS.items() if spec.gathers)
GUARDING = frozenset(kind for kind, spec in TEMPERAMENTS.items() if spec.guards)
DRAWN_TEMPERAMENTS = tuple(kind for kind, spec in TEMPERAMENTS.items() if spec.drawn)
REMEMBERING = frozenset(kind for kind, spec in TEMPERAMENTS.items() if spec.remembers)
