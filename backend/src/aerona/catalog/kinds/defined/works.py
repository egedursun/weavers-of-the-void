from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.works import WorksKind

WORKS_KIND = total(
    WorksKind,
    {
        WorksKind.ROAD: Defined(
            "Road",
            checked_by=("engine.works.building.WORKS_LEVELS",),
            used_by=("db.tables.works.PublicWorksRow", "engine.works.building.ROUTE_WORKS", "engine.works.seed.LEVEL_KINDS"),
        ),
        WorksKind.BRIDGE: Defined(
            "Bridge", checked_by=("engine.works.building.WORKS_LEVELS",), used_by=("engine.works.building.ROUTE_WORKS", "engine.works.seed.LEVEL_KINDS")
        ),
        WorksKind.CANAL: Defined("Canal", checked_by=("engine.works.building.WORKS_LEVELS",), used_by=("engine.works.building.ROUTE_WORKS",)),
        WorksKind.RAIL_LINE: Defined("Rail line", checked_by=("engine.works.building.WORKS_LEVELS",), used_by=("engine.works.building.ROUTE_WORKS",)),
        WorksKind.AQUEDUCT: Defined("Aqueduct", checked_by=("engine.works.building.apply_works", "engine.works.building.shift_infrastructure"), used_by=()),
        WorksKind.DAM: Defined("Dam", checked_by=("engine.works.building.WORKS_LEVELS",), used_by=()),
        WorksKind.DRAINAGE: Defined("Drainage", checked_by=("engine.works.building.WORKS_LEVELS",), used_by=("engine.works.seed.LEVEL_KINDS",)),
        WorksKind.HARBOUR_WORKS: Defined("Harbour works", checked_by=("engine.works.building.WORKS_LEVELS",), used_by=("engine.works.seed.CAPACITY_KINDS",)),
        WorksKind.WALLS: Defined("Walls", checked_by=("engine.works.building.WORKS_LEVELS",), used_by=("engine.works.seed.LEVEL_KINDS",)),
        WorksKind.GRANARY_SYSTEM: Defined("Granary system", checked_by=("engine.works.building.WORKS_LEVELS",), used_by=("engine.works.seed.CAPACITY_KINDS",)),
        WorksKind.SEWER: Defined(
            "Sewer", checked_by=("engine.works.building.apply_works", "engine.works.building.shift_infrastructure"), used_by=("engine.works.seed.legacy_kinds",)
        ),
        WorksKind.POWER_LINE: Defined("Power line", checked_by=("catalog.works_shapes.WORKS_PROSPERITY_PCT",), used_by=()),
        WorksKind.NETWORK_LINE: Defined("Network line", checked_by=("catalog.works_shapes.WORKS_PROSPERITY_PCT",), used_by=()),
        WorksKind.TERRAFORMING_STAGE: Defined("Terraforming stage", checked_by=("catalog.works_shapes.WORKS_PROSPERITY_PCT",), used_by=()),
        WorksKind.MEGASTRUCTURE_STAGE: Defined("Megastructure stage", checked_by=("catalog.works_shapes.WORKS_PROSPERITY_PCT",), used_by=()),
        WorksKind.GROWN_WORKS: Defined("Grown works", checked_by=("catalog.works_shapes.WORKS_PROSPERITY_PCT",), used_by=()),
    },
)
