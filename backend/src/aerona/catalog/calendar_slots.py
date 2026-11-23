from collections.abc import Callable, Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.culture import CalendarSlot, SlotOpening, TraditionEffectKind
from aerona.domain.enums.mind import ValueAxis
from aerona.rules.registry import Rules

E = TraditionEffectKind
C = CalendarSlot


@dataclass(frozen=True)
class SlotSpec:
    label: str
    opening: SlotOpening
    effects: frozenset[TraditionEffectKind]
    lean: ValueAxis
    strength: Callable[[Rules], int]


SLOTS: Mapping[CalendarSlot, SlotSpec] = total(
    CalendarSlot,
    {
        C.SOWING: SlotSpec(
            "Sowing", SlotOpening.WARMING_GROWTH, frozenset({E.FERTILITY, E.HARVEST}), ValueAxis.NATURE, lambda rules: rules.calendar.sowing_effect
        ),
        C.HARVEST: SlotSpec(
            "Harvest",
            SlotOpening.AFTER_GREENEST,
            frozenset({E.HARVEST, E.SATISFACTION, E.COHESION}),
            ValueAxis.NATURE,
            lambda rules: rules.calendar.harvest_effect,
        ),
        C.MIDWINTER: SlotSpec(
            "Midwinter",
            SlotOpening.DEAD_OF_WINTER,
            frozenset({E.COHESION, E.PLACATION, E.FOOD_SAVED}),
            ValueAxis.KINSHIP,
            lambda rules: rules.calendar.midwinter_effect,
        ),
        C.MIDSUMMER: SlotSpec(
            "Midsummer",
            SlotOpening.HEIGHT_OF_SUMMER,
            frozenset({E.COHESION, E.FERTILITY, E.SATISFACTION}),
            ValueAxis.LEISURE,
            lambda rules: rules.calendar.midsummer_effect,
        ),
        C.CAMPAIGN: SlotSpec(
            "Campaign", SlotOpening.WAR_SEASON, frozenset({E.MARTIAL, E.COHESION}), ValueAxis.MARTIAL, lambda rules: rules.calendar.campaign_effect
        ),
        C.HOLY_DAY: SlotSpec("Holy day", SlotOpening.HOLY, frozenset(TraditionEffectKind), ValueAxis.PIETY, lambda rules: rules.calendar.holy_day_effect),
        C.NEW_YEAR: SlotSpec(
            "New year", SlotOpening.YEAR, frozenset({E.COHESION, E.SATISFACTION, E.REST}), ValueAxis.TRADITION, lambda rules: rules.calendar.new_year_effect
        ),
        C.REMEMBRANCE: SlotSpec(
            "Remembrance",
            SlotOpening.REMEMBERED,
            frozenset({E.PIETY, E.PLACATION, E.COHESION}),
            ValueAxis.TRADITION,
            lambda rules: rules.calendar.remembrance_effect,
        ),
        C.MARKET: SlotSpec(
            "Market", SlotOpening.FAIR, frozenset({E.TRADE, E.SATISFACTION, E.COHESION}), ValueAxis.WEALTH, lambda rules: rules.calendar.market_effect
        ),
        C.WILD_HARVEST: SlotSpec(
            "Wild harvest",
            SlotOpening.WILD_PLENTY,
            frozenset({E.FORAGE, E.COHESION, E.SATISFACTION}),
            ValueAxis.NATURE,
            lambda rules: rules.calendar.wild_harvest_effect,
        ),
        C.RAINS: SlotSpec(
            "First rains", SlotOpening.RAINS_COME, frozenset({E.FERTILITY, E.HARVEST, E.COHESION}), ValueAxis.NATURE, lambda rules: rules.calendar.rains_effect
        ),
        C.ASSEMBLY: SlotSpec(
            "Assembly", SlotOpening.COUNCIL, frozenset({E.COHESION, E.SATISFACTION}), ValueAxis.TRADITION, lambda rules: rules.calendar.assembly_effect
        ),
        C.TAX: SlotSpec("Tax gathering", SlotOpening.DUES, frozenset({E.TRADE}), ValueAxis.WEALTH, lambda rules: rules.calendar.tax_effect),
        C.PILGRIMAGE: SlotSpec(
            "Pilgrimage", SlotOpening.SACRED_ROAD, frozenset({E.PIETY, E.COHESION}), ValueAxis.PIETY, lambda rules: rules.calendar.pilgrimage_effect
        ),
    },
)
