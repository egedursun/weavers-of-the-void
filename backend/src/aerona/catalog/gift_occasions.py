from collections.abc import Callable, Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.cycles import GiftOccasion, GiftState
from aerona.rules.registry import Rules

G = GiftOccasion


@dataclass(frozen=True)
class OccasionSpec:
    label: str
    debt: Callable[[Rules], int]
    standing: int
    in_kind: bool
    competitive: bool


OCCASIONS: Mapping[GiftOccasion, OccasionSpec] = total(
    GiftOccasion,
    {
        G.COURTESY: OccasionSpec("Courtesy", lambda rules: rules.gifts.courtesy_debt, standing=100, in_kind=True, competitive=False),
        G.FEAST: OccasionSpec("A rank-claiming feast", lambda rules: rules.gifts.feast_debt, standing=150, in_kind=True, competitive=True),
        G.CIRCUIT: OccasionSpec("A ceremonial circuit", lambda rules: rules.gifts.circuit_debt, standing=100, in_kind=True, competitive=False),
        G.OFFERING: OccasionSpec("An offering", lambda rules: rules.gifts.offering_debt, standing=100, in_kind=False, competitive=False),
        G.MARRIAGE: OccasionSpec("A marriage gift", lambda rules: rules.gifts.marriage_debt, standing=100, in_kind=True, competitive=False),
        G.RETURN: OccasionSpec("A return gift", lambda rules: rules.gifts.return_debt, standing=50, in_kind=True, competitive=False),
        G.ALLIANCE: OccasionSpec("Between allies", lambda rules: rules.gifts.alliance_debt, standing=100, in_kind=True, competitive=False),
        G.RELIEF: OccasionSpec("Aid in a stricken hour", lambda rules: rules.gifts.relief_debt, standing=120, in_kind=True, competitive=False),
        G.BIRTH: OccasionSpec("At a birth", lambda rules: rules.gifts.birth_debt, standing=100, in_kind=True, competitive=False),
        G.FUNERAL: OccasionSpec("To the bereaved", lambda rules: rules.gifts.funeral_debt, standing=100, in_kind=True, competitive=False),
        G.AMENDS: OccasionSpec("Amends for a wrong", lambda rules: rules.gifts.amends_debt, standing=80, in_kind=True, competitive=False),
        G.PATRONAGE: OccasionSpec("From a patron", lambda rules: rules.gifts.patronage_debt, standing=120, in_kind=False, competitive=False),
        G.HOSPITALITY: OccasionSpec("Between host and guest", lambda rules: rules.gifts.hospitality_debt, standing=100, in_kind=True, competitive=False),
    },
)
COMPETITIVE = frozenset(occasion for occasion, spec in OCCASIONS.items() if spec.competitive)


@dataclass(frozen=True)
class StateSpec:
    label: str
    held: bool
    settled: bool
    remembered: bool = False


S = GiftState
GIFT_STATES: Mapping[GiftState, StateSpec] = total(
    GiftState,
    {
        S.OPEN: StateSpec("Awaiting return", held=True, settled=False),
        S.RETURNED: StateSpec("Returned", held=True, settled=True),
        S.REFUSED: StateSpec("Refused", held=False, settled=True),
        S.DESTROYED: StateSpec("Destroyed, to be matched", held=False, settled=False),
        S.LAPSED: StateSpec("Unanswered", held=False, settled=True),
        S.EXCEEDED: StateSpec("Answered with more", held=False, settled=True, remembered=True),
        S.PASSED_ON: StateSpec("Passed on along a circuit", held=False, settled=True, remembered=True),
        S.RELEASED: StateSpec("Debt released", held=False, settled=True, remembered=True),
    },
)
HOLDING = frozenset(state for state, spec in GIFT_STATES.items() if spec.held)
REMEMBERED = frozenset(state for state, spec in GIFT_STATES.items() if spec.remembered)
