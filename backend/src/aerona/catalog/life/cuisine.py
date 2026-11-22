from types import MappingProxyType

from aerona.core.total import total
from aerona.domain.enums.cuisine import CookingMethod, DishCourse
from aerona.domain.enums.kinds import DrinkCategory, GoodCategory, IngredientRole, MealSlot
from aerona.domain.enums.society import KnowledgeBranch

METHOD_GATES: MappingProxyType[CookingMethod, tuple[KnowledgeBranch | None, int]] = total(
    CookingMethod,
    {
        CookingMethod.RAW: (None, 0),
        CookingMethod.BOILED: (None, 0),
        CookingMethod.STEWED: (None, 0),
        CookingMethod.STEAMED: (KnowledgeBranch.AGRICULTURE, 1),
        CookingMethod.ROASTED: (None, 0),
        CookingMethod.GRILLED: (None, 0),
        CookingMethod.BAKED: (KnowledgeBranch.AGRICULTURE, 1),
        CookingMethod.FRIED: (KnowledgeBranch.AGRICULTURE, 2),
        CookingMethod.SMOKED: (None, 0),
        CookingMethod.DRIED: (None, 0),
        CookingMethod.CURED: (KnowledgeBranch.TRADE, 1),
        CookingMethod.PICKLED: (KnowledgeBranch.TRADE, 1),
        CookingMethod.FERMENTED: (KnowledgeBranch.AGRICULTURE, 1),
        CookingMethod.BRAISED: (KnowledgeBranch.AGRICULTURE, 2),
        CookingMethod.SIMMERED: (None, 0),
        CookingMethod.GROUND: (KnowledgeBranch.AGRICULTURE, 1),
        CookingMethod.PRESSED: (KnowledgeBranch.AGRICULTURE, 2),
        CookingMethod.CONJURED: (KnowledgeBranch.MAGIC, 1),
        CookingMethod.FREEZE_DRIED: (KnowledgeBranch.AGRICULTURE, 5),
        CookingMethod.IRRADIATED: (KnowledgeBranch.METALLURGY, 7),
        CookingMethod.PRINTED: (KnowledgeBranch.METALLURGY, 7),
        CookingMethod.SYNTHESISED: (KnowledgeBranch.MEDICINE, 6),
        CookingMethod.VAT_GROWN: (KnowledgeBranch.BIOMANCY, 1),
        CookingMethod.INFUSED: (None, 0),
        CookingMethod.DISTILLED: (KnowledgeBranch.MEDICINE, 2),
        CookingMethod.CHURNED: (None, 0),
        CookingMethod.SPROUTED: (KnowledgeBranch.AGRICULTURE, 1),
        CookingMethod.ALKALI_TREATED: (KnowledgeBranch.AGRICULTURE, 2),
        CookingMethod.CULTURED: (KnowledgeBranch.AGRICULTURE, 2),
        CookingMethod.CURED_WITH_MINERAL: (KnowledgeBranch.TRADE, 1),
        CookingMethod.AGED: (KnowledgeBranch.AGRICULTURE, 1),
        CookingMethod.EXTRUDED: (KnowledgeBranch.METALLURGY, 6),
        CookingMethod.PRESSURE_COOKED: (KnowledgeBranch.METALLURGY, 5),
    },
)


METHOD_KEEPS: MappingProxyType[CookingMethod, int] = total(
    CookingMethod,
    {
        CookingMethod.RAW: 0,
        CookingMethod.BOILED: 0,
        CookingMethod.STEWED: 0,
        CookingMethod.STEAMED: 0,
        CookingMethod.ROASTED: 1,
        CookingMethod.GRILLED: 0,
        CookingMethod.BAKED: 1,
        CookingMethod.FRIED: 0,
        CookingMethod.SMOKED: 3,
        CookingMethod.DRIED: 4,
        CookingMethod.CURED: 4,
        CookingMethod.PICKLED: 3,
        CookingMethod.FERMENTED: 3,
        CookingMethod.BRAISED: 0,
        CookingMethod.SIMMERED: 0,
        CookingMethod.GROUND: 2,
        CookingMethod.PRESSED: 2,
        CookingMethod.CONJURED: 0,
        CookingMethod.FREEZE_DRIED: 6,
        CookingMethod.IRRADIATED: 6,
        CookingMethod.PRINTED: 3,
        CookingMethod.SYNTHESISED: 5,
        CookingMethod.VAT_GROWN: 3,
        CookingMethod.INFUSED: 0,
        CookingMethod.DISTILLED: 6,
        CookingMethod.CHURNED: 1,
        CookingMethod.SPROUTED: 0,
        CookingMethod.ALKALI_TREATED: 2,
        CookingMethod.CULTURED: 3,
        CookingMethod.CURED_WITH_MINERAL: 4,
        CookingMethod.AGED: 5,
        CookingMethod.EXTRUDED: 3,
        CookingMethod.PRESSURE_COOKED: 0,
    },
)


COURSE_LABELS: MappingProxyType[DishCourse, str] = total(
    DishCourse,
    {
        DishCourse.STAPLE: "Dish",
        DishCourse.SIDE: "Side dish",
        DishCourse.FESTIVE: "Feast dish",
        DishCourse.RITE: "Rite dish",
        DishCourse.RATION: "Ration",
        DishCourse.DELICACY: "Delicacy",
        DishCourse.REMEDY: "Remedy",
        DishCourse.DRINK: "Drink",
    },
)


COURSE_SLOTS: MappingProxyType[DishCourse, MealSlot] = total(
    DishCourse,
    {
        DishCourse.STAPLE: MealSlot.DAILY_MEAL,
        DishCourse.SIDE: MealSlot.DAILY_MEAL,
        DishCourse.FESTIVE: MealSlot.FEAST,
        DishCourse.RITE: MealSlot.RITE,
        DishCourse.RATION: MealSlot.RATION,
        DishCourse.DELICACY: MealSlot.SNACK,
        DishCourse.REMEDY: MealSlot.REMEDY,
        DishCourse.DRINK: MealSlot.DAILY_MEAL,
    },
)


CATEGORY_ROLES: MappingProxyType[GoodCategory, IngredientRole] = total(
    GoodCategory,
    {
        GoodCategory.GRAIN: IngredientRole.BASE,
        GoodCategory.ROOT_AND_TUBER: IngredientRole.BASE,
        GoodCategory.VEGETABLE: IngredientRole.BASE,
        GoodCategory.LEGUME: IngredientRole.PROTEIN,
        GoodCategory.FRUIT: IngredientRole.GARNISH,
        GoodCategory.NUT_AND_SEED: IngredientRole.FAT,
        GoodCategory.OIL_AND_FAT: IngredientRole.FAT,
        GoodCategory.SWEETENER: IngredientRole.SEASONING,
        GoodCategory.SEASONING: IngredientRole.SEASONING,
        GoodCategory.MINERAL_SEASONING: IngredientRole.PRESERVATIVE,
        GoodCategory.MEAT: IngredientRole.PROTEIN,
        GoodCategory.FISH_AND_SEAFOOD: IngredientRole.PROTEIN,
        GoodCategory.DAIRY: IngredientRole.FAT,
        GoodCategory.EGGS: IngredientRole.BINDER,
        GoodCategory.INSECTS: IngredientRole.PROTEIN,
        GoodCategory.FUNGI: IngredientRole.BASE,
        GoodCategory.ALGAE: IngredientRole.BASE,
        GoodCategory.OFFAL_AND_BLOOD: IngredientRole.PROTEIN,
        GoodCategory.FODDER: IngredientRole.BASE,
        GoodCategory.DRINK_BASE: IngredientRole.LIQUID,
        GoodCategory.STIMULANT: IngredientRole.SEASONING,
        GoodCategory.INTOXICANT: IngredientRole.LIQUID,
        GoodCategory.MEDICINE: IngredientRole.SEASONING,
        GoodCategory.FIBRE: IngredientRole.BINDER,
        GoodCategory.TEXTILE: IngredientRole.BINDER,
        GoodCategory.HIDE_AND_LEATHER: IngredientRole.BINDER,
        GoodCategory.TIMBER: IngredientRole.BASE,
        GoodCategory.FUEL: IngredientRole.BASE,
        GoodCategory.ORE: IngredientRole.BASE,
        GoodCategory.METAL: IngredientRole.BASE,
        GoodCategory.STONE: IngredientRole.BASE,
        GoodCategory.CLAY_AND_CERAMIC: IngredientRole.BASE,
        GoodCategory.GLASS: IngredientRole.BASE,
        GoodCategory.CHEMICAL: IngredientRole.PRESERVATIVE,
        GoodCategory.DYE_AND_PIGMENT: IngredientRole.COLOURING,
        GoodCategory.SCENT_MATERIAL: IngredientRole.SEASONING,
        GoodCategory.REAGENT: IngredientRole.LEAVENING,
        GoodCategory.TOOLS: IngredientRole.BASE,
        GoodCategory.WEAPONS: IngredientRole.BASE,
        GoodCategory.ARMOUR: IngredientRole.BASE,
        GoodCategory.GARMENTS: IngredientRole.BASE,
        GoodCategory.FURNISHINGS: IngredientRole.BASE,
        GoodCategory.CONTAINERS: IngredientRole.BASE,
        GoodCategory.INSTRUMENTS: IngredientRole.BASE,
        GoodCategory.ORNAMENTS: IngredientRole.GARNISH,
        GoodCategory.BOOKS_AND_RECORDS: IngredientRole.BASE,
        GoodCategory.MACHINES: IngredientRole.BASE,
        GoodCategory.PARTS: IngredientRole.BASE,
        GoodCategory.ENERGY_STORE: IngredientRole.BASE,
        GoodCategory.DATA: IngredientRole.BASE,
        GoodCategory.LIVING_GOODS: IngredientRole.PROTEIN,
        GoodCategory.SACRED_GOODS: IngredientRole.GARNISH,
        GoodCategory.LUXURIES: IngredientRole.GARNISH,
        GoodCategory.LIVESTOCK: IngredientRole.PROTEIN,
        GoodCategory.MOUNTS: IngredientRole.PROTEIN,
    },
)


FIRST_COURSES = (
    DishCourse.STAPLE,
    DishCourse.DRINK,
    DishCourse.FESTIVE,
    DishCourse.SIDE,
    DishCourse.RITE,
    DishCourse.RATION,
    DishCourse.DELICACY,
    DishCourse.REMEDY,
)


CATEGORY_WORDS = total(
    DrinkCategory,
    {
        DrinkCategory.WATER: "Water",
        DrinkCategory.INFUSION: "Infusion",
        DrinkCategory.FERMENTED: "Brew",
        DrinkCategory.DISTILLED: "Spirit",
        DrinkCategory.PRESSED: "Juice",
        DrinkCategory.MILK_BASED: "Milk drink",
        DrinkCategory.BROTH: "Broth",
        DrinkCategory.STIMULANT_BREW: "Waking brew",
        DrinkCategory.INTOXICANT: "Strong drink",
        DrinkCategory.MEDICINAL: "Draught",
        DrinkCategory.RITUAL: "Rite drink",
        DrinkCategory.SYNTHESISED: "Made drink",
    },
)

DISH_TRAITS_DISH_COURSES = frozenset({DishCourse.DELICACY, DishCourse.FESTIVE})
INVENT_DISH_DISH_COURSES = (
    DishCourse.STAPLE,
    DishCourse.STAPLE,
    DishCourse.SIDE,
    DishCourse.FESTIVE,
    DishCourse.RITE,
    DishCourse.RATION,
    DishCourse.DELICACY,
    DishCourse.REMEDY,
    DishCourse.DRINK,
)
SAVOUR_DISH_COURSES = frozenset({DishCourse.STAPLE, DishCourse.SIDE, DishCourse.DRINK, DishCourse.FESTIVE})
SAVOUR_DISH_COURSES_2 = frozenset({DishCourse.DELICACY, DishCourse.FESTIVE})
SAVOUR_DISH_COURSES_3 = frozenset({DishCourse.STAPLE, DishCourse.REMEDY})
