from collections.abc import Callable, Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.ecology import YieldProduct
from aerona.rules.registry import Rules


@dataclass(frozen=True)
class BeastProductSpec:
    worth: Callable[[Rules], int]
    share: Callable[[Rules], int]


BEAST_PRODUCTS: Mapping[YieldProduct, BeastProductSpec] = total(
    YieldProduct,
    {
        YieldProduct.MEAT: BeastProductSpec(lambda rules: rules.beast_products.meat_value, lambda rules: rules.beast_products.meat_yield),
        YieldProduct.HIDE: BeastProductSpec(lambda rules: rules.beast_products.hide_value, lambda rules: rules.beast_products.hide_yield),
        YieldProduct.CALCIFIED_TISSUE: BeastProductSpec(
            lambda rules: rules.beast_products.calcified_tissue_value, lambda rules: rules.beast_products.calcified_tissue_yield
        ),
        YieldProduct.IVORY: BeastProductSpec(lambda rules: rules.beast_products.ivory_value, lambda rules: rules.beast_products.ivory_yield),
        YieldProduct.CHITIN: BeastProductSpec(lambda rules: rules.beast_products.chitin_value, lambda rules: rules.beast_products.chitin_yield),
        YieldProduct.VENOM: BeastProductSpec(lambda rules: rules.beast_products.venom_value, lambda rules: rules.beast_products.venom_yield),
        YieldProduct.SILK: BeastProductSpec(lambda rules: rules.beast_products.silk_value, lambda rules: rules.beast_products.silk_yield),
        YieldProduct.WOOL: BeastProductSpec(lambda rules: rules.beast_products.wool_value, lambda rules: rules.beast_products.wool_yield),
        YieldProduct.MILK: BeastProductSpec(lambda rules: rules.beast_products.milk_value, lambda rules: rules.beast_products.milk_yield),
        YieldProduct.FEATHERS: BeastProductSpec(lambda rules: rules.beast_products.feathers_value, lambda rules: rules.beast_products.feathers_yield),
        YieldProduct.MAGIC_REAGENTS: BeastProductSpec(
            lambda rules: rules.beast_products.magic_reagents_value, lambda rules: rules.beast_products.magic_reagents_yield
        ),
        YieldProduct.GREAT_BEAST_TISSUE: BeastProductSpec(
            lambda rules: rules.beast_products.great_beast_tissue_value, lambda rules: rules.beast_products.great_beast_tissue_yield
        ),
        YieldProduct.EGGS: BeastProductSpec(lambda rules: rules.beast_products.eggs_value, lambda rules: rules.beast_products.eggs_yield),
        YieldProduct.BLOOD: BeastProductSpec(lambda rules: rules.beast_products.blood_value, lambda rules: rules.beast_products.blood_yield),
        YieldProduct.ORGANS: BeastProductSpec(lambda rules: rules.beast_products.organs_value, lambda rules: rules.beast_products.organs_yield),
        YieldProduct.FAT: BeastProductSpec(lambda rules: rules.beast_products.fat_value, lambda rules: rules.beast_products.fat_yield),
        YieldProduct.SCENT: BeastProductSpec(lambda rules: rules.beast_products.scent_value, lambda rules: rules.beast_products.scent_yield),
        YieldProduct.HONEY: BeastProductSpec(lambda rules: rules.beast_products.honey_value, lambda rules: rules.beast_products.honey_yield),
        YieldProduct.WAX: BeastProductSpec(lambda rules: rules.beast_products.wax_value, lambda rules: rules.beast_products.wax_yield),
        YieldProduct.SHELL: BeastProductSpec(lambda rules: rules.beast_products.shell_value, lambda rules: rules.beast_products.shell_yield),
        YieldProduct.SCALES: BeastProductSpec(lambda rules: rules.beast_products.scales_value, lambda rules: rules.beast_products.scales_yield),
    },
)
BY_PRODUCT_NAME: Mapping[str, YieldProduct] = {**{item.value: item for item in YieldProduct}, "magic reagents": YieldProduct.MAGIC_REAGENTS}
