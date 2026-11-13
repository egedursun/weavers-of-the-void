from aerona.domain.enums.economy import CommodityKind

C = CommodityKind
DISH_FOODS = (C.GRAIN, C.TUBERS, C.FRUIT, C.MEAT, C.FISH, C.MILK, C.CHEESE, C.EGGS, C.HERBS, C.BREW_BASE, C.BREAD)
STAPLE_FOODS = frozenset({C.GRAIN, C.TUBERS, C.BREAD})
