from collections.abc import Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.kinds import GoodCategory, GoodSource, GoodTaxClass

C = CommodityKind
G = GoodCategory
S = GoodSource
T = GoodTaxClass


@dataclass(frozen=True)
class BuiltInGood:
    category: GoodCategory
    source: GoodSource
    tax_class: GoodTaxClass
    perishability: int
    bulk: int
    prestige: int
    sacred: int


BUILT_IN_GOODS: Mapping[CommodityKind, BuiltInGood] = total(
    CommodityKind,
    {
        C.GRAIN: BuiltInGood(G.GRAIN, S.SPECIES, T.STAPLE, 8, 40, 5, 5),
        C.LIVESTOCK: BuiltInGood(G.LIVESTOCK, S.SPECIES, T.STAPLE, 0, 60, 15, 10),
        C.FISH: BuiltInGood(G.FISH_AND_SEAFOOD, S.SPECIES, T.STAPLE, 1, 30, 5, 0),
        C.FODDER: BuiltInGood(G.FODDER, S.SPECIES, T.STAPLE, 4, 50, 0, 0),
        C.TIMBER: BuiltInGood(G.TIMBER, S.SPECIES, T.ORDINARY, 0, 80, 5, 0),
        C.FUEL: BuiltInGood(G.FUEL, S.MATERIAL, T.STAPLE, 0, 50, 0, 0),
        C.BREAD: BuiltInGood(G.GRAIN, S.METHOD, T.STAPLE, 1, 20, 5, 10),
        C.ORE: BuiltInGood(G.ORE, S.DEPOSIT, T.STRATEGIC, 0, 90, 5, 0),
        C.STONE: BuiltInGood(G.STONE, S.DEPOSIT, T.ORDINARY, 0, 95, 5, 5),
        C.CLOTH: BuiltInGood(G.TEXTILE, S.METHOD, T.ORDINARY, 0, 20, 20, 5),
        C.TOOLS: BuiltInGood(G.TOOLS, S.MAKING, T.ORDINARY, 0, 30, 10, 0),
        C.WEAPONS: BuiltInGood(G.WEAPONS, S.MAKING, T.STRATEGIC, 0, 30, 25, 0),
        C.ARMOUR: BuiltInGood(G.ARMOUR, S.MAKING, T.STRATEGIC, 0, 40, 25, 0),
        C.MOUNTS: BuiltInGood(G.MOUNTS, S.SPECIES, T.STRATEGIC, 0, 70, 30, 5),
        C.SIEGE_MATERIEL: BuiltInGood(G.MACHINES, S.MAKING, T.STRATEGIC, 0, 90, 10, 0),
        C.MEDICINE: BuiltInGood(G.MEDICINE, S.METHOD, T.EXEMPT, 4, 10, 15, 10),
        C.LUXURIES: BuiltInGood(G.LUXURIES, S.MAKING, T.LUXURY, 0, 10, 70, 10),
        C.INCENSE: BuiltInGood(G.SCENT_MATERIAL, S.SPECIES, T.LUXURY, 0, 10, 30, 60),
        C.SACRED_GOODS: BuiltInGood(G.SACRED_GOODS, S.MAKING, T.EXEMPT, 0, 15, 40, 90),
        C.MAGICAL_REAGENTS: BuiltInGood(G.REAGENT, S.MATERIAL, T.LUXURY, 0, 10, 50, 40),
        C.MEAT: BuiltInGood(G.MEAT, S.SPECIES, T.STAPLE, 1, 30, 15, 5),
        C.MILK: BuiltInGood(G.DAIRY, S.SPECIES, T.STAPLE, 1, 30, 5, 5),
        C.CHEESE: BuiltInGood(G.DAIRY, S.METHOD, T.ORDINARY, 6, 20, 15, 0),
        C.FRUIT: BuiltInGood(G.FRUIT, S.SPECIES, T.STAPLE, 1, 25, 10, 5),
        C.TUBERS: BuiltInGood(G.ROOT_AND_TUBER, S.SPECIES, T.STAPLE, 6, 45, 0, 0),
        C.COAL: BuiltInGood(G.FUEL, S.DEPOSIT, T.STRATEGIC, 0, 90, 0, 0),
        C.PEAT: BuiltInGood(G.FUEL, S.DEPOSIT, T.STAPLE, 0, 80, 0, 0),
        C.DUNG: BuiltInGood(G.FUEL, S.SPECIES, T.EXEMPT, 0, 60, 0, 0),
        C.FIBRE: BuiltInGood(G.FIBRE, S.SPECIES, T.ORDINARY, 0, 40, 5, 0),
        C.DYE: BuiltInGood(G.DYE_AND_PIGMENT, S.SPECIES, T.LUXURY, 0, 10, 45, 10),
        C.HERBS: BuiltInGood(G.SEASONING, S.SPECIES, T.ORDINARY, 2, 10, 10, 20),
        C.BREW_BASE: BuiltInGood(G.DRINK_BASE, S.METHOD, T.ORDINARY, 4, 35, 10, 10),
        C.POISON: BuiltInGood(G.CHEMICAL, S.METHOD, T.STRATEGIC, 0, 5, 10, 0),
        C.EGGS: BuiltInGood(G.EGGS, S.SPECIES, T.STAPLE, 1, 20, 5, 5),
        C.WOOL: BuiltInGood(G.FIBRE, S.SPECIES, T.ORDINARY, 0, 40, 10, 0),
        C.OIL: BuiltInGood(G.OIL_AND_FAT, S.SPECIES, T.ORDINARY, 2, 30, 15, 15),
        C.SUGAR: BuiltInGood(G.SWEETENER, S.METHOD, T.LUXURY, 0, 20, 35, 5),
        C.SPICE: BuiltInGood(G.SEASONING, S.SPECIES, T.LUXURY, 1, 5, 55, 15),
        C.HALITE: BuiltInGood(G.MINERAL_SEASONING, S.DEPOSIT, T.STRATEGIC, 0, 40, 15, 10),
        C.HONEY: BuiltInGood(G.SWEETENER, S.SPECIES, T.ORDINARY, 0, 15, 25, 20),
        C.WAX: BuiltInGood(G.CHEMICAL, S.SPECIES, T.ORDINARY, 0, 15, 10, 20),
        C.POTTERY: BuiltInGood(G.CLAY_AND_CERAMIC, S.MAKING, T.ORDINARY, 0, 50, 10, 5),
        C.BOOKS: BuiltInGood(G.BOOKS_AND_RECORDS, S.MAKING, T.ORDINARY, 1, 15, 40, 20),
    },
)
