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
        RiverShiftCause.SILTING: Defined("Silting", checked_by=(), used_by=("engine.water.courses.silt_out",)),
        RiverShiftCause.WORKS: Defined("Works", checked_by=(), used_by=("engine.water.courses.works_move", "tools.mortal.deep.divert_river")),
        RiverShiftCause.ERUPTION: Defined("Eruption", checked_by=(), used_by=("engine.environment.geomorph.erupted",)),
        RiverShiftCause.LANDSLIDE: Defined("Landslide", checked_by=("engine.water.courses.burst_slide_dams",), used_by=("engine.water.courses.slide_dam",)),
        RiverShiftCause.ICE: Defined("Ice", checked_by=(), used_by=("engine.water.courses.ice_moves",)),
        RiverShiftCause.CAPTURE: Defined("Capture", checked_by=(), used_by=("engine.water.courses.captures",)),
    },
)
