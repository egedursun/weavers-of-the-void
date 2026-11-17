from aerona.catalog.kinds.labels import GOOD_CATEGORY_LABELS, METHOD_LABELS
from aerona.db.kind_concepts.spec import ConceptSpec, KindProperty
from aerona.db.tables.cuisine import FLAVOURS
from aerona.db.tables.food_kinds import CuisineRow
from aerona.domain.enums.kinds import GoodCategory, KindConcept

SPEC = ConceptSpec(
    concept=KindConcept.CUISINE,
    label="Cuisine",
    plural="Cuisines",
    hint="A people's way of eating: its staple, its signature method, its taste, its manners at table",
    table=CuisineRow,
    category=GoodCategory,
    category_labels=GOOD_CATEGORY_LABELS,
    properties=(
        KindProperty("signature_method", "Signature method", "The way of cooking it is known for", options=METHOD_LABELS),
        KindProperty("taboo_category", "Shunned food", "A kind of food its eaters will not touch", options=GOOD_CATEGORY_LABELS),
        KindProperty("etiquette", "Manners at table", "How strict its rules of eating are; breaches cost standing"),
        KindProperty("meals_per_day", "Meals a day", "How many meals its eaters take", 1, 8),
        KindProperty("feasting", "Feasting", "How often and how richly it feasts; feasts calm and cost"),
        *(KindProperty(flavour, flavour.capitalize(), "The mean taste of its dishes") for flavour in FLAVOURS),
    ),
    readers=("kinds", "cuisine", "markets", "kitchens"),
)
