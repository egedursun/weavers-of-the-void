from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.ecology import AttackRange, Aversion, Cultivation, Habitat, HerdTraining, RangeTrend, SpeciesClass, Temperament, TissueMaterial

ATTACK_RANGE = total(
    AttackRange,
    {
        AttackRange.TOUCH: Defined("Touch", checked_by=(), used_by=("engine.ecology.anatomy.attack_specs",)),
        AttackRange.NEAR: Defined(
            "Near",
            checked_by=(),
            used_by=(
                "catalog.creature_anatomy.TRAIT_ATTACKS",
                "db.tables.anatomy.CreatureAttackRow",
                "engine.ecology.anatomy.attack_specs",
                "services.player.typed_models.AttackMake",
                "tools.son.creation.shape_beast",
            ),
        ),
        AttackRange.FAR: Defined("A whole town", checked_by=(), used_by=("engine.ecology.anatomy.attack_specs", "engine.ecology.beast_acts.WHOLE_TOWN")),
        AttackRange.SIGHT: Defined(
            "By sight, a whole town",
            checked_by=("engine.ecology.beast_acts.sight_scale",),
            used_by=("engine.ecology.anatomy.attack_specs", "engine.ecology.beast_acts.WHOLE_TOWN"),
        ),
    },
)

AVERSION = total(
    Aversion,
    {
        Aversion.FIRE: Defined("Fire", checked_by=("engine.ecology.anatomy.repelled",), used_by=()),
        Aversion.IRON: Defined("Iron", checked_by=("engine.ecology.anatomy.repelled",), used_by=()),
        Aversion.NOISE: Defined("Noise", checked_by=("engine.ecology.anatomy.repelled",), used_by=()),
        Aversion.WATER: Defined("Water", checked_by=("engine.ecology.anatomy.repelled",), used_by=()),
        Aversion.HOLY_GROUND: Defined("Holy ground", checked_by=(), used_by=()),
    },
)

CULTIVATION = total(
    Cultivation,
    {
        Cultivation.WILD: Defined("Wild", checked_by=("engine.ecology.flora.gather_wild",), used_by=("db.tables.flora.PlantProfileRow",)),
        Cultivation.GATHERED: Defined("Gathered", checked_by=("engine.ecology.flora.gather_wild",), used_by=("engine.ecology.flora.gather_wild",)),
        Cultivation.CULTIVATED: Defined(
            "Cultivated", checked_by=("engine.ecology.flora.breed_cultivars",), used_by=("engine.ecology.flora.gather_wild", "tools.son.flora.sow_crop")
        ),
        Cultivation.CULTIVAR: Defined("Cultivar", checked_by=(), used_by=("engine.ecology.flora.breed_cultivar",)),
    },
)

HABITAT = total(
    Habitat,
    {
        Habitat.LAND: Defined("Land", checked_by=(), used_by=("db.tables.anatomy.CreatureAnatomyRow", "engine.ecology.anatomy.habitat_of")),
        Habitat.WATER: Defined("Water", checked_by=(), used_by=("engine.ecology.anatomy.habitat_of",)),
        Habitat.SKY: Defined("Sky", checked_by=(), used_by=("engine.ecology.anatomy.habitat_of",)),
        Habitat.DEEP: Defined("Deep", checked_by=(), used_by=("engine.ecology.anatomy.habitat_of",)),
        Habitat.VOID: Defined(
            "Void",
            checked_by=("engine.cosmos.routes.has_beast_mount", "engine.ecology.beast_acts.void_trophy", "engine.ecology.monsters.roam_void"),
            used_by=("engine.ecology.anatomy.habitat_of",),
        ),
    },
)

HERD_TRAINING = total(
    HerdTraining,
    {
        HerdTraining.WAR: Defined("War", checked_by=(), used_by=("engine.ecology.domestication.training_for", "engine.military.units.composition")),
        HerdTraining.HUNTING: Defined("Hunting", checked_by=("engine.ecology.ranges.load_wilds",), used_by=("engine.ecology.domestication.training_for",)),
        HerdTraining.GUARD: Defined("Guard", checked_by=(), used_by=("engine.ecology.domestication.guarded", "engine.ecology.domestication.training_for")),
    },
)

RANGE_TREND = total(
    RangeTrend,
    {
        RangeTrend.RISING: Defined(
            "Rising",
            checked_by=(),
            used_by=(
                "engine.ecology.control.edit_range",
                "engine.ecology.ranges.migrate",
                "engine.ecology.ranges.settle",
                "engine.ecology.ranges.spread",
                "engine.living.lines.run_wild",
                "engine.plants.bodies.spread",
                "engine.protected_nature.species.reintroduce",
                "tools.mortal.fossils.revive",
            ),
        ),
        RangeTrend.STEADY: Defined(
            "Steady",
            checked_by=(),
            used_by=(
                "db.tables.ecology.SpeciesRangeRow",
                "engine.ecology.control.create_species",
                "engine.ecology.ranges.adapt_subspecies",
                "engine.ecology.ranges.seed",
                "engine.ecology.ranges.settle",
            ),
        ),
        RangeTrend.FALLING: Defined("Falling", checked_by=(), used_by=("engine.ecology.ranges.settle",)),
    },
)

SPECIES_CLASS = total(
    SpeciesClass,
    {
        SpeciesClass.ANIMAL: Defined(
            "Animal",
            checked_by=("engine.ecology.flora.flora_backfill",),
            used_by=(
                "db.tables.ecology.SpeciesProfileRow",
                "engine.ecology.profiles.Nature",
                "engine.ecology.profiles.class_of",
                "engine.folk_knowledge.truth.ROAMING",
                "engine.museums.gardens.PLANTED",
            ),
        ),
        SpeciesClass.PLANT: Defined(
            "Plant",
            checked_by=("catalog.flora.DEFAULT_YIELDS", "engine.ecology.profiles.PLANT_DIETS", "engine.ecology.profiles.PLANT_PLANS"),
            used_by=(
                "engine.ecology.flora.reclass_plant",
                "engine.ecology.profiles.class_of",
                "engine.museums.gardens.planting",
                "engine.plants.bodies.PLANT_CLASSES",
            ),
        ),
        SpeciesClass.FUNGUS: Defined(
            "Fungus",
            checked_by=(
                "catalog.flora.DEFAULT_YIELDS",
                "engine.ecology.profiles.PLANT_DIETS",
                "engine.ecology.profiles.PLANT_PLANS",
                "engine.plants.bodies.CLASS_FORMS",
            ),
            used_by=("engine.museums.gardens.planting", "engine.plants.bodies.PLANT_CLASSES"),
        ),
        SpeciesClass.VERMIN: Defined(
            "Vermin",
            checked_by=(
                "agents.context.wilds.plant_lines",
                "engine.ecology.flora.pest_ids",
                "engine.ecology.pests.pest_traits",
                "engine.industry.stores.vermin_in",
            ),
            used_by=("engine.ecology.flora.flora_backfill", "engine.ecology.profiles.class_of", "engine.folk_knowledge.truth.ROAMING"),
        ),
        SpeciesClass.MICROBE: Defined("Microbe", checked_by=(), used_by=()),
        SpeciesClass.MINERAL: Defined("Mineral", checked_by=(), used_by=()),
        SpeciesClass.GASEOUS: Defined("Gaseous", checked_by=(), used_by=()),
        SpeciesClass.ENERGY: Defined("Energy", checked_by=(), used_by=()),
        SpeciesClass.MADE: Defined("Made", checked_by=(), used_by=()),
        SpeciesClass.COLONIAL: Defined("Colonial", checked_by=("engine.plants.bodies.CLASS_FORMS",), used_by=("engine.plants.bodies.PLANT_CLASSES",)),
        SpeciesClass.HYBRID: Defined("Hybrid", checked_by=(), used_by=()),
    },
)

TEMPERAMENT = total(
    Temperament,
    {
        Temperament.PLACID: Defined(
            "Placid",
            checked_by=(),
            used_by=(
                "db.tables.anatomy.CreatureAnatomyRow",
                "engine.ecology.anatomy.TEMPERAMENTS",
                "engine.living.backfill.bioships",
                "engine.living.control.give_life",
            ),
        ),
        Temperament.SKITTISH: Defined("Skittish", checked_by=(), used_by=("engine.ecology.anatomy.TEMPERAMENTS", "engine.ecology.anatomy.temperament_of")),
        Temperament.CURIOUS: Defined("Curious", checked_by=(), used_by=("engine.ecology.anatomy.TEMPERAMENTS", "engine.living.control.give_life")),
        Temperament.FIERCE: Defined("Fierce", checked_by=(), used_by=("engine.ecology.anatomy.TEMPERAMENTS", "engine.ecology.anatomy.temperament_of")),
        Temperament.CUNNING: Defined("Cunning", checked_by=(), used_by=("engine.ecology.anatomy.TEMPERAMENTS",)),
        Temperament.SEIZES_PREY: Defined("Seizes prey", checked_by=("engine.ecology.beast_acts.is_abductor",), used_by=("engine.ecology.anatomy.generate",)),
    },
)

TISSUE_MATERIAL = total(
    TissueMaterial,
    {
        TissueMaterial.SOFT_TISSUE: Defined("Soft tissue", checked_by=(), used_by=("catalog.creature_anatomy.PLAN_SKIN", "catalog.creature_anatomy.TISSUES")),
        TissueMaterial.HIDE: Defined(
            "Hide", checked_by=(), used_by=("catalog.creature_anatomy.PLAN_SKIN", "catalog.creature_anatomy.TISSUES", "db.tables.anatomy.CreatureAnatomyRow")
        ),
        TissueMaterial.PLATES: Defined(
            "Plates", checked_by=(), used_by=("catalog.creature_anatomy.PLAN_SKIN", "catalog.creature_anatomy.TISSUES", "catalog.creature_anatomy.TRAIT_SKIN")
        ),
        TissueMaterial.SHELL: Defined("Shell", checked_by=(), used_by=("catalog.creature_anatomy.PLAN_SKIN", "catalog.creature_anatomy.TISSUES")),
        TissueMaterial.PLUMAGE: Defined("Plumage", checked_by=(), used_by=("catalog.creature_anatomy.PLAN_SKIN", "catalog.creature_anatomy.TISSUES")),
        TissueMaterial.RIGID: Defined(
            "Rigid", checked_by=(), used_by=("catalog.creature_anatomy.TISSUES", "db.tables.anatomy.CreatureAnatomyRow", "engine.ecology.anatomy.generate")
        ),
        TissueMaterial.FIBROUS: Defined(
            "Fibrous", checked_by=(), used_by=("catalog.biology.BIOLOGY_VARIANTS", "catalog.creature_anatomy.PLAN_SKIN", "catalog.creature_anatomy.TISSUES")
        ),
        TissueMaterial.FROZEN: Defined("Frozen", checked_by=(), used_by=("catalog.creature_anatomy.LIFE_SKIN", "catalog.creature_anatomy.TISSUES")),
        TissueMaterial.VAPOUR: Defined("Vapour", checked_by=(), used_by=("catalog.creature_anatomy.EXOTIC_TISSUES", "catalog.creature_anatomy.TISSUES")),
        TissueMaterial.MINERAL: Defined(
            "Mineral",
            checked_by=(),
            used_by=(
                "catalog.creature_anatomy.LIFE_SKIN",
                "catalog.creature_anatomy.PLAN_SKIN",
                "catalog.creature_anatomy.TISSUES",
                "catalog.creature_anatomy.TRAIT_SKIN",
                "engine.ecology.anatomy.BONE_OF",
            ),
        ),
        TissueMaterial.METALLIC: Defined(
            "Metallic", checked_by=(), used_by=("catalog.creature_anatomy.EXOTIC_TISSUES", "catalog.creature_anatomy.TISSUES", "engine.ecology.anatomy.BONE_OF")
        ),
        TissueMaterial.CRYSTALLINE: Defined(
            "Crystalline",
            checked_by=(),
            used_by=(
                "catalog.biology.BIOLOGY_VARIANTS",
                "catalog.creature_anatomy.EXOTIC_TISSUES",
                "catalog.creature_anatomy.LIFE_SKIN",
                "catalog.creature_anatomy.TISSUES",
                "engine.ecology.anatomy.BONE_OF",
            ),
        ),
        TissueMaterial.GEL: Defined("Gel", checked_by=(), used_by=("catalog.creature_anatomy.EXOTIC_TISSUES", "catalog.creature_anatomy.TISSUES")),
        TissueMaterial.ENERGY: Defined("Energy", checked_by=(), used_by=("catalog.creature_anatomy.EXOTIC_TISSUES", "catalog.creature_anatomy.TISSUES")),
        TissueMaterial.INSUBSTANTIAL: Defined(
            "Insubstantial",
            checked_by=(),
            used_by=("catalog.creature_anatomy.LIFE_SKIN", "catalog.creature_anatomy.PLAN_SKIN", "catalog.creature_anatomy.TISSUES"),
        ),
    },
)
