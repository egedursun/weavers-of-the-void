from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.agrarian import AidKind, KeystoneUse, NutrientKind, RebuildPlan

AID_KIND = total(
    AidKind,
    {
        AidKind.GOODS: Defined(
            "Goods", checked_by=(), used_by=("engine.agrarian.resilience.aid_goods", "engine.agrarian.resilience.aid_kind", "services.player.agrarian.AidDraft")
        ),
        AidKind.HEALERS: Defined(
            "Healers",
            checked_by=("engine.agrarian.resilience.aid_kind",),
            used_by=("engine.agrarian.resilience.EVENT_AID", "engine.agrarian.resilience.aid_healers"),
        ),
        AidKind.LABOUR: Defined("Labour", checked_by=(), used_by=("engine.agrarian.resilience.aid_kind", "engine.agrarian.resilience.aid_labour")),
        AidKind.MONEY: Defined("Money", checked_by=(), used_by=("engine.agrarian.resilience.aid_kind", "engine.agrarian.resilience.aid_money")),
        AidKind.CREDIT: Defined("Credit", checked_by=(), used_by=("engine.agrarian.resilience.aid_credit", "engine.agrarian.resilience.aid_kind")),
        AidKind.FOOD: Defined("Food", checked_by=(), used_by=("engine.agrarian.resilience.EVENT_AID", "engine.agrarian.resilience.aid_food")),
        AidKind.SHELTER: Defined("Shelter", checked_by=(), used_by=("engine.agrarian.resilience.EVENT_AID", "engine.agrarian.resilience.aid_shelter")),
        AidKind.MEDICINE: Defined("Medicine", checked_by=(), used_by=("engine.agrarian.resilience.aid_kind", "engine.agrarian.resilience.aid_medicine")),
        AidKind.SOLDIERS: Defined("Soldiers", checked_by=(), used_by=("engine.agrarian.resilience.EVENT_AID", "engine.agrarian.resilience.aid_soldiers")),
        AidKind.KNOWLEDGE: Defined("Knowledge", checked_by=(), used_by=("engine.agrarian.resilience.aid_kind", "engine.agrarian.resilience.aid_knowledge")),
    },
)

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
