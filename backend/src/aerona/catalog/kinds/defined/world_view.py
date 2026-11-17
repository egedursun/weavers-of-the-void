from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.world_view import BindingNeed, WarTerrain

BINDING_NEED = total(
    BindingNeed,
    {
        BindingNeed.NONE: Defined(
            "Nothing beyond food",
            checked_by=("agents.context.world_view_lines.view_lines", "engine.cosmos.world_views.keep_needs"),
            used_by=("catalog.world_views.WorldViewSpec", "db.tables.world_views.WorldViewRow", "engine.cosmos.world_views.WorldView"),
        ),
        BindingNeed.WATER: Defined(
            "Water", checked_by=("engine.cosmos.world_views.born_free", "engine.cosmos.world_views.need_met"), used_by=("catalog.world_views.WORLD_VIEWS",)
        ),
        BindingNeed.HEAT: Defined(
            "Heat", checked_by=("engine.cosmos.world_views.born_free", "engine.cosmos.world_views.need_met"), used_by=("catalog.world_views.WORLD_VIEWS",)
        ),
        BindingNeed.AIR: Defined(
            "Air",
            checked_by=("engine.cosmos.world_views.born_free", "engine.cosmos.world_views.keep_needs", "engine.cosmos.world_views.need_met"),
            used_by=("catalog.world_views.SEALED_WORLD",),
        ),
        BindingNeed.OFFERINGS: Defined("Offerings", checked_by=("engine.cosmos.world_views.need_met",), used_by=("catalog.world_views.WORLD_VIEWS",)),
        BindingNeed.BELIEF: Defined("Belief", checked_by=("engine.cosmos.world_views.need_met",), used_by=("catalog.world_views.WORLD_VIEWS",)),
    },
)

WAR_TERRAIN = total(
    WarTerrain,
    {
        WarTerrain.LAND: Defined(
            "On land",
            checked_by=("agents.context.world_view_lines.view_lines",),
            used_by=("catalog.world_views.WorldViewSpec", "db.tables.world_views.WorldViewRow", "engine.cosmos.world_views.WorldView"),
        ),
        WarTerrain.NAVAL: Defined("At sea", checked_by=(), used_by=("catalog.world_views.WORLD_VIEWS", "engine.cosmos.world_views.LAND_UNFIT")),
        WarTerrain.SKY: Defined(
            "In the sky", checked_by=(), used_by=("catalog.world_views.SKY_WORLD", "catalog.world_views.WORLD_VIEWS", "engine.cosmos.world_views.LAND_UNFIT")
        ),
        WarTerrain.BOARDING: Defined("By boarding", checked_by=(), used_by=("catalog.world_views.WORLD_VIEWS", "engine.cosmos.world_views.LAND_UNFIT")),
        WarTerrain.STRATA: Defined("Between strata", checked_by=(), used_by=("catalog.world_views.WORLD_VIEWS",)),
    },
)
