from collections.abc import Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.culture import CalendarSlot, SlotOpening, TraditionEffectKind
from aerona.domain.enums.mind import ValueAxis

E = TraditionEffectKind


@dataclass(frozen=True)
class SlotSpec:
    label: str
    opening: SlotOpening
    effects: frozenset[TraditionEffectKind]
    lean: ValueAxis


SLOTS: Mapping[CalendarSlot, SlotSpec] = total(
    CalendarSlot,
    {
        CalendarSlot.SOWING: SlotSpec("Sowing", SlotOpening.GROWING, frozenset({E.FERTILITY, E.HARVEST}), ValueAxis.NATURE),
        CalendarSlot.HARVEST: SlotSpec("Harvest", SlotOpening.GROWING, frozenset({E.HARVEST, E.SATISFACTION, E.COHESION}), ValueAxis.NATURE),
        CalendarSlot.MIDWINTER: SlotSpec("Midwinter", SlotOpening.DEAD_OF_WINTER, frozenset({E.COHESION, E.PLACATION, E.FOOD_SAVED}), ValueAxis.TRADITION),
        CalendarSlot.CAMPAIGN: SlotSpec("Campaign", SlotOpening.WAR_SEASON, frozenset({E.MARTIAL, E.COHESION}), ValueAxis.MARTIAL),
        CalendarSlot.HOLY_DAY: SlotSpec("Holy day", SlotOpening.HOLY, frozenset(TraditionEffectKind), ValueAxis.PIETY),
    },
)
