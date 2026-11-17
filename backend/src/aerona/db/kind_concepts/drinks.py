from aerona.catalog.kinds.labels import DRINK_CATEGORY_LABELS, DRINK_ROLE_LABELS, LEGALITY_LABELS
from aerona.db.kind_concepts.spec import ConceptSpec, KindProperty
from aerona.db.tables.food_kinds import DrinkKindRow
from aerona.domain.enums.kinds import DrinkCategory, KindConcept

SPEC = ConceptSpec(
    concept=KindConcept.DRINK,
    label="Drink",
    plural="Drinks",
    hint="What a people drinks, daily, with guests, at feasts and in rites",
    table=DrinkKindRow,
    category=DrinkCategory,
    category_labels=DRINK_CATEGORY_LABELS,
    properties=(
        KindProperty("role", "Social role", "When and with whom it is drunk", options=DRINK_ROLE_LABELS),
        KindProperty("strength", "Strength", "How strongly it intoxicates; raises disorder where it is drunk"),
        KindProperty("stimulation", "Stimulation", "How much it wakes and drives those who drink it; raises the yield of work"),
        KindProperty("nourishment", "Nourishment", "How much it feeds"),
        KindProperty("water_safety", "Water safety", "How much safer it is than the water it is made from; lowers waterborne sickness"),
        KindProperty("keeps", "Keeps for", "Epochs it keeps", 0, 20),
        KindProperty("prestige", "Prestige", "Standing it lends to hosts; raises how fast it spreads"),
        KindProperty("dependence", "Dependence", "How readily its drinkers come to need it"),
        KindProperty("legality", "Legality", "Whether it may be sold freely", options=LEGALITY_LABELS),
    ),
    readers=("kinds", "drink", "epidemics", "settlements"),
)
