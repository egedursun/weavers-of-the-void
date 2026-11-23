from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.physics import CosmicFeatureKind, LifeComplexity

COSMIC_FEATURE_KIND = total(
    CosmicFeatureKind,
    {
        CosmicFeatureKind.ASTEROID_FIELD: Defined(
            "Asteroid field",
            checked_by=("engine.cosmos.physics_control.create_feature",),
            used_by=(
                "catalog.life.cosmos.STAR_BOUND",
                "engine.cosmos.features.harbour_pirates",
                "engine.cosmos.features.mine_fields",
                "engine.cosmos.impacts.forecast",
            ),
        ),
        CosmicFeatureKind.WORMHOLE: Defined(
            "Wormhole", checked_by=("engine.cosmos.physics_control.create_feature",), used_by=("engine.cosmos.features.keep_wormholes",)
        ),
        CosmicFeatureKind.PERIODIC_COMET: Defined(
            "Periodic comet",
            checked_by=("engine.cosmos.features.return_comets",),
            used_by=("catalog.life.domain.PERIODIC_BODIES", "engine.cosmos.features.WANDERING_SUBTYPES", "engine.cosmos.impacts.forecast"),
        ),
        CosmicFeatureKind.ROGUE_WORLD: Defined(
            "Rogue world",
            checked_by=("engine.cosmos.orbits.rogue_worlds", "engine.cosmos.physics_control.create_feature"),
            used_by=("engine.cosmos.features.pass_rogues", "engine.cosmos.impacts.forecast"),
        ),
        CosmicFeatureKind.GRAVITY_WELL: Defined(
            "Gravity well", checked_by=(), used_by=("catalog.life.cosmos.STAR_BOUND", "engine.cosmos.features.devour", "engine.cosmos.features.ensure_wells")
        ),
        CosmicFeatureKind.WANDERING_STAR: Defined(
            "Wandering star",
            checked_by=("engine.cosmos.features.periodic_period",),
            used_by=("catalog.life.domain.PERIODIC_BODIES", "engine.cosmos.features.WANDERING_SUBTYPES"),
        ),
    },
)

LIFE_COMPLEXITY = total(
    LifeComplexity,
    {
        LifeComplexity.NONE: Defined("No life", checked_by=("engine.cosmos.lifeforms.rehome_life",), used_by=("engine.cosmos.lifeforms.inferred_life",)),
        LifeComplexity.MICROBIAL: Defined("Microbial", checked_by=(), used_by=("engine.cosmos.lifeforms.inferred_life",)),
        LifeComplexity.SIMPLE: Defined("Simple", checked_by=(), used_by=("engine.cosmos.lifeforms.inferred_life",)),
        LifeComplexity.COMPLEX: Defined(
            "Complex",
            checked_by=(),
            used_by=(
                "db.tables.physics.WorldLifeRow",
                "engine.cosmos.lifeforms.inferred_life",
                "engine.cosmos.lifeforms.quicken",
                "engine.phases.life_seed.life_seed",
                "engine.phases.life_seed.seed_life",
            ),
        ),
        LifeComplexity.SAPIENT: Defined(
            "Sapient",
            checked_by=(),
            used_by=("engine.cosmos.lifeforms.inferred_life", "engine.phases.life_seed.life_seed", "engine.phases.life_seed.seed_life"),
        ),
    },
)
