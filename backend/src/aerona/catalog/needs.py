from collections.abc import Mapping
from types import MappingProxyType

from aerona.domain.enums.demography import Job
from aerona.domain.enums.economy import CommodityKind, WorkshopKind
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.society_depth import ShortfallEffect

C = CommodityKind
S = SocialClass
E = ShortfallEffect
J = Job
W = WorkshopKind
AVERAGE = 100

SHORTFALL_EFFECTS: Mapping[CommodityKind, ShortfallEffect] = MappingProxyType(
    {
        C.GRAIN: E.HUNGER,
        C.LIVESTOCK: E.HUNGER,
        C.FISH: E.HUNGER,
        C.BREAD: E.HUNGER,
        C.FODDER: E.HERDS,
        C.TIMBER: E.COLD,
        C.FUEL: E.COLD,
        C.CLOTH: E.COLD,
        C.ORE: E.TOIL,
        C.STONE: E.TOIL,
        C.TOOLS: E.TOIL,
        C.WEAPONS: E.INSECURITY,
        C.ARMOUR: E.INSECURITY,
        C.MOUNTS: E.INSECURITY,
        C.SIEGE_MATERIEL: E.INSECURITY,
        C.MEDICINE: E.SICKNESS,
        C.LUXURIES: E.STATUS,
        C.INCENSE: E.IMPIETY,
        C.SACRED_GOODS: E.IMPIETY,
        C.MAGICAL_REAGENTS: E.ARCANE,
        C.MEAT: E.HUNGER,
        C.MILK: E.HUNGER,
        C.CHEESE: E.HUNGER,
        C.FRUIT: E.HUNGER,
        C.TUBERS: E.HUNGER,
        C.COAL: E.COLD,
        C.PEAT: E.COLD,
        C.DUNG: E.COLD,
    }
)

EFFECT_CLASSES: Mapping[ShortfallEffect, frozenset[SocialClass]] = MappingProxyType(
    {
        E.HUNGER: frozenset(SocialClass),
        E.HERDS: frozenset({S.FARMER, S.SERF_OR_SLAVE, S.NOBLE}),
        E.COLD: frozenset(SocialClass),
        E.SICKNESS: frozenset(SocialClass),
        E.IMPIETY: frozenset({S.PRIEST, S.MONASTIC}),
        E.STATUS: frozenset({S.NOBLE, S.MERCHANT}),
        E.TOIL: frozenset({S.ARTISAN, S.FARMER, S.SERF_OR_SLAVE}),
        E.INSECURITY: frozenset({S.WARRIOR, S.NOBLE}),
        E.ARCANE: frozenset({S.SCRIBE, S.MONASTIC}),
    }
)

EFFECT_BASKET: Mapping[ShortfallEffect, Mapping[SocialClass, int]] = MappingProxyType(
    {
        E.HUNGER: MappingProxyType({}),
        E.HERDS: MappingProxyType({S.FARMER: 200, S.WARRIOR: 150, S.NOBLE: 120, S.SERF_OR_SLAVE: 80, S.OUTCAST: 10}),
        E.COLD: MappingProxyType({S.NOBLE: 180, S.MERCHANT: 140, S.SERF_OR_SLAVE: 70, S.OUTCAST: 50}),
        E.SICKNESS: MappingProxyType({S.NOBLE: 160, S.PRIEST: 120, S.MERCHANT: 120, S.OUTCAST: 40, S.SERF_OR_SLAVE: 50}),
        E.IMPIETY: MappingProxyType(
            {S.PRIEST: 500, S.MONASTIC: 400, S.NOBLE: 160, S.MERCHANT: 90, S.SERF_OR_SLAVE: 40, S.OUTCAST: 20, S.WARRIOR: 70, S.FARMER: 70}
        ),
        E.STATUS: MappingProxyType(
            {
                S.NOBLE: 600,
                S.MERCHANT: 300,
                S.PRIEST: 100,
                S.SCRIBE: 100,
                S.ARTISAN: 50,
                S.WARRIOR: 50,
                S.MONASTIC: 20,
                S.FARMER: 20,
                S.SERF_OR_SLAVE: 0,
                S.OUTCAST: 0,
            }
        ),
        E.TOIL: MappingProxyType(
            {S.ARTISAN: 400, S.FARMER: 120, S.SERF_OR_SLAVE: 90, S.MERCHANT: 40, S.PRIEST: 20, S.SCRIBE: 20, S.MONASTIC: 40, S.NOBLE: 30, S.OUTCAST: 20}
        ),
        E.INSECURITY: MappingProxyType(
            {S.WARRIOR: 600, S.NOBLE: 250, S.FARMER: 20, S.ARTISAN: 20, S.MERCHANT: 30, S.PRIEST: 10, S.SCRIBE: 10, S.MONASTIC: 10, S.SERF_OR_SLAVE: 0}
        ),
        E.ARCANE: MappingProxyType(
            {S.SCRIBE: 350, S.MONASTIC: 300, S.PRIEST: 150, S.NOBLE: 100, S.MERCHANT: 30, S.FARMER: 5, S.SERF_OR_SLAVE: 0, S.OUTCAST: 0}
        ),
    }
)

SERVE_ORDER: tuple[SocialClass, ...] = (
    S.NOBLE,
    S.PRIEST,
    S.MERCHANT,
    S.WARRIOR,
    S.SCRIBE,
    S.MONASTIC,
    S.ARTISAN,
    S.FARMER,
    S.SERF_OR_SLAVE,
    S.OUTCAST,
)

CLASS_INCOME: Mapping[SocialClass, int] = MappingProxyType(
    {
        S.NOBLE: 800,
        S.MERCHANT: 450,
        S.PRIEST: 220,
        S.SCRIBE: 160,
        S.ARTISAN: 150,
        S.WARRIOR: 130,
        S.MONASTIC: 90,
        S.FARMER: 100,
        S.SERF_OR_SLAVE: 25,
        S.OUTCAST: 10,
    }
)

JOB_GOODS: Mapping[Job, tuple[CommodityKind, ...]] = MappingProxyType(
    {
        J.FARMING: (C.GRAIN, C.BREAD, C.FRUIT, C.TUBERS),
        J.HERDING: (C.LIVESTOCK, C.FODDER, C.MOUNTS, C.MEAT, C.MILK, C.CHEESE, C.DUNG),
        J.FISHING: (C.FISH,),
        J.MINING: (C.ORE, C.STONE, C.COAL, C.PEAT),
        J.CRAFTING: (C.TOOLS, C.CLOTH, C.WEAPONS, C.ARMOUR, C.FUEL, C.MEDICINE),
        J.TRADE: (C.LUXURIES,),
        J.CLERGY: (C.INCENSE, C.SACRED_GOODS),
        J.SCHOLARSHIP: (C.MAGICAL_REAGENTS,),
        J.BUILDING: (C.TIMBER, C.SIEGE_MATERIEL),
        J.SOLDIERING: (),
        J.IDLE: (),
    }
)

MOVABLE_JOBS: frozenset[Job] = frozenset({J.FARMING, J.HERDING, J.FISHING, J.MINING, J.CRAFTING, J.TRADE, J.BUILDING})

WORKSHOP_JOBS: Mapping[WorkshopKind, Job] = MappingProxyType(
    {
        W.MARKET: J.TRADE,
        W.GRANARY: J.TRADE,
        W.WAREHOUSE: J.TRADE,
        W.MINE: J.MINING,
        W.LUMBER_CAMP: J.BUILDING,
        W.FISHERY: J.FISHING,
        W.CHARCOAL_KILN: J.CRAFTING,
        W.FORGE: J.CRAFTING,
        W.TANNERY: J.CRAFTING,
        W.MILL: J.FARMING,
        W.BREWERY: J.CRAFTING,
        W.WEAVERY: J.CRAFTING,
        W.STABLE: J.HERDING,
        W.MASON_YARD: J.MINING,
        W.SHIPYARD: J.BUILDING,
        W.SIEGE_YARD: J.BUILDING,
        W.ALCHEMIST: J.SCHOLARSHIP,
        W.SHRINE_WORKSHOP: J.CLERGY,
        W.MINT: J.TRADE,
    }
)

GATED_JOBS: Mapping[Job, tuple[Job, frozenset[WorkshopKind]]] = MappingProxyType(
    {
        J.MINING: (J.BUILDING, frozenset({W.MINE, W.MASON_YARD})),
        J.FISHING: (J.FARMING, frozenset({W.FISHERY, W.SHIPYARD})),
    }
)


def basket_weight(effect: ShortfallEffect, social_class: SocialClass) -> int:
    return EFFECT_BASKET[effect].get(social_class, AVERAGE)
