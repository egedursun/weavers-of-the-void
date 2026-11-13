from collections.abc import Mapping
from types import MappingProxyType

from aerona.core.total import total
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
        C.EGGS: E.HUNGER,
        C.WOOL: E.COLD,
        C.FIBRE: E.COLD,
        C.DYE: E.STATUS,
        C.HERBS: E.SICKNESS,
        C.BREW_BASE: E.STATUS,
        C.POISON: E.INSECURITY,
    }
)


EFFECT_BASKET: Mapping[ShortfallEffect, Mapping[SocialClass, int]] = MappingProxyType(
    {
        E.HUNGER: MappingProxyType({}),
        E.HERDS: MappingProxyType(
            {
                S.FARMER: 200,
                S.WARRIOR: 150,
                S.NOBLE: 120,
                S.SERF_OR_SLAVE: 80,
                S.OUTCAST: 10,
                S.WORKER: 60,
                S.PROFESSIONAL: 90,
                S.OFFICIAL: 100,
                S.CITIZEN: 80,
                S.UNEMPLOYED: 10,
            }
        ),
        E.COLD: MappingProxyType(
            {
                S.NOBLE: 180,
                S.MERCHANT: 140,
                S.SERF_OR_SLAVE: 70,
                S.OUTCAST: 50,
                S.WORKER: 70,
                S.PROFESSIONAL: 130,
                S.OFFICIAL: 140,
                S.CITIZEN: 100,
                S.UNEMPLOYED: 50,
            }
        ),
        E.SICKNESS: MappingProxyType(
            {
                S.NOBLE: 160,
                S.PRIEST: 120,
                S.MERCHANT: 120,
                S.OUTCAST: 40,
                S.SERF_OR_SLAVE: 50,
                S.WORKER: 60,
                S.PROFESSIONAL: 140,
                S.OFFICIAL: 120,
                S.CITIZEN: 90,
                S.UNEMPLOYED: 40,
            }
        ),
        E.IMPIETY: MappingProxyType(
            {
                S.PRIEST: 500,
                S.MONASTIC: 400,
                S.NOBLE: 160,
                S.MERCHANT: 90,
                S.SERF_OR_SLAVE: 40,
                S.OUTCAST: 20,
                S.WARRIOR: 70,
                S.FARMER: 70,
                S.WORKER: 50,
                S.PROFESSIONAL: 40,
                S.OFFICIAL: 60,
                S.CITIZEN: 60,
                S.UNEMPLOYED: 30,
            }
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
                S.WORKER: 20,
                S.PROFESSIONAL: 250,
                S.OFFICIAL: 300,
                S.CITIZEN: 80,
                S.UNEMPLOYED: 0,
            }
        ),
        E.TOIL: MappingProxyType(
            {
                S.ARTISAN: 400,
                S.FARMER: 120,
                S.SERF_OR_SLAVE: 90,
                S.MERCHANT: 40,
                S.PRIEST: 20,
                S.SCRIBE: 20,
                S.MONASTIC: 40,
                S.NOBLE: 30,
                S.OUTCAST: 20,
                S.WORKER: 450,
                S.PROFESSIONAL: 150,
                S.OFFICIAL: 30,
                S.CITIZEN: 120,
                S.UNEMPLOYED: 10,
            }
        ),
        E.INSECURITY: MappingProxyType(
            {
                S.WARRIOR: 600,
                S.NOBLE: 250,
                S.FARMER: 20,
                S.ARTISAN: 20,
                S.MERCHANT: 30,
                S.PRIEST: 10,
                S.SCRIBE: 10,
                S.MONASTIC: 10,
                S.SERF_OR_SLAVE: 0,
                S.WORKER: 20,
                S.PROFESSIONAL: 40,
                S.OFFICIAL: 120,
                S.CITIZEN: 40,
                S.UNEMPLOYED: 0,
            }
        ),
        E.ARCANE: MappingProxyType(
            {
                S.SCRIBE: 350,
                S.MONASTIC: 300,
                S.PRIEST: 150,
                S.NOBLE: 100,
                S.MERCHANT: 30,
                S.FARMER: 5,
                S.SERF_OR_SLAVE: 0,
                S.OUTCAST: 0,
                S.WORKER: 5,
                S.PROFESSIONAL: 200,
                S.OFFICIAL: 60,
                S.CITIZEN: 20,
                S.UNEMPLOYED: 0,
            }
        ),
    }
)

SERVE_ORDER: tuple[SocialClass, ...] = (
    S.NOBLE,
    S.OFFICIAL,
    S.PRIEST,
    S.MERCHANT,
    S.PROFESSIONAL,
    S.WARRIOR,
    S.SCRIBE,
    S.MONASTIC,
    S.CITIZEN,
    S.ARTISAN,
    S.WORKER,
    S.FARMER,
    S.SERF_OR_SLAVE,
    S.UNEMPLOYED,
    S.OUTCAST,
)

CLASS_INCOME: Mapping[SocialClass, int] = total(
    SocialClass,
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
        S.WORKER: 120,
        S.PROFESSIONAL: 350,
        S.OFFICIAL: 300,
        S.CITIZEN: 140,
        S.UNEMPLOYED: 15,
    },
)

JOB_GOODS: Mapping[Job, tuple[CommodityKind, ...]] = total(
    Job,
    {
        J.FARMING: (C.GRAIN, C.BREAD, C.FRUIT, C.TUBERS, C.FIBRE, C.DYE, C.HERBS, C.BREW_BASE, C.POISON),
        J.HERDING: (C.LIVESTOCK, C.FODDER, C.MOUNTS, C.MEAT, C.MILK, C.CHEESE, C.DUNG, C.EGGS, C.WOOL),
        J.FISHING: (C.FISH,),
        J.MINING: (C.ORE, C.STONE, C.COAL, C.PEAT),
        J.CRAFTING: (C.TOOLS, C.CLOTH, C.WEAPONS, C.ARMOUR, C.FUEL, C.MEDICINE),
        J.TRADE: (C.LUXURIES,),
        J.CLERGY: (C.INCENSE, C.SACRED_GOODS),
        J.SCHOLARSHIP: (C.MAGICAL_REAGENTS,),
        J.BUILDING: (C.TIMBER, C.SIEGE_MATERIEL),
        J.SOLDIERING: (),
        J.SERVICE: (),
        J.IDLE: (),
    },
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
