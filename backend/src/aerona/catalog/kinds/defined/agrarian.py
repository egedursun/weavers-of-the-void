from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.agrarian import KeystoneUse, NutrientKind, PreparednessKind, RebuildCause, RebuildPlan

KEYSTONE_USE = total(
    KeystoneUse,
    {
        KeystoneUse.NAVIGATION: Defined("Navigation", checked_by=("engine.agrarian.staples.dependents_suffer",), used_by=()),
        KeystoneUse.LONGEVITY: Defined("Longevity", checked_by=("engine.agrarian.staples.dependents_suffer",), used_by=()),
        KeystoneUse.PRESCIENCE: Defined("Prescience", checked_by=("engine.agrarian.staples.dependents_suffer",), used_by=()),
        KeystoneUse.RITE: Defined(
            "Rites",
            checked_by=(),
            used_by=("db.tables.agrarian.KeystoneResourceRow", "engine.agrarian.staples.designate", "services.player.agrarian.KeystoneDraft"),
        ),
    },
)

NUTRIENT_KIND = total(
    NutrientKind,
    {
        NutrientKind.FIXED: Defined(
            "Fixed element",
            checked_by=("engine.agrarian.soil.nutrient_change",),
            used_by=("engine.agrarian.book.BODY", "services.player.agrarian.NutrientDraft"),
        ),
        NutrientKind.MINERAL: Defined(
            "Minerals", checked_by=("engine.agrarian.soil.nutrient_change",), used_by=("engine.agrarian.book.BODY", "engine.phases.disasters.silt_land")
        ),
        NutrientKind.ORGANIC: Defined("Organic matter", checked_by=("engine.agrarian.soil.nutrient_change",), used_by=("engine.agrarian.book.BODY",)),
        NutrientKind.SALINITY: Defined(
            "Salt",
            checked_by=(
                "agents.context.agrarian_lines.son_agrarian_lines",
                "api.routers.map.agrarian_by_region",
                "engine.agrarian.soil.feed_soils",
                "engine.nature.microbes.keep_microbiota",
            ),
            used_by=("engine.agrarian.book.readout",),
        ),
    },
)

PREPAREDNESS_KIND = total(
    PreparednessKind,
    {
        PreparednessKind.LEVEE: Defined(
            "Levees", checked_by=(), used_by=("engine.agrarian.book.SHIELDS", "engine.agrarian.resilience.wishes", "services.player.agrarian.WorkDraft")
        ),
        PreparednessKind.FIREBREAK: Defined("Firebreaks", checked_by=(), used_by=("engine.agrarian.book.FIRE_SHIELDS", "engine.agrarian.resilience.wishes")),
        PreparednessKind.STOCKPILE: Defined(
            "Stockpiles", checked_by=("engine.agrarian.book.famine_cushions",), used_by=("engine.agrarian.book.SHIELDS", "engine.agrarian.resilience.wishes")
        ),
        PreparednessKind.DRILL: Defined("Drills", checked_by=(), used_by=("engine.agrarian.book.SHIELDS", "engine.agrarian.resilience.wishes")),
        PreparednessKind.WATCHTOWER: Defined(
            "Watchtowers",
            checked_by=("engine.agrarian.book.shield_cut", "engine.agrarian.book.shield_of"),
            used_by=("engine.agrarian.resilience.prepare", "engine.agrarian.resilience.wishes"),
        ),
        PreparednessKind.SEAWALL: Defined("Seawalls", checked_by=(), used_by=("engine.agrarian.book.SHIELDS", "engine.agrarian.resilience.wishes")),
        PreparednessKind.QUARANTINE_PLAN: Defined(
            "Quarantine plan", checked_by=(), used_by=("engine.agrarian.book.SHIELDS", "engine.agrarian.resilience.wishes")
        ),
        PreparednessKind.SHELTERS: Defined("Shelters", checked_by=(), used_by=("engine.agrarian.book.SHIELDS", "engine.agrarian.resilience.wishes")),
        PreparednessKind.WARNING_NETWORK: Defined(
            "Warning network", checked_by=(), used_by=("engine.agrarian.book.SHIELDS", "engine.agrarian.resilience.wishes")
        ),
        PreparednessKind.EVACUATION_ROUTES: Defined(
            "Evacuation routes",
            checked_by=(),
            used_by=("engine.agrarian.book.FIRE_SHIELDS", "engine.agrarian.book.SHIELDS", "engine.agrarian.resilience.wishes"),
        ),
        PreparednessKind.WARD: Defined(
            "Ward", checked_by=(), used_by=("engine.agrarian.book.FIRE_SHIELDS", "engine.agrarian.book.SHIELDS", "engine.agrarian.resilience.wishes")
        ),
        PreparednessKind.RESERVES_OF_ENERGY: Defined(
            "Reserves of energy", checked_by=(), used_by=("engine.agrarian.book.SHIELDS", "engine.agrarian.resilience.wishes")
        ),
    },
)

REBUILD_CAUSE = total(
    RebuildCause,
    {
        RebuildCause.FIRE: Defined(
            "Fire", checked_by=(), used_by=("engine.agrarian.resilience.SEIZING", "engine.settlement.life.fires", "services.player.agrarian.RebuildDraft")
        ),
        RebuildCause.FLOOD: Defined("Flood", checked_by=(), used_by=("engine.agrarian.ruin.CAUSES",)),
        RebuildCause.QUAKE: Defined("Quake", checked_by=(), used_by=("engine.agrarian.ruin.CAUSES",)),
        RebuildCause.STORM: Defined("Storm", checked_by=(), used_by=("engine.agrarian.ruin.CAUSES",)),
        RebuildCause.SACK: Defined("Sack", checked_by=(), used_by=("engine.agrarian.resilience.SEIZING", "engine.agrarian.ruin.CAUSES")),
    },
)

REBUILD_PLAN = total(
    RebuildPlan,
    {
        RebuildPlan.PLANNED: Defined(
            "Planned anew",
            checked_by=("engine.agrarian.resilience.finish", "engine.agrarian.resilience.plan_rebuild", "engine.agrarian.resilience.rebuild"),
            used_by=("engine.agrarian.resilience.plan_rebuild", "services.player.agrarian.RebuildDraft", "tools.mortal.agrarian.plan_rebuilding"),
        ),
        RebuildPlan.OPPORTUNISTIC: Defined(
            "Hasty, as before", checked_by=("engine.agrarian.resilience.rebuild",), used_by=("db.tables.agrarian.ReconstructionRow",)
        ),
    },
)
