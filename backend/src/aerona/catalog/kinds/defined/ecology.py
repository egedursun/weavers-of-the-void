from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.ecology import Cultivation, Habitat, HerdTraining, RangeTrend, TissueMaterial

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
        Habitat.WATER: Defined("Water", checked_by=(), used_by=("engine.ecology.anatomy.HABITAT_TESTS",)),
        Habitat.SKY: Defined("Sky", checked_by=(), used_by=("engine.ecology.anatomy.HABITAT_TESTS",)),
        Habitat.DEEP: Defined("Deep", checked_by=(), used_by=("engine.ecology.anatomy.HABITAT_TESTS",)),
        Habitat.VOID: Defined(
            "Void",
            checked_by=("engine.cosmos.routes.has_beast_mount", "engine.ecology.beast_acts.void_trophy", "engine.ecology.monsters.roam_void"),
            used_by=("engine.ecology.anatomy.HABITAT_TESTS",),
        ),
        Habitat.MAGMA: Defined("Magma", checked_by=("engine.ecology.beast_ways.habitat_ways",), used_by=("engine.ecology.anatomy.HABITAT_TESTS",)),
        Habitat.ETHEREAL: Defined(
            "Ethereal",
            checked_by=("engine.ecology.beast_ways.habitat_ways", "engine.ecology.contracts.reachable"),
            used_by=("engine.ecology.anatomy.HABITAT_TESTS",),
        ),
        Habitat.ICE: Defined("Ice", checked_by=(), used_by=("engine.ecology.anatomy.HABITAT_TESTS",)),
        Habitat.SHORE: Defined("Shore", checked_by=(), used_by=("engine.ecology.anatomy.HABITAT_TESTS",)),
    },
)

HERD_TRAINING = total(
    HerdTraining,
    {
        HerdTraining.WAR: Defined("War", checked_by=(), used_by=("engine.ecology.domestication.training_for", "engine.military.units.composition")),
        HerdTraining.HUNTING: Defined(
            "Hunting",
            checked_by=("engine.ecology.ranges.load_wilds", "engine.ecology.w52_life.backfill_hunting_role"),
            used_by=("engine.ecology.domestication.training_for",),
        ),
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

TISSUE_MATERIAL = total(
    TissueMaterial,
    {
        TissueMaterial.SOFT_TISSUE: Defined(
            "Soft tissue", checked_by=(), used_by=("catalog.biology.BIOLOGY_VARIANTS", "catalog.creature_anatomy.PLAN_SKIN", "catalog.creature_anatomy.TISSUES")
        ),
        TissueMaterial.HIDE: Defined(
            "Hide", checked_by=(), used_by=("catalog.creature_anatomy.PLAN_SKIN", "catalog.creature_anatomy.TISSUES", "db.tables.anatomy.CreatureAnatomyRow")
        ),
        TissueMaterial.PLATES: Defined(
            "Plates", checked_by=(), used_by=("catalog.creature_anatomy.PLAN_SKIN", "catalog.creature_anatomy.TISSUES", "catalog.creature_anatomy.TRAIT_SKIN")
        ),
        TissueMaterial.SHELL: Defined("Shell", checked_by=(), used_by=("catalog.creature_anatomy.PLAN_SKIN", "catalog.creature_anatomy.TISSUES")),
        TissueMaterial.PLUMAGE: Defined("Plumage", checked_by=(), used_by=("catalog.creature_anatomy.PLAN_SKIN", "catalog.creature_anatomy.TISSUES")),
        TissueMaterial.RIGID: Defined(
            "Rigid",
            checked_by=(),
            used_by=(
                "catalog.creature_anatomy.PLAN_SKIN",
                "catalog.creature_anatomy.TISSUES",
                "db.tables.anatomy.CreatureAnatomyRow",
                "engine.ecology.anatomy.generate",
            ),
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
                "catalog.life.ecology.BONE_OF",
            ),
        ),
        TissueMaterial.METALLIC: Defined(
            "Metallic",
            checked_by=(),
            used_by=(
                "catalog.biology.BIOLOGY_VARIANTS",
                "catalog.creature_anatomy.EXOTIC_TISSUES",
                "catalog.creature_anatomy.LIFE_SKIN",
                "catalog.creature_anatomy.TISSUES",
                "catalog.life.ecology.BONE_OF",
            ),
        ),
        TissueMaterial.CRYSTALLINE: Defined(
            "Crystalline",
            checked_by=(),
            used_by=(
                "catalog.biology.BIOLOGY_VARIANTS",
                "catalog.creature_anatomy.EXOTIC_TISSUES",
                "catalog.creature_anatomy.LIFE_SKIN",
                "catalog.creature_anatomy.TISSUES",
                "catalog.life.ecology.BONE_OF",
            ),
        ),
        TissueMaterial.GEL: Defined("Gel", checked_by=(), used_by=("catalog.creature_anatomy.EXOTIC_TISSUES", "catalog.creature_anatomy.TISSUES")),
        TissueMaterial.ENERGY: Defined("Energy", checked_by=(), used_by=("catalog.creature_anatomy.EXOTIC_TISSUES", "catalog.creature_anatomy.TISSUES")),
        TissueMaterial.INSUBSTANTIAL: Defined(
            "Insubstantial",
            checked_by=(),
            used_by=("catalog.creature_anatomy.LIFE_SKIN", "catalog.creature_anatomy.PLAN_SKIN", "catalog.creature_anatomy.TISSUES"),
        ),
        TissueMaterial.LIQUID: Defined("Liquid", checked_by=(), used_by=("catalog.creature_anatomy.TISSUES",)),
        TissueMaterial.WOODY: Defined("Woody", checked_by=(), used_by=("catalog.creature_anatomy.PLAN_SKIN", "catalog.creature_anatomy.TISSUES")),
    },
)
