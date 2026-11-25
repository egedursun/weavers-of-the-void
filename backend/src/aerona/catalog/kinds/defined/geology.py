from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.geology import DeepPassageKind, DeepPassageOrigin

DEEP_PASSAGE_KIND = total(
    DeepPassageKind,
    {
        DeepPassageKind.LEVEL: Defined(
            "Level passage",
            checked_by=("api.views.deep_map.passage_lines", "engine.primitives.deep.LayeredGraph.__init__", "engine.primitives.deep.LayeredGraph.cost"),
            used_by=("engine.primitives.deep.passage_kind",),
        ),
        DeepPassageKind.VERTICAL: Defined("Vertical passage", checked_by=(), used_by=("engine.primitives.deep.passage_kind",)),
        DeepPassageKind.OPENING: Defined(
            "Opening to the surface", checked_by=("api.views.deep_map.deep_summary",), used_by=("engine.primitives.deep.passage_kind",)
        ),
    },
)

DEEP_PASSAGE_ORIGIN = total(
    DeepPassageOrigin,
    {
        DeepPassageOrigin.NATURAL: Defined(
            "Formed with the world", checked_by=(), used_by=("db.tables.geology.DeepPassageRow", "engine.environment.cells.lay_natural_passages")
        ),
        DeepPassageOrigin.DUG: Defined(
            "Dug by a people",
            checked_by=(),
            used_by=("engine.environment.cells.dig_toward", "engine.environment.cells.open_the_way_down", "engine.environment.deep.reach_stratum"),
        ),
        DeepPassageOrigin.BREACH: Defined("Broken open", checked_by=(), used_by=("engine.environment.cells.breach_opening",)),
        DeepPassageOrigin.DIVINE: Defined("Made by a god", checked_by=(), used_by=("engine.environment.shaping.stir_ground", "tools.son.deep.open_the_deep")),
    },
)
