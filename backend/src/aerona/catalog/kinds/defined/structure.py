from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.structure import BuildingForm, StructureSection

BUILDING_FORM = total(
    BuildingForm,
    {
        BuildingForm.HALL: Defined("hall", checked_by=("engine.structures.types.cultural_form",), used_by=("catalog.structure_sections.FORMS",)),
        BuildingForm.LONGHOUSE: Defined("longhouse", checked_by=(), used_by=("catalog.structure_sections.FORMS",)),
        BuildingForm.TOWER: Defined(
            "tower",
            checked_by=("engine.structures.types.cultural_form",),
            used_by=("catalog.structure_sections.FORMS", "catalog.structure_sections.TALL_FORMS"),
        ),
        BuildingForm.KEEP: Defined("keep", checked_by=(), used_by=("catalog.structure_sections.FORMS",)),
        BuildingForm.DOME: Defined("dome", checked_by=("engine.structures.types.cultural_form",), used_by=("catalog.structure_sections.FORMS",)),
        BuildingForm.SPIRE: Defined("spire", checked_by=(), used_by=("catalog.structure_sections.FORMS", "catalog.structure_sections.TALL_FORMS")),
        BuildingForm.STEPPED: Defined("stepped", checked_by=(), used_by=("catalog.structure_sections.FORMS",)),
        BuildingForm.PYRAMID: Defined("pyramid", checked_by=(), used_by=("catalog.structure_sections.FORMS",)),
        BuildingForm.COURTYARD: Defined("courtyard", checked_by=(), used_by=("catalog.structure_sections.FORMS",)),
        BuildingForm.RING: Defined("amphitheatre", checked_by=(), used_by=("catalog.structure_sections.FORMS", "engine.structures.types.FIXED_FORMS")),
        BuildingForm.TENT: Defined("tent", checked_by=(), used_by=("engine.structures.types.cultural_form",)),
        BuildingForm.MOUND: Defined("mound", checked_by=(), used_by=("catalog.structure_sections.FORMS",)),
        BuildingForm.ARCADE: Defined("arcade", checked_by=(), used_by=("catalog.structure_sections.FORMS",)),
        BuildingForm.TERRACE: Defined("terrace", checked_by=(), used_by=("catalog.structure_sections.FORMS",)),
        BuildingForm.PLATFORM: Defined("platform", checked_by=(), used_by=("catalog.structure_sections.FORMS",)),
        BuildingForm.BRIDGE_FORM: Defined("bridge", checked_by=(), used_by=("catalog.structure_sections.FORMS", "engine.structures.types.FIXED_FORMS")),
        BuildingForm.WALL_LINE: Defined(
            "wall", checked_by=("engine.urban.cityscape.perimeter_of",), used_by=("catalog.structure_sections.FORMS", "engine.structures.types.FIXED_FORMS")
        ),
        BuildingForm.TUNNEL_FORM: Defined("tunnel", checked_by=(), used_by=("catalog.structure_sections.FORMS", "engine.structures.types.FIXED_FORMS")),
        BuildingForm.ORBITAL: Defined("ring", checked_by=(), used_by=("catalog.structure_sections.FORMS", "engine.structures.types.FIXED_FORMS")),
        BuildingForm.HIGH_RISE: Defined(
            "high_rise",
            checked_by=("catalog.structure_sections.FORM_GUARD",),
            used_by=("catalog.structure_sections.TALL_FORMS", "engine.structures.types.cultural_form"),
        ),
        BuildingForm.ARCOLOGY: Defined(
            "arcology",
            checked_by=("catalog.structure_sections.FORM_GUARD",),
            used_by=("catalog.structure_sections.TALL_FORMS", "engine.structures.types.cultural_form"),
        ),
        BuildingForm.BUNKER: Defined("bunker", checked_by=("catalog.structure_sections.FORM_GUARD",), used_by=("engine.structures.types.cultural_form",)),
        BuildingForm.FLOATING: Defined("floating", checked_by=("catalog.structure_sections.FORM_GUARD",), used_by=("engine.structures.types.cultural_form",)),
        BuildingForm.GEODESIC: Defined("geodesic", checked_by=("catalog.structure_sections.FORM_GUARD",), used_by=("engine.structures.types.cultural_form",)),
        BuildingForm.MODULAR: Defined("modular", checked_by=("catalog.structure_sections.FORM_GUARD",), used_by=("engine.structures.types.cultural_form",)),
        BuildingForm.GROWN: Defined(
            "grown",
            checked_by=("catalog.structure_sections.FORM_GUARD", "engine.living.backfill.grown_works"),
            used_by=("engine.structures.types.cultural_form",),
        ),
        BuildingForm.CARVED: Defined("carved", checked_by=("catalog.structure_sections.FORM_GUARD",), used_by=("engine.structures.types.cultural_form",)),
    },
)

STRUCTURE_SECTION = total(
    StructureSection,
    {
        StructureSection.FOUNDATION: Defined(
            "Foundation",
            checked_by=("engine.structures.integrity.strike_rows",),
            used_by=(
                "catalog.structure_sections.ARENA",
                "catalog.structure_sections.BARRACKS",
                "catalog.structure_sections.BRIDGE",
                "catalog.structure_sections.CARE",
                "catalog.structure_sections.DAM",
                "catalog.structure_sections.ELEVATOR",
                "catalog.structure_sections.ENGINE",
                "catalog.structure_sections.FAITH",
                "catalog.structure_sections.FORTRESS",
                "catalog.structure_sections.FURNACE_WORKS",
                "catalog.structure_sections.GATE",
                "catalog.structure_sections.GATEWAY",
                "catalog.structure_sections.GROUND",
                "catalog.structure_sections.HOUSE",
                "catalog.structure_sections.KNOWLEDGE",
                "catalog.structure_sections.LIGHT",
                "catalog.structure_sections.MARKET",
                "catalog.structure_sections.MONUMENT",
                "catalog.structure_sections.PENS",
                "catalog.structure_sections.PIT",
                "catalog.structure_sections.PLANT",
                "catalog.structure_sections.PLAZA",
                "catalog.structure_sections.ROAD",
                "catalog.structure_sections.SEAT",
                "catalog.structure_sections.STATION",
                "catalog.structure_sections.STORE",
                "catalog.structure_sections.TOMB",
                "catalog.structure_sections.TOWER",
                "catalog.structure_sections.TUNNEL",
                "catalog.structure_sections.VAULTED_ARCHIVE",
                "catalog.structure_sections.WALL",
                "catalog.structure_sections.WATERWORK",
                "catalog.structure_sections.WHEEL_WORKS",
                "catalog.structure_sections.WONDER",
                "catalog.structure_sections.WORKS",
            ),
        ),
        StructureSection.OUTER_WALL: Defined(
            "Outer wall",
            checked_by=(),
            used_by=(
                "catalog.structure_sections.DAM",
                "catalog.structure_sections.FORTRESS",
                "catalog.structure_sections.WALL",
                "engine.structures.damage.BREACHES",
            ),
        ),
        StructureSection.GATE: Defined(
            "Gate", checked_by=(), used_by=("catalog.structure_sections.FORTRESS", "catalog.structure_sections.GATE", "engine.structures.damage.BREACHES")
        ),
        StructureSection.GATEHOUSE: Defined("Gatehouse", checked_by=(), used_by=("catalog.structure_sections.GATE",)),
        StructureSection.TOWERS: Defined(
            "Towers",
            checked_by=(),
            used_by=(
                "catalog.structure_sections.FORTRESS",
                "catalog.structure_sections.GATE",
                "catalog.structure_sections.LIGHT",
                "catalog.structure_sections.TOWER",
                "catalog.structure_sections.WALL",
                "engine.structures.integrity.TALL",
            ),
        ),
        StructureSection.KEEP: Defined(
            "Keep", checked_by=(), used_by=("catalog.structure_sections.FORTRESS", "engine.structures.damage.FALLEN", "engine.structures.integrity.TALL")
        ),
        StructureSection.BATTLEMENTS: Defined(
            "Battlements",
            checked_by=(),
            used_by=(
                "catalog.structure_sections.FORTRESS",
                "catalog.structure_sections.GATE",
                "catalog.structure_sections.TOWER",
                "catalog.structure_sections.WALL",
            ),
        ),
        StructureSection.EARTHWORK: Defined(
            "Earthwork", checked_by=(), used_by=("catalog.structure_sections.GARDEN", "catalog.structure_sections.PLAZA", "catalog.structure_sections.WALL")
        ),
        StructureSection.ROOF: Defined(
            "Roof",
            checked_by=(),
            used_by=(
                "catalog.structure_sections.ARENA",
                "catalog.structure_sections.BARRACKS",
                "catalog.structure_sections.CARE",
                "catalog.structure_sections.FAITH",
                "catalog.structure_sections.FURNACE_WORKS",
                "catalog.structure_sections.HOUSE",
                "catalog.structure_sections.KNOWLEDGE",
                "catalog.structure_sections.MARKET",
                "catalog.structure_sections.PENS",
                "catalog.structure_sections.PLANT",
                "catalog.structure_sections.SEAT",
                "catalog.structure_sections.STORE",
                "catalog.structure_sections.TOWER",
                "catalog.structure_sections.WHEEL_WORKS",
                "catalog.structure_sections.WORKS",
                "engine.structures.integrity.TALL",
            ),
        ),
        StructureSection.MAIN_HALL: Defined(
            "Main hall",
            checked_by=(),
            used_by=(
                "catalog.structure_sections.BARRACKS",
                "catalog.structure_sections.CARE",
                "catalog.structure_sections.FAITH",
                "catalog.structure_sections.GROUND",
                "catalog.structure_sections.HOUSE",
                "catalog.structure_sections.KNOWLEDGE",
                "catalog.structure_sections.MARKET",
                "catalog.structure_sections.SEAT",
                "catalog.structure_sections.STATION",
                "catalog.structure_sections.WONDER",
            ),
        ),
        StructureSection.UPPER_FLOORS: Defined(
            "Upper floors",
            checked_by=(),
            used_by=(
                "catalog.structure_sections.GROUND",
                "catalog.structure_sections.HOUSE",
                "catalog.structure_sections.KNOWLEDGE",
                "catalog.structure_sections.SEAT",
                "engine.structures.integrity.TALL",
            ),
        ),
        StructureSection.STORES: Defined(
            "Stores",
            checked_by=("engine.structures.damage.house_effects",),
            used_by=(
                "catalog.structure_sections.BARRACKS",
                "catalog.structure_sections.CARE",
                "catalog.structure_sections.FORTRESS",
                "catalog.structure_sections.FURNACE_WORKS",
                "catalog.structure_sections.GARDEN",
                "catalog.structure_sections.HOUSE",
                "catalog.structure_sections.MARKET",
                "catalog.structure_sections.PENS",
                "catalog.structure_sections.PIT",
                "catalog.structure_sections.PLANT",
                "catalog.structure_sections.PORT",
                "catalog.structure_sections.STATION",
                "catalog.structure_sections.STORE",
                "catalog.structure_sections.WHEEL_WORKS",
                "catalog.structure_sections.WORKS",
                "catalog.structure_sections.YARD",
            ),
        ),
        StructureSection.QUARTERS: Defined(
            "Quarters",
            checked_by=(),
            used_by=(
                "catalog.structure_sections.ARENA",
                "catalog.structure_sections.BARRACKS",
                "catalog.structure_sections.CARE",
                "catalog.structure_sections.FORTRESS",
                "catalog.structure_sections.GATEWAY",
                "catalog.structure_sections.LIGHT",
                "catalog.structure_sections.SEAT",
            ),
        ),
        StructureSection.WORKSHOP_FLOOR: Defined(
            "Workshop floor",
            checked_by=(),
            used_by=(
                "catalog.structure_sections.FURNACE_WORKS",
                "catalog.structure_sections.PIT",
                "catalog.structure_sections.PLANT",
                "catalog.structure_sections.WHEEL_WORKS",
                "catalog.structure_sections.WORKS",
            ),
        ),
        StructureSection.KITCHEN: Defined("Kitchen", checked_by=(), used_by=("catalog.structure_sections.CARE", "catalog.structure_sections.SEAT")),
        StructureSection.SANCTUM: Defined(
            "Sanctum",
            checked_by=("engine.structures.damage.house_effects",),
            used_by=("catalog.structure_sections.FAITH", "catalog.structure_sections.TOMB", "catalog.structure_sections.WONDER"),
        ),
        StructureSection.VAULT: Defined(
            "Vault",
            checked_by=(),
            used_by=(
                "catalog.structure_sections.FAITH",
                "catalog.structure_sections.SEAT",
                "catalog.structure_sections.TOMB",
                "catalog.structure_sections.WONDER",
            ),
        ),
        StructureSection.ARCHIVE: Defined(
            "Archive",
            checked_by=("engine.structures.damage.house_effects",),
            used_by=("catalog.structure_sections.KNOWLEDGE", "catalog.structure_sections.VAULTED_ARCHIVE"),
        ),
        StructureSection.WARDS: Defined("Wards", checked_by=(), used_by=("catalog.structure_sections.GATEWAY", "catalog.structure_sections.VAULTED_ARCHIVE")),
        StructureSection.DOME: Defined(
            "Dome", checked_by=(), used_by=("catalog.structure_sections.FAITH", "catalog.structure_sections.WONDER", "engine.structures.integrity.TALL")
        ),
        StructureSection.SPIRE: Defined(
            "Spire", checked_by=(), used_by=("catalog.structure_sections.MONUMENT", "catalog.structure_sections.WONDER", "engine.structures.integrity.TALL")
        ),
        StructureSection.SPAN: Defined(
            "Span", checked_by=("engine.structures.damage.works_effects",), used_by=("catalog.structure_sections.BRIDGE", "catalog.structure_sections.ROAD")
        ),
        StructureSection.PIERS: Defined(
            "Piers",
            checked_by=("engine.structures.integrity.strike_rows",),
            used_by=("catalog.structure_sections.BRIDGE", "catalog.structure_sections.PORT", "catalog.structure_sections.YARD"),
        ),
        StructureSection.SLUICE: Defined(
            "Sluice", checked_by=("engine.structures.damage.works_effects",), used_by=("catalog.structure_sections.DAM", "catalog.structure_sections.WATERWORK")
        ),
        StructureSection.CONDUITS: Defined(
            "Conduits",
            checked_by=(),
            used_by=(
                "catalog.structure_sections.DAM",
                "catalog.structure_sections.ENGINE",
                "catalog.structure_sections.GARDEN",
                "catalog.structure_sections.TUNNEL",
                "catalog.structure_sections.WATERWORK",
            ),
        ),
        StructureSection.SEATING: Defined("Seating", checked_by=(), used_by=("catalog.structure_sections.ARENA",)),
        StructureSection.STAGE: Defined("Stage", checked_by=(), used_by=("catalog.structure_sections.ARENA",)),
        StructureSection.PENS: Defined("Pens", checked_by=(), used_by=("catalog.structure_sections.PENS",)),
        StructureSection.FURNACE: Defined("Furnace", checked_by=(), used_by=("catalog.structure_sections.FURNACE_WORKS", "catalog.structure_sections.PLANT")),
        StructureSection.WHEEL: Defined("Wheel", checked_by=(), used_by=("catalog.structure_sections.WHEEL_WORKS",)),
        StructureSection.SHAFTS: Defined("Shafts", checked_by=(), used_by=("catalog.structure_sections.PIT", "catalog.structure_sections.TUNNEL")),
        StructureSection.DOCKS: Defined(
            "Docks", checked_by=(), used_by=("catalog.structure_sections.PORT", "catalog.structure_sections.STATION", "catalog.structure_sections.YARD")
        ),
        StructureSection.SLIPWAY: Defined("Slipway", checked_by=(), used_by=("catalog.structure_sections.YARD",)),
        StructureSection.BEACON: Defined(
            "Beacon",
            checked_by=(),
            used_by=(
                "catalog.structure_sections.COSMIC_BEACON",
                "catalog.structure_sections.LIGHT",
                "catalog.structure_sections.PORT",
                "catalog.structure_sections.STATION",
                "catalog.structure_sections.TOWER",
                "engine.structures.integrity.TALL",
            ),
        ),
        StructureSection.CORE: Defined("Core", checked_by=(), used_by=("catalog.structure_sections.GATEWAY", "catalog.structure_sections.VAULTED_ARCHIVE")),
        StructureSection.SPINE: Defined(
            "Spine",
            checked_by=("engine.structures.integrity.strike_rows",),
            used_by=(
                "catalog.structure_sections.COLLECTOR",
                "catalog.structure_sections.COSMIC_BEACON",
                "catalog.structure_sections.ELEVATOR",
                "catalog.structure_sections.HABITAT",
                "catalog.structure_sections.RING",
                "catalog.structure_sections.STATION_RING",
                "engine.structures.integrity.TALL",
            ),
        ),
        StructureSection.RING_SEGMENTS: Defined(
            "Ring segments", checked_by=(), used_by=("catalog.structure_sections.RING", "engine.structures.damage.BREACHED_DECKS")
        ),
        StructureSection.COLLECTORS: Defined("Collectors", checked_by=(), used_by=("catalog.structure_sections.COLLECTOR",)),
        StructureSection.THRUSTERS: Defined(
            "Thrusters",
            checked_by=(),
            used_by=(
                "catalog.structure_sections.COLLECTOR",
                "catalog.structure_sections.ENGINE",
                "catalog.structure_sections.RING",
                "catalog.structure_sections.STATION_RING",
            ),
        ),
        StructureSection.DOCKING_RING: Defined(
            "Docking ring",
            checked_by=(),
            used_by=(
                "catalog.structure_sections.ELEVATOR",
                "catalog.structure_sections.HABITAT",
                "catalog.structure_sections.RING",
                "catalog.structure_sections.STATION_RING",
            ),
        ),
        StructureSection.HABITAT_DECKS: Defined(
            "Habitat decks",
            checked_by=(),
            used_by=("catalog.structure_sections.HABITAT", "catalog.structure_sections.STATION_RING", "engine.structures.damage.BREACHED_DECKS"),
        ),
        StructureSection.CONTROL_CORE: Defined(
            "Control core",
            checked_by=("engine.structures.damage.consequences",),
            used_by=(
                "catalog.structure_sections.COLLECTOR",
                "catalog.structure_sections.COSMIC_BEACON",
                "catalog.structure_sections.ELEVATOR",
                "catalog.structure_sections.ENGINE",
                "catalog.structure_sections.HABITAT",
                "catalog.structure_sections.RING",
                "catalog.structure_sections.STATION_RING",
            ),
        ),
        StructureSection.SHIELDING: Defined(
            "Shielding",
            checked_by=(),
            used_by=(
                "catalog.structure_sections.COLLECTOR",
                "catalog.structure_sections.COSMIC_BEACON",
                "catalog.structure_sections.ENGINE",
                "catalog.structure_sections.HABITAT",
                "catalog.structure_sections.RING",
                "catalog.structure_sections.STATION_RING",
            ),
        ),
    },
)
