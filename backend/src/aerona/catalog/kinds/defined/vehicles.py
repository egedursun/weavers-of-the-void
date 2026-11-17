from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.vehicles import FireControl, MountArc

FIRE_CONTROL = total(
    FireControl,
    {
        FireControl.MANUAL: Defined(
            "By hand",
            checked_by=(),
            used_by=("db.tables.collective.DesignRow", "engine.collective.designs.FIRE_ORDER", "engine.collective.designs.draw_design"),
        ),
        FireControl.DRILLED: Defined("Drilled crews", checked_by=(), used_by=("engine.collective.designs.FIRE_ORDER",)),
        FireControl.SIGHTED: Defined("Sighted", checked_by=(), used_by=("engine.collective.designs.FIRE_ORDER",)),
        FireControl.DIRECTED: Defined("Directed", checked_by=(), used_by=("engine.collective.designs.FIRE_ORDER",)),
        FireControl.COMPUTED: Defined("Computed", checked_by=(), used_by=("engine.collective.designs.FIRE_ORDER",)),
        FireControl.AUTOMATIC: Defined("Automatic", checked_by=(), used_by=("engine.collective.designs.FIRE_ORDER",)),
        FireControl.GUIDED: Defined("Guided", checked_by=(), used_by=("engine.collective.designs.FIRE_ORDER",)),
    },
)

MOUNT_ARC = total(
    MountArc,
    {
        MountArc.FORWARD: Defined("Forward", checked_by=(), used_by=("engine.collective.designs.MOUNT_ARCS",)),
        MountArc.AFT: Defined("Aft", checked_by=(), used_by=("engine.collective.designs.MOUNT_ARCS",)),
        MountArc.SIDE: Defined("Sides", checked_by=(), used_by=("engine.collective.designs.MOUNT_ARCS",)),
        MountArc.ALL_ROUND: Defined(
            "All round", checked_by=("engine.vehicles.fixups.rearm",), used_by=("db.tables.vehicles.DesignMountRow", "engine.collective.designs.MOUNT_ARCS")
        ),
    },
)
