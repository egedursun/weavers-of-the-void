from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.customs import IntoxicantUse

INTOXICANT_USE = total(
    IntoxicantUse,
    {
        IntoxicantUse.DAILY: Defined(
            "Daily",
            checked_by=("engine.customs.intoxicants.habits",),
            used_by=(
                "catalog.life.customs.KEEP_INTOXICATION_INTOXICANT_USES",
                "catalog.life.customs.KEEP_INTOXICATION_INTOXICANT_USES_2",
                "engine.customs.intoxicants.adopt_new",
                "engine.customs.intoxicants.seed_customs",
            ),
        ),
        IntoxicantUse.FEAST: Defined(
            "At feasts",
            checked_by=("engine.customs.intoxicants.keep_intoxication",),
            used_by=(
                "catalog.life.customs.KEEP_INTOXICATION_INTOXICANT_USES",
                "db.tables.customs.IntoxicantCustomRow",
                "engine.customs.intoxicants.seed_customs",
                "services.player.customs.IntoxicantCustomDraft",
            ),
        ),
        IntoxicantUse.RITE: Defined(
            "In rites", checked_by=("engine.customs.intoxicants.keep_intoxication",), used_by=("engine.customs.intoxicants.seed_customs",)
        ),
        IntoxicantUse.MOURNING: Defined("In mourning", checked_by=("engine.customs.intoxicants.keep_intoxication",), used_by=()),
        IntoxicantUse.FORBIDDEN: Defined(
            "Forbidden",
            checked_by=("engine.customs.intoxicants.forbids", "engine.customs.intoxicants.habits", "engine.customs.intoxicants.keep_intoxication"),
            used_by=("catalog.life.customs.KEEP_INTOXICATION_INTOXICANT_USES_2",),
        ),
        IntoxicantUse.MEDICINE: Defined(
            "As medicine",
            checked_by=("engine.customs.intoxicants.keep_intoxication",),
            used_by=("catalog.life.customs.KEEP_INTOXICATION_INTOXICANT_USES_2", "engine.customs.intoxicants.adopt_new"),
        ),
        IntoxicantUse.HOSPITALITY: Defined("Offered to guests", checked_by=("engine.customs.intoxicants.keep_intoxication",), used_by=()),
    },
)
