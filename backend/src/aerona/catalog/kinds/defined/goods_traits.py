from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.goods_traits import CommodityTrait, MaterialTrait, WorkshopTrait

COMMODITY_TRAIT = total(
    CommodityTrait,
    {
        CommodityTrait.CASH_CROP: Defined("Cash crop", checked_by=(), used_by=("catalog.goods_traits.COMMODITY_TRAITS", "engine.agrarian.lands.CASH_CROPS")),
        CommodityTrait.HEAT_STOCK: Defined(
            "Heat stock", checked_by=(), used_by=("catalog.goods_traits.COMMODITY_TRAITS", "engine.cosmos.world_views.HEAT_STOCKS")
        ),
        CommodityTrait.OFFERING: Defined(
            "Offering", checked_by=(), used_by=("catalog.goods_traits.COMMODITY_TRAITS", "engine.cosmos.world_views.OFFERING_STOCKS")
        ),
        CommodityTrait.STAPLE: Defined(
            "Staple", checked_by=(), used_by=("catalog.goods_traits.COMMODITY_TRAITS", "engine.demography.peoples.STAPLE_FOODS", "engine.faith.doctrine.FOODS")
        ),
        CommodityTrait.HOARD: Defined("Hoard", checked_by=(), used_by=("catalog.goods_traits.COMMODITY_TRAITS", "engine.ecology.beasts.HOARD_GOODS")),
        CommodityTrait.DUG: Defined(
            "Dug", checked_by=(), used_by=("catalog.goods_traits.COMMODITY_TRAITS", "engine.economy.extraction.ORE_LIKE", "engine.urban.cityscape.DEEP")
        ),
        CommodityTrait.RAW_MATERIAL: Defined(
            "Raw material",
            checked_by=(),
            used_by=("catalog.goods_traits.COMMODITY_TRAITS", "engine.economy.resources.RAW_MATERIALS", "engine.economy.survey.RAW_MATERIALS"),
        ),
        CommodityTrait.HEALING: Defined(
            "Healing", checked_by=(), used_by=("catalog.goods_traits.COMMODITY_TRAITS", "engine.folk_knowledge.truth.HEALING_GOODS")
        ),
        CommodityTrait.KEEPING: Defined("Keeping", checked_by=(), used_by=("catalog.goods_traits.COMMODITY_TRAITS", "engine.folkways.fed.KEEPING_FOODS")),
        CommodityTrait.STORED_GRAIN: Defined(
            "Stored grain", checked_by=(), used_by=("catalog.goods_traits.COMMODITY_TRAITS", "engine.industry.stores.STORED_GRAINS")
        ),
        CommodityTrait.WAR_GOOD: Defined("War good", checked_by=(), used_by=("catalog.goods_traits.COMMODITY_TRAITS", "engine.military.war_lines.WAR_GOODS")),
        CommodityTrait.CIVILIAN: Defined(
            "Civilian", checked_by=(), used_by=("catalog.goods_traits.COMMODITY_TRAITS", "engine.military.war_lines.CIVILIAN_GOODS")
        ),
        CommodityTrait.WOODY: Defined(
            "Woody", checked_by=(), used_by=("catalog.goods_traits.COMMODITY_TRAITS", "engine.economy.household.WOODY", "engine.urban.cityscape.WOODS")
        ),
        CommodityTrait.RENEWABLE: Defined("Renewable", checked_by=(), used_by=("catalog.goods_traits.COMMODITY_TRAITS", "engine.economy.resources.RENEWABLE")),
        CommodityTrait.FOOD_STARCH: Defined(
            "Food starch", checked_by=(), used_by=("catalog.goods_traits.COMMODITY_TRAITS", "engine.folkways.nutrition.GROUPS")
        ),
        CommodityTrait.FOOD_PROTEIN: Defined(
            "Food protein", checked_by=(), used_by=("catalog.goods_traits.COMMODITY_TRAITS", "engine.folkways.nutrition.GROUPS")
        ),
        CommodityTrait.FOOD_FAT: Defined("Food fat", checked_by=(), used_by=("catalog.goods_traits.COMMODITY_TRAITS", "engine.folkways.nutrition.GROUPS")),
        CommodityTrait.FOOD_FRESH: Defined("Food fresh", checked_by=(), used_by=("catalog.goods_traits.COMMODITY_TRAITS", "engine.folkways.nutrition.GROUPS")),
        CommodityTrait.FOOD_MINERAL: Defined(
            "Food mineral", checked_by=(), used_by=("catalog.goods_traits.COMMODITY_TRAITS", "engine.folkways.nutrition.GROUPS")
        ),
        CommodityTrait.FOOD_SPECIAL: Defined(
            "Food special", checked_by=(), used_by=("catalog.goods_traits.COMMODITY_TRAITS", "engine.folkways.nutrition.SPECIAL")
        ),
    },
)

MATERIAL_TRAIT = total(
    MaterialTrait,
    {
        MaterialTrait.MINERAL: Defined(
            "Mineral",
            checked_by=(),
            used_by=(
                "catalog.commodities.COMMODITIES",
                "catalog.goods_traits.MATERIAL_TRAITS",
                "engine.economy.resources.MINERALS",
                "engine.economy.survey.MINERALS",
            ),
        ),
        MaterialTrait.PRECIOUS: Defined("Precious", checked_by=(), used_by=("catalog.goods_traits.MATERIAL_TRAITS", "engine.body.healing.PRECIOUS")),
        MaterialTrait.METAL_SEAM: Defined(
            "Metal seam", checked_by=(), used_by=("catalog.goods_traits.MATERIAL_TRAITS", "engine.environment.profile.METAL_SEAMS")
        ),
        MaterialTrait.STONE_SEAM: Defined(
            "Stone seam", checked_by=(), used_by=("catalog.goods_traits.MATERIAL_TRAITS", "engine.environment.profile.STONE_SEAMS")
        ),
        MaterialTrait.RARE_SEAM: Defined("Rare seam", checked_by=(), used_by=("catalog.goods_traits.MATERIAL_TRAITS", "engine.environment.profile.RARE_SEAMS")),
        MaterialTrait.RESERVE: Defined("Reserve", checked_by=(), used_by=("catalog.goods_traits.MATERIAL_TRAITS", "engine.finance.credit.RESERVE_METALS")),
        MaterialTrait.ORGANIC_CLOTH: Defined(
            "Organic cloth", checked_by=(), used_by=("catalog.goods_traits.MATERIAL_TRAITS", "engine.lore.items.ORGANIC_CLOTH")
        ),
        MaterialTrait.STRATEGIC: Defined(
            "Strategic", checked_by=(), used_by=("catalog.goods_traits.MATERIAL_TRAITS", "engine.phases.trade.STRATEGIC_MATERIALS")
        ),
        MaterialTrait.STONY: Defined("Stony", checked_by=(), used_by=("catalog.goods_traits.MATERIAL_TRAITS", "engine.economy.survey.STONY")),
        MaterialTrait.STONE_KIND: Defined(
            "Stone kind", checked_by=(), used_by=("catalog.goods_traits.MATERIAL_TRAITS", "engine.economy.resources.STONE_KINDS")
        ),
        MaterialTrait.COMMON: Defined("Common", checked_by=(), used_by=("catalog.goods_traits.MATERIAL_TRAITS", "engine.economy.provenance.COMMON")),
        MaterialTrait.FEVER: Defined("Fever", checked_by=(), used_by=("catalog.goods_traits.MATERIAL_TRAITS", "engine.mind.inspiration.FEVER_MATERIALS")),
        MaterialTrait.CONSTRUCT_BODY: Defined(
            "Construct body", checked_by=(), used_by=("catalog.goods_traits.MATERIAL_TRAITS", "engine.constructs.making.BODIES")
        ),
    },
)

WORKSHOP_TRAIT = total(
    WorkshopTrait,
    {
        WorkshopTrait.SMELTING: Defined("Smelting", checked_by=(), used_by=("catalog.goods_traits.WORKSHOP_TRAITS", "engine.economy.survey.wanted_workshops")),
        WorkshopTrait.MILLING: Defined("Milling", checked_by=(), used_by=("catalog.goods_traits.WORKSHOP_TRAITS", "engine.economy.survey.wanted_workshops")),
        WorkshopTrait.TRADING: Defined("Trading", checked_by=(), used_by=("catalog.goods_traits.WORKSHOP_TRAITS", "engine.economy.survey.wanted_workshops")),
        WorkshopTrait.CELLAR: Defined(
            "Cellar",
            checked_by=(),
            used_by=(
                "catalog.goods_traits.WORKSHOP_TRAITS",
                "engine.industry.methods.CELLARS",
                "engine.settlement.life.store_up",
                "engine.settlement.readout.plan_readout",
            ),
        ),
        WorkshopTrait.CART_WORKS: Defined(
            "Cart works", checked_by=(), used_by=("catalog.goods_traits.WORKSHOP_TRAITS", "engine.vehicles.production.CART_WORKS")
        ),
    },
)
