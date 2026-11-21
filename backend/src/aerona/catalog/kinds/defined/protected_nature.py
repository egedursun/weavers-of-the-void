from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.protected_nature import ProtectedUse, ProtectionMeasure

PROTECTED_USE = total(
    ProtectedUse,
    {
        ProtectedUse.HUNTING: Defined(
            "Hunting",
            checked_by=("engine.protected_nature.book.hunting_marks",),
            used_by=(
                "engine.protected_nature.areas.apply_legacy",
                "engine.protected_nature.areas.recover",
                "engine.protected_nature.movement.AIMS",
                "tools.son.protected_nature.hallow_wild",
            ),
        ),
        ProtectedUse.LOGGING: Defined(
            "Logging",
            checked_by=("engine.protected_nature.areas.recover",),
            used_by=(
                "engine.protected_nature.areas.apply_legacy",
                "engine.protected_nature.book.LIVELIHOODS",
                "engine.protected_nature.movement.AIMS",
                "tools.son.protected_nature.hallow_wild",
            ),
        ),
        ProtectedUse.FARMING: Defined("Farming", checked_by=("engine.protected_nature.areas.recover",), used_by=("engine.protected_nature.book.LIVELIHOODS",)),
        ProtectedUse.MINING: Defined("Mining", checked_by=(), used_by=("engine.protected_nature.book.LIVELIHOODS",)),
        ProtectedUse.SETTLEMENT: Defined(
            "Settlement", checked_by=(), used_by=("engine.protected_nature.areas.recover", "engine.protected_nature.book.LIVELIHOODS")
        ),
        ProtectedUse.ENTRY: Defined("Entry", checked_by=(), used_by=("engine.protected_nature.areas.recover",)),
        ProtectedUse.FISHING: Defined("Fishing", checked_by=(), used_by=("engine.protected_nature.areas.recover", "engine.protected_nature.book.LIVELIHOODS")),
        ProtectedUse.BUILDING: Defined(
            "Building", checked_by=(), used_by=("engine.protected_nature.areas.recover", "engine.protected_nature.book.LIVELIHOODS")
        ),
    },
)

PROTECTION_MEASURE = total(
    ProtectionMeasure,
    {
        ProtectionMeasure.HUNTING_BAN: Defined(
            "Hunting ban", checked_by=("engine.protected_nature.book.spared_species",), used_by=("engine.protected_nature.movement.AIMS",)
        ),
        ProtectionMeasure.TRADE_BAN: Defined("Trade ban", checked_by=(), used_by=()),
        ProtectionMeasure.BREEDING_PROGRAMME: Defined("Breeding programme", checked_by=("engine.protected_nature.species.tend_species",), used_by=()),
        ProtectionMeasure.REINTRODUCTION: Defined("Reintroduction", checked_by=("engine.protected_nature.species.tend_species",), used_by=()),
        ProtectionMeasure.HABITAT_GUARD: Defined("Habitat guard", checked_by=("engine.protected_nature.species.tend_species",), used_by=()),
    },
)
