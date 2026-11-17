from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.living import Fertility, LineTrait, Metabolism

FERTILITY = total(
    Fertility,
    {
        Fertility.STERILE: Defined(
            "Sterile",
            checked_by=("engine.living.blessing.bless_line", "engine.living.profiles.breed"),
            used_by=("engine.living.backfill.alive", "engine.living.lines.make_line", "engine.living.production.seed_dues"),
        ),
        Fertility.BREEDS_TRUE: Defined(
            "Breeds true",
            checked_by=(),
            used_by=(
                "db.tables.living.LivingLineRow",
                "db.tables.living.LivingProfileRow",
                "engine.living.backfill.bred_lines",
                "engine.living.backfill.bred_species_lines",
                "engine.living.blessing.bless_line",
                "engine.living.control.give_life",
                "engine.living.lines.LineDraft",
                "services.player.living.LineCreate",
                "tools.mortal.living.DesignLineInput",
            ),
        ),
        Fertility.BREEDS_WILD: Defined("Breeds wild", checked_by=("engine.living.profiles.breed",), used_by=("engine.living.lines.drift",)),
        Fertility.NEEDS_MAKER: Defined("Needs its maker", checked_by=("engine.living.profiles.breed",), used_by=("engine.living.production.seed_dues",)),
    },
)

LINE_TRAIT = total(
    LineTrait,
    {
        LineTrait.YIELD: Defined("Yield", checked_by=(), used_by=("engine.agrarian.lands.grow", "engine.living.world.SHAPING_TRAITS")),
        LineTrait.HARDINESS: Defined(
            "Hardiness",
            checked_by=(),
            used_by=(
                "catalog.genetic_effects.LOCUS_EFFECTS",
                "engine.agrarian.lands.grow",
                "engine.living.profiles.live",
                "engine.living.world.SHAPING_TRAITS",
            ),
        ),
        LineTrait.CLIMATE_TOLERANCE: Defined(
            "Climate tolerance", checked_by=(), used_by=("catalog.genetic_effects.LOCUS_EFFECTS", "engine.living.world.SHAPING_TRAITS")
        ),
        LineTrait.DISEASE_RESISTANCE: Defined(
            "Disease resistance", checked_by=(), used_by=("catalog.genetic_effects.LOCUS_EFFECTS", "engine.living.production.blight_monocultures")
        ),
        LineTrait.STRENGTH: Defined("Strength", checked_by=("engine.living.grown.grow_gear",), used_by=("catalog.genetic_effects.LOCUS_EFFECTS",)),
        LineTrait.SPEED: Defined("Speed", checked_by=(), used_by=("catalog.genetic_effects.LOCUS_EFFECTS",)),
        LineTrait.SIZE: Defined("Size", checked_by=(), used_by=("catalog.genetic_effects.LOCUS_EFFECTS", "engine.living.profiles.live")),
        LineTrait.REGENERATION: Defined("Regeneration", checked_by=(), used_by=("catalog.genetic_effects.LOCUS_EFFECTS", "engine.living.control.give_life")),
        LineTrait.LIFESPAN: Defined("Lifespan", checked_by=(), used_by=("catalog.genetic_effects.LOCUS_EFFECTS", "engine.living.control.give_life")),
        LineTrait.DOCILITY: Defined(
            "Docility", checked_by=(), used_by=("catalog.genetic_effects.LOCUS_EFFECTS", "engine.living.control.give_life", "engine.living.profiles.live")
        ),
        LineTrait.POTENCY: Defined("Potency", checked_by=(), used_by=("engine.living.disease.design_cure",)),
        LineTrait.FIBRE: Defined("Fibre", checked_by=(), used_by=()),
        LineTrait.VENOM: Defined("Venom", checked_by=(), used_by=()),
        LineTrait.FLIGHT: Defined("Flight", checked_by=(), used_by=("engine.living.lines.SPREADING",)),
        LineTrait.AQUATIC: Defined("Living in water", checked_by=(), used_by=("catalog.genetic_effects.LOCUS_EFFECTS", "engine.living.lines.SPREADING")),
        LineTrait.VOID_HARDY: Defined("Hardy in the void", checked_by=(), used_by=("engine.living.lines.SPREADING",)),
        LineTrait.GIFT: Defined("A gift of power", checked_by=(), used_by=("catalog.genetic_effects.GIFT", "engine.living.control.give_life")),
        LineTrait.NERVOUS_SYSTEM: Defined(
            "Nervous system",
            checked_by=("engine.living.grown.raise_sapience",),
            used_by=("catalog.genetic_effects.LOCUS_EFFECTS", "engine.living.control.give_life"),
        ),
        LineTrait.SAPIENCE: Defined(
            "Thought",
            checked_by=("engine.living.grown.raise_sapience", "engine.living.profiles.mutate", "engine.living.world.designed_sapience"),
            used_by=("catalog.genetic_effects.LOCUS_EFFECTS", "engine.living.grown.raise_sapience"),
        ),
    },
)

METABOLISM = total(
    Metabolism,
    {
        Metabolism.FEEDING: Defined(
            "Eats food",
            checked_by=("engine.living.backfill.alive", "engine.living.control.FEED_OF", "services.integrity.living_links.mend_living_links"),
            used_by=(
                "db.tables.living.LivingLineRow",
                "db.tables.living.LivingProfileRow",
                "engine.living.backfill.bioships",
                "engine.living.grown.found_living_works",
                "engine.living.grown.grow_vessel",
                "services.player.living.LifeGive",
            ),
        ),
        Metabolism.LIGHT: Defined(
            "Lives on light",
            checked_by=(),
            used_by=("engine.living.backfill.grown_works", "engine.living.grown.grow_structure", "engine.living.profiles.SELF_FED"),
        ),
        Metabolism.CHEMICAL: Defined(
            "Lives on minerals", checked_by=("engine.living.control.FEED_OF", "services.integrity.living_links.mend_living_links"), used_by=()
        ),
        Metabolism.HOST: Defined("Draws on its host", checked_by=("engine.living.profiles.fed",), used_by=("engine.living.grown.grow_gear",)),
        Metabolism.SOURCE: Defined("Draws on a source", checked_by=(), used_by=("engine.living.profiles.SELF_FED",)),
        Metabolism.PARTNER: Defined("Fed by a partner", checked_by=(), used_by=("engine.living.profiles.SELF_FED",)),
        Metabolism.DORMANT: Defined("Dormant", checked_by=("engine.living.profiles.fed", "engine.living.profiles.live"), used_by=()),
    },
)
