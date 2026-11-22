from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.folkways import LuckReach, Purification

LUCK_REACH = total(
    LuckReach,
    {
        LuckReach.HARVEST: Defined("Harvest", checked_by=(), used_by=("engine.folkways.mishaps.HARVEST", "services.player.folkways.BeliefDraft")),
        LuckReach.HEALTH: Defined("Health", checked_by=(), used_by=("engine.folkways.mishaps.HEALTH",)),
        LuckReach.BIRTH: Defined("Birth", checked_by=(), used_by=("engine.folkways.mishaps.REACHES",)),
        LuckReach.JOURNEY: Defined("Journeys", checked_by=(), used_by=("engine.folkways.mishaps.JOURNEY",)),
        LuckReach.BATTLE: Defined("Battle", checked_by=("engine.folkways.fed.battle_luck",), used_by=("engine.folkways.mishaps.REACHES",)),
    },
)

PURIFICATION = total(
    Purification,
    {
        Purification.TIME: Defined("Waiting", checked_by=("engine.folkways.purity.defile", "engine.folkways.purity.purify"), used_by=()),
        Purification.WASHING: Defined("Washing", checked_by=(), used_by=("services.player.folkways.MethodDraft",)),
        Purification.FASTING: Defined("Fasting", checked_by=(), used_by=()),
        Purification.OFFERING: Defined("An offering", checked_by=(), used_by=()),
        Purification.RITE: Defined("A rite", checked_by=(), used_by=()),
        Purification.CONFESSION: Defined("Confession", checked_by=(), used_by=()),
        Purification.PAYMENT: Defined("A payment", checked_by=(), used_by=()),
        Purification.ORDEAL: Defined("An ordeal", checked_by=(), used_by=()),
    },
)
