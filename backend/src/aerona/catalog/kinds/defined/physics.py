from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.physics import CosmicFeatureKind, ImpactBody, LifeComplexity, LifeEnvironment

COSMIC_FEATURE_KIND = total(
    CosmicFeatureKind,
    {
        CosmicFeatureKind.ASTEROID_FIELD: Defined(
            "Asteroid field",
            checked_by=("engine.cosmos.physics_control.create_feature",),
            used_by=(
                "engine.cosmos.features.harbour_pirates",
                "engine.cosmos.features.mine_fields",
                "engine.cosmos.impacts.forecast",
                "engine.cosmos.physics_control.STAR_BOUND",
            ),
        ),
        CosmicFeatureKind.WORMHOLE: Defined(
            "Wormhole", checked_by=("engine.cosmos.physics_control.create_feature",), used_by=("engine.cosmos.features.keep_wormholes",)
        ),
        CosmicFeatureKind.PERIODIC_COMET: Defined(
            "Periodic comet",
            checked_by=("engine.cosmos.features.return_comets",),
            used_by=("engine.cosmos.features.WANDERING_SUBTYPES", "engine.cosmos.impacts.forecast"),
        ),
        CosmicFeatureKind.ROGUE_WORLD: Defined(
            "Rogue world",
            checked_by=("engine.cosmos.orbits.rogue_worlds", "engine.cosmos.physics_control.create_feature"),
            used_by=("engine.cosmos.features.pass_rogues", "engine.cosmos.impacts.forecast"),
        ),
        CosmicFeatureKind.GRAVITY_WELL: Defined(
            "Gravity well",
            checked_by=(),
            used_by=("engine.cosmos.features.devour", "engine.cosmos.features.ensure_wells", "engine.cosmos.physics_control.STAR_BOUND"),
        ),
        CosmicFeatureKind.WANDERING_STAR: Defined(
            "Wandering star", checked_by=("engine.cosmos.features.periodic_period",), used_by=("engine.cosmos.features.WANDERING_SUBTYPES",)
        ),
    },
)

IMPACT_BODY = total(
    ImpactBody,
    {
        ImpactBody.ASTEROID: Defined("Asteroid", checked_by=(), used_by=("engine.cosmos.formation.mark_craters", "engine.cosmos.impacts.forecast")),
        ImpactBody.COMET: Defined("Comet", checked_by=(), used_by=("engine.cosmos.formation.mark_craters", "engine.cosmos.impacts.forecast")),
        ImpactBody.ROGUE_WORLD: Defined("Rogue world", checked_by=(), used_by=("engine.cosmos.impacts.forecast",)),
        ImpactBody.CALLED: Defined("Called by a god", checked_by=(), used_by=("engine.cosmos.impacts.call_impact",)),
    },
)

LIFE_COMPLEXITY = total(
    LifeComplexity,
    {
        LifeComplexity.NONE: Defined("No life", checked_by=(), used_by=("engine.cosmos.lifeforms.inferred_life",)),
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

LIFE_ENVIRONMENT = total(
    LifeEnvironment,
    {
        LifeEnvironment.MARINE: Defined("Marine", checked_by=(), used_by=("engine.cosmos.lifeforms.environments_of",)),
        LifeEnvironment.TERRESTRIAL: Defined("Terrestrial", checked_by=(), used_by=("engine.cosmos.lifeforms.environments_of",)),
        LifeEnvironment.AERIAL: Defined("Aerial", checked_by=(), used_by=("engine.cosmos.lifeforms.environments_of",)),
        LifeEnvironment.SUBTERRANEAN: Defined("Subterranean", checked_by=(), used_by=("engine.cosmos.lifeforms.environments_of",)),
    },
)
