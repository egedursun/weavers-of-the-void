from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.kinds import KindAct, KindConcept, MealSlot

KIND_ACT = total(
    KindAct,
    {
        KindAct.MAKE: Defined("Make", checked_by=("tools.son.kinds.shape_kind",), used_by=()),
        KindAct.BLESS: Defined("Bless", checked_by=("tools.son.kinds.shape_kind",), used_by=()),
        KindAct.FORBID: Defined("Forbid", checked_by=(), used_by=()),
    },
)

KIND_CONCEPT = total(
    KindConcept,
    {
        KindConcept.GOOD: Defined("Good", checked_by=("engine.kinds.derive.TIES",), used_by=("db.kind_concepts.goods.SPEC", "engine.kinds.legacy.goods_held")),
        KindConcept.DISH: Defined(
            "Dish",
            checked_by=("engine.cuisine.dishes.adopt_held", "engine.cuisine.dishes.hold_dish", "engine.cuisine.legacy.makers_hold"),
            used_by=(
                "db.kind_concepts.dishes.SPEC",
                "engine.cuisine.dishes.hold_dish",
                "engine.cuisine.legacy.makers_hold",
                "engine.kinds.derive.OWN_DERIVATION",
                "engine.kinds.legacy.dishes_held",
            ),
        ),
        KindConcept.DRINK: Defined(
            "Drink",
            checked_by=("engine.cuisine.drinks.drink_safety", "engine.cuisine.drinks.holdings_of", "engine.cuisine.drinks.share_hospitality"),
            used_by=("db.kind_concepts.drinks.SPEC", "engine.cuisine.drinks.found_drink", "engine.kinds.derive.OWN_DERIVATION"),
        ),
        KindConcept.CUISINE: Defined(
            "Cuisine",
            checked_by=("engine.cuisine.cuisines.fuse", "engine.cuisine.dishes.cuisine_of"),
            used_by=(
                "db.kind_concepts.cuisines.SPEC",
                "engine.cuisine.cuisines.hold_cuisine",
                "engine.kinds.derive.OWN_DERIVATION",
                "services.kind_map.MAPPED_CONCEPTS",
            ),
        ),
        KindConcept.GARMENT: Defined(
            "Garment",
            checked_by=(
                "engine.body.systems.ways_past",
                "engine.kinds.crafts_life.EFFECTS",
                "engine.kinds.crafts_life.exposure_of",
                "engine.kinds.crafts_life.garment_fashion",
            ),
            used_by=(
                "db.kind_concepts.crafts.GARMENT",
                "engine.kinds.crafts_life.exposure_of",
                "engine.kinds.crafts_life.restraints",
                "engine.kinds.legacy.ITEM_KINDS",
                "services.kind_map.MAPPED_CONCEPTS",
            ),
        ),
        KindConcept.COLOUR_TERM: Defined(
            "Colour term",
            checked_by=("engine.kinds.crafts_life.EFFECTS", "engine.kinds.crafts_life.repeal_colour"),
            used_by=(
                "db.kind_concepts.crafts.COLOUR",
                "engine.kinds.crafts_life.colour_laws",
                "engine.kinds.crafts_life.held_meanings",
                "engine.kinds.crafts_life.restraints",
                "engine.kinds.crafts_life.restrict_colour",
            ),
        ),
        KindConcept.SCENT: Defined("Scent", checked_by=("engine.kinds.crafts_life.EFFECTS",), used_by=("db.kind_concepts.crafts.SCENT",)),
        KindConcept.EMBLEM_SYSTEM: Defined(
            "Emblem system",
            checked_by=("engine.kinds.crafts_life.EFFECTS", "engine.kinds.crafts_life.link_arms"),
            used_by=("db.kind_concepts.crafts.EMBLEM", "engine.kinds.crafts_life.link_arms"),
        ),
        KindConcept.FURNISHING: Defined(
            "Furnishing",
            checked_by=("engine.kinds.crafts_life.EFFECTS", "engine.kinds.crafts_life.furnishing_worth"),
            used_by=("db.kind_concepts.crafts.FURNISHING", "engine.kinds.legacy.ITEM_KINDS"),
        ),
        KindConcept.TOOL: Defined(
            "Tool",
            checked_by=("engine.kinds.crafts_life.EFFECTS", "engine.kinds.crafts_life.exposure_of"),
            used_by=("db.kind_concepts.crafts.TOOL", "engine.kinds.crafts_life.exposure_of", "engine.kinds.legacy.ITEM_KINDS"),
        ),
        KindConcept.INSTRUMENT: Defined(
            "Instrument", checked_by=("engine.kinds.crafts_life.EFFECTS",), used_by=("db.kind_concepts.crafts.INSTRUMENT", "engine.kinds.legacy.ITEM_KINDS")
        ),
        KindConcept.MUSIC_TRADITION: Defined("Music tradition", checked_by=("engine.kinds.crafts_life.EFFECTS",), used_by=("db.kind_concepts.crafts.MUSIC",)),
        KindConcept.GAME: Defined(
            "Game",
            checked_by=(
                "agents.context.crafts_lines.people_lines",
                "engine.arts.sport.field_game",
                "engine.belonging.peers.play_of",
                "engine.crafts.games.played_games",
            ),
            used_by=("db.kind_concepts.crafts.GAME", "engine.crafts.games.made_by", "engine.kinds.crafts_life.exposure_of"),
        ),
        KindConcept.SUBSTANCE: Defined(
            "Substance",
            checked_by=("engine.kinds.crafts_life.EFFECTS",),
            used_by=("db.kind_concepts.crafts.SUBSTANCE", "engine.kinds.crafts_life.restraints", "engine.kinds.legacy.ITEM_KINDS"),
        ),
        KindConcept.PROFESSION: Defined(
            "Profession",
            checked_by=(),
            used_by=(
                "db.kind_concepts.society.PROFESSION_SPEC",
                "engine.kinds.professions.profession_kind",
                "engine.kinds.society.earnings",
                "engine.kinds.society.work_mishaps",
            ),
        ),
        KindConcept.RANK: Defined(
            "Rank", checked_by=(), used_by=("db.kind_concepts.society.RANK_SPEC", "engine.kinds.legacy.ranks_held", "engine.kinds.society.rank_effects")
        ),
        KindConcept.ORGANISATION: Defined(
            "Organisation",
            checked_by=(),
            used_by=(
                "db.kind_concepts.society.ORGANISATION_SPEC",
                "engine.kinds.legacy.organisations_held",
                "engine.kinds.society.organisation_kind_for",
                "engine.kinds.society.organisation_of",
                "services.kind_map.MAPPED_CONCEPTS",
            ),
        ),
        KindConcept.DWELLING: Defined(
            "Dwelling", checked_by=("engine.households.dwelling_kinds.dwelling_of_people",), used_by=("db.kind_concepts.dwellings.SPEC",)
        ),
        KindConcept.PRODUCTION_METHOD: Defined("Production method", checked_by=(), used_by=("db.kind_concepts.nature.METHOD_SPEC",)),
        KindConcept.DIVINE_OFFICE: Defined("Divine office", checked_by=(), used_by=("db.kind_concepts.nature.OFFICE_SPEC",)),
        KindConcept.REALM: Defined("Realm", checked_by=(), used_by=("db.kind_concepts.nature.REALM_SPEC",)),
        KindConcept.TRAIT: Defined(
            "Trait", checked_by=("engine.kinds.nature.keep_traits",), used_by=("db.kind_concepts.nature.TRAIT_SPEC", "engine.kinds.nature.legacy_traits")
        ),
        KindConcept.TENET: Defined(
            "Tenet",
            checked_by=("engine.kinds.culture_life.keep_culture_kinds",),
            used_by=("db.kind_concepts.culture.TENET_SPEC", "engine.kinds.culture_life.hold_tenets"),
        ),
        KindConcept.FEAR: Defined("Fear", checked_by=(), used_by=("db.kind_concepts.culture.FEAR_SPEC", "engine.kinds.culture_life.fears_held")),
        KindConcept.DREAM_READING: Defined(
            "Dream reading",
            checked_by=(),
            used_by=("db.kind_concepts.culture.READING_SPEC", "engine.kinds.culture_life.reading_kind_for", "engine.sacred.mysteries.dream_read"),
        ),
        KindConcept.AIM: Defined("Aim", checked_by=(), used_by=("db.kind_concepts.culture.AIM_SPEC", "engine.kinds.culture_life.aims_held")),
    },
)

MEAL_SLOT = total(
    MealSlot,
    {
        MealSlot.DAILY_MEAL: Defined("Daily meal", checked_by=(), used_by=("catalog.life.cuisine.COURSE_SLOTS", "db.tables.cuisine.DishRow")),
        MealSlot.SNACK: Defined("Snack", checked_by=(), used_by=("catalog.life.cuisine.COURSE_SLOTS",)),
        MealSlot.FEAST: Defined("Feast", checked_by=(), used_by=("catalog.life.cuisine.COURSE_SLOTS",)),
        MealSlot.RITE: Defined("Rite", checked_by=(), used_by=("catalog.life.cuisine.COURSE_SLOTS",)),
        MealSlot.RATION: Defined("Ration", checked_by=(), used_by=("catalog.life.cuisine.COURSE_SLOTS",)),
        MealSlot.REMEDY: Defined("Remedy", checked_by=(), used_by=("catalog.life.cuisine.COURSE_SLOTS",)),
        MealSlot.TRAVEL_FOOD: Defined("Travel food", checked_by=(), used_by=()),
        MealSlot.FAMINE_FOOD: Defined("Famine food", checked_by=(), used_by=()),
        MealSlot.STREET: Defined("Street food", checked_by=(), used_by=()),
    },
)
