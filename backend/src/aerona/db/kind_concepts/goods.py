from aerona.catalog.kinds.labels import CARGO_LABELS, COMMODITY_LABELS, GOOD_CATEGORY_LABELS, GOOD_SOURCE_LABELS, LEGALITY_LABELS, TAX_CLASS_LABELS
from aerona.db.kind_concepts.spec import ConceptSpec, KindProperty
from aerona.db.tables.kinds import GoodKindRow
from aerona.domain.enums.kinds import GoodCategory, KindConcept

SPEC = ConceptSpec(
    concept=KindConcept.GOOD,
    label="Good",
    plural="Goods",
    hint="Things a people grows, gathers, makes or trades",
    table=GoodKindRow,
    category=GoodCategory,
    category_labels=GOOD_CATEGORY_LABELS,
    properties=(
        KindProperty("perishability", "Keeps for", "Seasons before it spoils in a store; 0 never spoils", 0, 40),
        KindProperty("bulk", "Bulk", "Room it takes in a store or a hold; bulky goods cost more to carry by land"),
        KindProperty("base_value", "Base value", "Worth of one lot before supply and demand move its price", 0, 1000),
        KindProperty("nourishment", "Nourishment", "How much it feeds those who eat it; read by the dishes made from it"),
        KindProperty("prestige", "Prestige", "Standing it lends to those who hold it; raises demand among the wealthy and how fast it spreads"),
        KindProperty("sacred", "Sacredness", "Weight it carries in rites and offerings; raises demand among the pious"),
        KindProperty("taboo", "Taboo", "How strongly its holders shun it; lowers demand in their markets"),
        KindProperty("stocked_as", "Stocked as", "The store of goods it is counted in", options=COMMODITY_LABELS),
        KindProperty("source", "Source", "Where it comes from", options=GOOD_SOURCE_LABELS),
        KindProperty("cargo_class", "Cargo", "How it travels and what it loses on the way", options=CARGO_LABELS),
        KindProperty("tax_class", "Tax class", "The rate at which tariffs fall on it", options=TAX_CLASS_LABELS),
        KindProperty("legality", "Legality", "Whether markets may sell it freely", options=LEGALITY_LABELS),
    ),
    readers=("kinds", "markets", "stores", "routes", "cuisine"),
)
