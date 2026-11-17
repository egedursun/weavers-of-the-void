from aerona.catalog.kinds.labels import MEAL_SLOT_LABELS, METHOD_LABELS
from aerona.db.kind_concepts.spec import ConceptSpec, KindProperty
from aerona.db.tables.cuisine import FLAVOURS, DishRow
from aerona.domain.enums.cuisine import DishCourse
from aerona.domain.enums.kinds import KindConcept, MealSlot

COURSE_OPTIONS = {course.value: course.value.capitalize() for course in DishCourse}
FLAVOUR_HINT = "How strongly the dish tastes of this, for those whose bodies can taste it"

SPEC = ConceptSpec(
    concept=KindConcept.DISH,
    label="Dish",
    plural="Dishes",
    hint="What a people cooks, by its steps, its ingredients and the meal it is eaten at",
    table=DishRow,
    category=MealSlot,
    category_labels=MEAL_SLOT_LABELS,
    properties=(
        KindProperty("method", "First method", "How the dish is first prepared; its first step", options=METHOD_LABELS),
        KindProperty("course", "Course", "Where the dish sits in a meal", options=COURSE_OPTIONS),
        KindProperty("nourishment", "Nourishment", "How much it feeds a household; raises prosperity where it is a staple"),
        KindProperty("delight", "Delight", "How much it pleases; calms unrest where it is eaten"),
        KindProperty("keeps", "Keeps for", "Epochs it keeps; long-keeping dishes become rations", 0, 20),
        KindProperty("prestige", "Prestige", "Standing it lends at feasts; raises how fast it spreads"),
        KindProperty("prep_skill", "Skill to make", "Cooking skill a kitchen needs before it can make the dish"),
        *(KindProperty(flavour, flavour.capitalize(), FLAVOUR_HINT) for flavour in FLAVOURS),
    ),
    readers=("kinds", "kitchens", "cuisine", "rations", "markets"),
)
