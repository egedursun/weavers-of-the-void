from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.happening import RiverShiftCause

RIVER_SHIFT_CAUSE = total(
    RiverShiftCause,
    {
        RiverShiftCause.FLOOD: Defined("Flood", checked_by=(), used_by=("engine.environment.geomorph.river_after_flood",)),
        RiverShiftCause.QUAKE: Defined("Quake", checked_by=(), used_by=("engine.environment.geomorph.river_after_quake",)),
        RiverShiftCause.DIVINE: Defined("Divine", checked_by=(), used_by=("engine.environment.shaping.work_soil", "tools.son.regions.redirect_river")),
        RiverShiftCause.PLAYER: Defined(
            "Player", checked_by=(), used_by=("engine.environment.region_control.redirect_river", "services.player.happenings.move_river")
        ),
    },
)
