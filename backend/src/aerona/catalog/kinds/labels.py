from collections.abc import Mapping
from enum import StrEnum

from aerona.core.grammar import spoken
from aerona.core.total import total
from aerona.domain.enums.cuisine import CookingMethod
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.kinds import DrinkCategory, DrinkRole, GoodCategory, GoodLegality, GoodSource, GoodTaxClass, IngredientRole, MealSlot
from aerona.domain.enums.urban import CargoClass


def plain[E: StrEnum](kind: type[E], table: Mapping[E, str]) -> dict[str, str]:
    return {member.value: label for member, label in total(kind, table).items()}


def spoken_labels[E: StrEnum](kind: type[E]) -> dict[str, str]:
    return plain(kind, {member: spoken(member).capitalize() for member in kind})


GOOD_CATEGORY_LABELS = spoken_labels(GoodCategory)
GOOD_SOURCE_LABELS = plain(
    GoodSource,
    {
        GoodSource.SPECIES: "A living species",
        GoodSource.MATERIAL: "A material",
        GoodSource.DEPOSIT: "A deposit",
        GoodSource.METHOD: "A method of production",
        GoodSource.MAKING: "Making by hand or machine",
    },
)
TAX_CLASS_LABELS = spoken_labels(GoodTaxClass)
LEGALITY_LABELS = spoken_labels(GoodLegality)
COMMODITY_LABELS = spoken_labels(CommodityKind)
CARGO_LABELS = spoken_labels(CargoClass)
METHOD_LABELS = spoken_labels(CookingMethod)
MEAL_SLOT_LABELS = spoken_labels(MealSlot)
DRINK_CATEGORY_LABELS = spoken_labels(DrinkCategory)
DRINK_ROLE_LABELS = spoken_labels(DrinkRole)
ROLE_LABELS = spoken_labels(IngredientRole)
