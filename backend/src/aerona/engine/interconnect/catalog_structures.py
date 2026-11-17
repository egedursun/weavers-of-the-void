from aerona.db.tables.economy import WorkshopRow
from aerona.db.tables.structures import ConstructionRow, StructureDesignRow, StructureProfileRow, StructureStaffRow
from aerona.domain.enums.structure import StructureKind
from aerona.engine.interconnect.registry import Coupling, EdgeKind, Exposure, Mechanic, Subsystem, Surface

STRUCTURE_SECTION = "section-structure"
STRUCTURES_SECTION = "section-structures"
KINDS = tuple(item.value for item in StructureKind)
HOSTS = ("settlement", "people", "structure")

STRUCTURE_MECHANICS = (
    Mechanic(
        key="structure_profiles",
        spec_item="S7.2",
        title="Typed structures: kind, level, capacity, material, builder, architect, aesthetic and ley line",
        subsystem=Subsystem.ECONOMY,
        phases=("structure_survey",),
        surface=Surface(drawer=STRUCTURE_SECTION),
        backfill="structures.typed_backfill: every standing structure is typed once from its record and linked to its workshop",
        templates=("structures.damaged", "structures.repaired"),
        fields=(
            "kind",
            "level",
            "capacity",
            "condition",
            "construction_state",
            "fire_resistance",
            "builder_kind",
            "architect",
            "dedicated_son",
            "style_ornament",
            "style_geometry",
            "style_colour",
            "style_scale",
            "style_symmetry",
            "on_ley_line",
            "anchor",
            *KINDS,
        ),
        tables=(StructureProfileRow.__tablename__, StructureDesignRow.__tablename__, WorkshopRow.__tablename__),
        exposure=Exposure.TOOL,
        tools=("build_structure", "commission_structure"),
        targets=HOSTS,
        couplings=(
            Coupling(Subsystem.ENVIRONMENT, "ley lines strengthen attuned works", EdgeKind.MODIFIER, "structure_functions.ley_bonus_pct"),
            Coupling(Subsystem.ENVIRONMENT, "earthquakes break brittle materials", EdgeKind.MODIFIER, "upkeep.quake_toughness_pct"),
            Coupling(Subsystem.ECONOMY, "a working forge, mill or mine drives its workshop", EdgeKind.MODIFIER, "structure_functions.mill_output_pct"),
        ),
    ),
    Mechanic(
        key="structure_construction",
        spec_item="S7.2",
        title="Construction over ages: builders, engineering and materials; wonders across generations; abandoned shells become legends",
        subsystem=Subsystem.ECONOMY,
        phases=("engine_works",),
        surface=Surface(drawer=STRUCTURES_SECTION),
        backfill="none: works begin from the next epoch",
        templates=("structures.begun", "structures.finished", "structures.abandoned", "structures.generation"),
        fields=("cost", "work", "funds", "workers", "materials_pct", "stalled_epochs", "generations"),
        tables=(ConstructionRow.__tablename__,),
        exposure=Exposure.CONTEXT,
        targets=HOSTS,
        couplings=(
            Coupling(Subsystem.DEMOGRAPHY, "builders come from the community's labour", EdgeKind.FLOW, "construction.worker_output"),
            Coupling(Subsystem.KNOWLEDGE, "architecture and the architect speed the work", EdgeKind.MODIFIER, "construction.engineering_pct_per_level"),
            Coupling(Subsystem.ECONOMY, "stone, timber and coin are spent on the work", EdgeKind.FLOW, "construction.materials_per_100_work"),
            Coupling(Subsystem.CULTURE, "an abandoned great work leaves a legend", EdgeKind.TRIGGER, "construction.legend_scale"),
        ),
    ),
    Mechanic(
        key="structure_upkeep",
        spec_item="S7.2",
        title="Upkeep, staff from cohorts and decay: unpaid works crumble, unstaffed works stand idle",
        subsystem=Subsystem.ECONOMY,
        phases=("structure_upkeep",),
        surface=Surface(drawer=STRUCTURE_SECTION),
        backfill="structure_upkeep: staff and upkeep are reckoned every epoch",
        templates=("structures.ruined", "structures.damaged"),
        fields=("staff_required", "staff_allocated", "upkeep_coin", "upkeep_goods", "unpaid_epochs", "condition"),
        tables=(StructureStaffRow.__tablename__,),
        targets=HOSTS,
        couplings=(
            Coupling(Subsystem.DEMOGRAPHY, "priests, scribes and guards are drawn from the cohorts", EdgeKind.FLOW, "upkeep.staff_share_pct"),
            Coupling(Subsystem.POLITY, "the treasury pays each work's upkeep", EdgeKind.FLOW, "upkeep.coin_major"),
            Coupling(Subsystem.ECONOMY, "unpaid upkeep wears condition away", EdgeKind.MODIFIER, "upkeep.unpaid_condition_loss"),
        ),
    ),
    Mechanic(
        key="structure_functions",
        spec_item="S7.2",
        title="Function by kind times condition and staff: faith, learning, healing, defence, order, trade, production, water, roads, mood and wonders",
        subsystem=Subsystem.ECONOMY,
        phases=("structure_functions", "splendor_growth"),
        surface=Surface(drawer=STRUCTURES_SECTION),
        backfill="none: functions act from the next epoch",
        templates=("structures.duel", "structures.burned", "living_stats.work_knowledge"),
        fields=("effect_pct", "staff_pct", "splendor", "function"),
        exposure=Exposure.CONTEXT,
        targets=HOSTS,
        couplings=(
            Coupling(Subsystem.FAITH, "temples and shrines hold piety", EdgeKind.MODIFIER, "structure_functions.temple_piety_pct"),
            Coupling(Subsystem.KNOWLEDGE, "libraries and academies deepen learning", EdgeKind.TRIGGER, "structure_functions.library_deepen_pct"),
            Coupling(Subsystem.BODY, "hospitals cut infection and death from wounds", EdgeKind.MODIFIER, "structure_functions.hospital_infection_cut_pct"),
            Coupling(
                Subsystem.WAR,
                "walls write their level and material into the settlement's defences",
                EdgeKind.FLOW,
                "structure_functions.wall_defense_per_level",
            ),
            Coupling(Subsystem.POLITY, "a palace lends its realm legitimacy", EdgeKind.MODIFIER, "structure_functions.palace_legitimacy"),
            Coupling(Subsystem.SOCIAL, "courts and prisons keep order; arenas and theatres calm unrest", EdgeKind.MODIFIER, "structure_functions.court_order"),
            Coupling(
                Subsystem.ECONOMY, "caravanserais and markets are waystations on the roads", EdgeKind.MODIFIER, "structure_functions.caravanserai_capacity"
            ),
            Coupling(Subsystem.ENVIRONMENT, "dams turn floods aside", EdgeKind.MODIFIER, "structure_functions.dam_flood_cut_pct"),
            Coupling(Subsystem.COSMOS, "a cosmic gate opens ancient gates without blood", EdgeKind.RULE_SWITCH, "structure_functions.gate_open_pct"),
            Coupling(Subsystem.CULTURE, "monuments, theatres and wonders raise prestige", EdgeKind.MODIFIER, "structure_functions.wonder_prestige"),
        ),
    ),
)
