from collections.abc import Mapping

from aerona.core.total import total
from aerona.domain.enums.economy import CommodityKind, WorkshopKind
from aerona.domain.enums.goods_traits import CommodityTrait, MaterialTrait, WorkshopTrait
from aerona.domain.enums.material import MaterialKind

C = CommodityKind
M = MaterialKind
W = WorkshopKind

COMMODITY_TRAITS: Mapping[CommodityKind, frozenset[CommodityTrait]] = total(
    CommodityKind,
    {
        C.GRAIN: frozenset({CommodityTrait.FOOD_STARCH, CommodityTrait.HOARD, CommodityTrait.RENEWABLE, CommodityTrait.STAPLE, CommodityTrait.STORED_GRAIN}),
        C.LIVESTOCK: frozenset({CommodityTrait.FOOD_PROTEIN, CommodityTrait.HOARD, CommodityTrait.RENEWABLE, CommodityTrait.STAPLE}),
        C.FISH: frozenset({CommodityTrait.FOOD_MINERAL, CommodityTrait.FOOD_PROTEIN, CommodityTrait.RENEWABLE, CommodityTrait.STAPLE}),
        C.FODDER: frozenset({CommodityTrait.RENEWABLE}),
        C.TIMBER: frozenset({CommodityTrait.RAW_MATERIAL, CommodityTrait.RENEWABLE, CommodityTrait.WOODY}),
        C.FUEL: frozenset({CommodityTrait.HEAT_STOCK, CommodityTrait.WOODY}),
        C.BREAD: frozenset({CommodityTrait.FOOD_STARCH}),
        C.ORE: frozenset({CommodityTrait.DUG, CommodityTrait.RAW_MATERIAL}),
        C.STONE: frozenset({CommodityTrait.DUG, CommodityTrait.RAW_MATERIAL}),
        C.CLOTH: frozenset({CommodityTrait.CIVILIAN}),
        C.TOOLS: frozenset(),
        C.WEAPONS: frozenset({CommodityTrait.WAR_GOOD}),
        C.ARMOUR: frozenset({CommodityTrait.WAR_GOOD}),
        C.MOUNTS: frozenset({CommodityTrait.RENEWABLE}),
        C.SIEGE_MATERIEL: frozenset({CommodityTrait.WAR_GOOD}),
        C.MEDICINE: frozenset({CommodityTrait.HEALING}),
        C.LUXURIES: frozenset({CommodityTrait.CASH_CROP, CommodityTrait.CIVILIAN, CommodityTrait.FOOD_SPECIAL, CommodityTrait.HOARD}),
        C.INCENSE: frozenset({CommodityTrait.CASH_CROP, CommodityTrait.CIVILIAN, CommodityTrait.OFFERING, CommodityTrait.RENEWABLE}),
        C.SACRED_GOODS: frozenset({CommodityTrait.OFFERING}),
        C.MAGICAL_REAGENTS: frozenset({CommodityTrait.FOOD_SPECIAL, CommodityTrait.RENEWABLE}),
        C.MEAT: frozenset({CommodityTrait.FOOD_PROTEIN}),
        C.MILK: frozenset({CommodityTrait.FOOD_FAT}),
        C.CHEESE: frozenset({CommodityTrait.FOOD_FAT, CommodityTrait.KEEPING}),
        C.FRUIT: frozenset({CommodityTrait.FOOD_FRESH, CommodityTrait.KEEPING}),
        C.TUBERS: frozenset({CommodityTrait.FOOD_STARCH, CommodityTrait.STORED_GRAIN}),
        C.COAL: frozenset({CommodityTrait.DUG, CommodityTrait.HEAT_STOCK}),
        C.PEAT: frozenset({CommodityTrait.HEAT_STOCK}),
        C.DUNG: frozenset(),
        C.FIBRE: frozenset({CommodityTrait.CASH_CROP}),
        C.DYE: frozenset({CommodityTrait.CASH_CROP}),
        C.HERBS: frozenset({CommodityTrait.CASH_CROP, CommodityTrait.FOOD_FRESH, CommodityTrait.FOOD_MINERAL, CommodityTrait.HEALING, CommodityTrait.KEEPING}),
        C.BREW_BASE: frozenset(),
        C.POISON: frozenset(),
        C.EGGS: frozenset({CommodityTrait.FOOD_PROTEIN}),
        C.WOOL: frozenset(),
        C.OIL: frozenset({CommodityTrait.CASH_CROP, CommodityTrait.FOOD_FAT, CommodityTrait.KEEPING}),
        C.SUGAR: frozenset({CommodityTrait.CASH_CROP, CommodityTrait.FOOD_SPECIAL, CommodityTrait.KEEPING}),
        C.SPICE: frozenset({CommodityTrait.CASH_CROP, CommodityTrait.FOOD_SPECIAL, CommodityTrait.KEEPING, CommodityTrait.HOARD}),
        C.HALITE: frozenset({CommodityTrait.DUG, CommodityTrait.FOOD_MINERAL, CommodityTrait.KEEPING, CommodityTrait.RAW_MATERIAL}),
        C.HONEY: frozenset({CommodityTrait.FOOD_SPECIAL, CommodityTrait.KEEPING, CommodityTrait.RENEWABLE}),
        C.WAX: frozenset({CommodityTrait.RAW_MATERIAL, CommodityTrait.RENEWABLE}),
        C.POTTERY: frozenset({CommodityTrait.CIVILIAN}),
        C.BOOKS: frozenset({CommodityTrait.CIVILIAN, CommodityTrait.HOARD}),
    },
)

MATERIAL_TRAITS: Mapping[MaterialKind, frozenset[MaterialTrait]] = total(
    MaterialKind,
    {
        M.WOOD: frozenset({MaterialTrait.COMMON, MaterialTrait.FEVER}),
        M.CALCIFIED_TISSUE: frozenset({MaterialTrait.COMMON}),
        M.HIDE: frozenset({MaterialTrait.COMMON, MaterialTrait.ORGANIC_CLOTH}),
        M.LEATHER: frozenset({MaterialTrait.ORGANIC_CLOTH}),
        M.CLOTH: frozenset({MaterialTrait.COMMON, MaterialTrait.ORGANIC_CLOTH}),
        M.STONE: frozenset(
            {
                MaterialTrait.COMMON,
                MaterialTrait.CONSTRUCT_BODY,
                MaterialTrait.FEVER,
                MaterialTrait.MINERAL,
                MaterialTrait.STONE_KIND,
                MaterialTrait.STONE_SEAM,
                MaterialTrait.STONY,
            }
        ),
        M.FLINT: frozenset({MaterialTrait.MINERAL, MaterialTrait.STONE_KIND, MaterialTrait.STONE_SEAM}),
        M.OBSIDIAN: frozenset({MaterialTrait.MINERAL, MaterialTrait.RARE_SEAM, MaterialTrait.STONE_KIND}),
        M.COPPER: frozenset({MaterialTrait.METAL_SEAM, MaterialTrait.MINERAL}),
        M.TIN: frozenset({MaterialTrait.METAL_SEAM, MaterialTrait.MINERAL}),
        M.BRONZE: frozenset({MaterialTrait.CONSTRUCT_BODY, MaterialTrait.FEVER}),
        M.IRON: frozenset({MaterialTrait.CONSTRUCT_BODY, MaterialTrait.FEVER, MaterialTrait.METAL_SEAM, MaterialTrait.MINERAL, MaterialTrait.STRATEGIC}),
        M.STEEL: frozenset({MaterialTrait.CONSTRUCT_BODY}),
        M.SILVER: frozenset({MaterialTrait.FEVER, MaterialTrait.METAL_SEAM, MaterialTrait.MINERAL, MaterialTrait.PRECIOUS, MaterialTrait.RESERVE}),
        M.GOLD: frozenset({MaterialTrait.FEVER, MaterialTrait.METAL_SEAM, MaterialTrait.MINERAL, MaterialTrait.PRECIOUS, MaterialTrait.RESERVE}),
        M.GLASS: frozenset({MaterialTrait.FEVER}),
        M.CRYSTAL: frozenset({MaterialTrait.MINERAL, MaterialTrait.PRECIOUS, MaterialTrait.RARE_SEAM}),
        M.IVORY: frozenset(),
        M.CHITIN: frozenset(),
        M.GREAT_BEAST_TISSUE: frozenset({MaterialTrait.PRECIOUS, MaterialTrait.STRATEGIC}),
        M.STAR_METAL: frozenset({MaterialTrait.MINERAL, MaterialTrait.PRECIOUS, MaterialTrait.STRATEGIC}),
        M.VOID_GLASS: frozenset({MaterialTrait.MINERAL, MaterialTrait.RARE_SEAM}),
        M.DIVINE_TISSUE: frozenset(),
        M.LIVING_WOOD: frozenset(),
        M.HALITE: frozenset({MaterialTrait.MINERAL}),
        M.AMBER: frozenset({MaterialTrait.MINERAL}),
        M.LEAD: frozenset({MaterialTrait.METAL_SEAM, MaterialTrait.MINERAL}),
        M.SKYSTEEL: frozenset({MaterialTrait.PRECIOUS, MaterialTrait.STRATEGIC}),
        M.SULFUR: frozenset({MaterialTrait.MINERAL}),
        M.CLAY: frozenset(
            {MaterialTrait.COMMON, MaterialTrait.CONSTRUCT_BODY, MaterialTrait.MINERAL, MaterialTrait.STONE_KIND, MaterialTrait.STONE_SEAM, MaterialTrait.STONY}
        ),
        M.GEMS: frozenset({MaterialTrait.MINERAL, MaterialTrait.RARE_SEAM}),
        M.MUD_BRICK: frozenset({MaterialTrait.COMMON}),
        M.FIRED_BRICK: frozenset(),
        M.DRESSED_STONE: frozenset(),
        M.RUBBLE: frozenset({MaterialTrait.COMMON}),
        M.LIME_MORTAR: frozenset(),
        M.HYDRAULIC_CONCRETE: frozenset(),
        M.THATCH: frozenset({MaterialTrait.COMMON}),
        M.TILE: frozenset(),
        M.CERAMIC: frozenset({MaterialTrait.COMMON}),
        M.SILK: frozenset({MaterialTrait.ORGANIC_CLOTH, MaterialTrait.PRECIOUS}),
        M.RESIN: frozenset({MaterialTrait.COMMON}),
        M.SHELL: frozenset({MaterialTrait.PRECIOUS}),
        M.POLYMER: frozenset({MaterialTrait.CONSTRUCT_BODY}),
        M.COMPOSITE: frozenset({MaterialTrait.CONSTRUCT_BODY, MaterialTrait.STRATEGIC}),
    },
)

WORKSHOP_TRAITS: Mapping[WorkshopKind, frozenset[WorkshopTrait]] = total(
    WorkshopKind,
    {
        W.MARKET: frozenset({WorkshopTrait.CART_WORKS, WorkshopTrait.TRADING}),
        W.GRANARY: frozenset({WorkshopTrait.CELLAR, WorkshopTrait.MILLING}),
        W.WAREHOUSE: frozenset({WorkshopTrait.CELLAR, WorkshopTrait.TRADING}),
        W.MINE: frozenset(),
        W.LUMBER_CAMP: frozenset({WorkshopTrait.CART_WORKS}),
        W.FISHERY: frozenset(),
        W.CHARCOAL_KILN: frozenset({WorkshopTrait.SMELTING}),
        W.FORGE: frozenset({WorkshopTrait.SMELTING}),
        W.TANNERY: frozenset(),
        W.MILL: frozenset({WorkshopTrait.MILLING}),
        W.BREWERY: frozenset(),
        W.WEAVERY: frozenset(),
        W.STABLE: frozenset({WorkshopTrait.CART_WORKS}),
        W.MASON_YARD: frozenset(),
        W.SHIPYARD: frozenset(),
        W.SIEGE_YARD: frozenset(),
        W.ALCHEMIST: frozenset(),
        W.SHRINE_WORKSHOP: frozenset(),
        W.MINT: frozenset(),
        W.POTTERY: frozenset({WorkshopTrait.SMELTING}),
        W.GLASSWORKS: frozenset({WorkshopTrait.SMELTING}),
        W.DYEWORKS: frozenset(),
        W.SCRIPTORIUM: frozenset(),
        W.EVAPORATION_WORKS: frozenset({WorkshopTrait.CELLAR}),
    },
)


def commodities_with(trait: CommodityTrait) -> tuple[CommodityKind, ...]:
    return tuple(kind for kind, traits in COMMODITY_TRAITS.items() if trait in traits)


def materials_with(trait: MaterialTrait) -> tuple[MaterialKind, ...]:
    return tuple(kind for kind, traits in MATERIAL_TRAITS.items() if trait in traits)


def workshops_with(trait: WorkshopTrait) -> tuple[WorkshopKind, ...]:
    return tuple(kind for kind, traits in WORKSHOP_TRAITS.items() if trait in traits)
