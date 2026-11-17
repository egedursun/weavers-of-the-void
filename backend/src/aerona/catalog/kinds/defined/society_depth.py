from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.society_depth import DriftCause, LoyaltyPart

DRIFT_CAUSE = total(
    DriftCause,
    {
        DriftCause.GOD: Defined("God", checked_by=(), used_by=("engine.mind.values.pressure_causes",)),
        DriftCause.RULER: Defined("Ruler", checked_by=(), used_by=("engine.customs.revival.PRESSING", "engine.mind.values.pressure_causes")),
        DriftCause.NEIGHBOURS: Defined("Neighbours", checked_by=(), used_by=("engine.customs.revival.PRESSING", "engine.mind.values.pressure_causes")),
        DriftCause.IDEOLOGY: Defined("Ideology", checked_by=(), used_by=("engine.mind.values.experience_shift",)),
        DriftCause.WAR_FOUGHT: Defined("War fought", checked_by=(), used_by=("engine.mind.values.experience_shift",)),
        DriftCause.WAR_WON: Defined("War won", checked_by=(), used_by=("engine.mind.values.experience_shift",)),
        DriftCause.WAR_LOST: Defined("War lost", checked_by=(), used_by=("engine.mind.values.experience_shift",)),
        DriftCause.PLAGUE: Defined("Plague", checked_by=(), used_by=("engine.mind.values.experience_shift",)),
        DriftCause.FAMINE: Defined("Famine", checked_by=(), used_by=("engine.mind.values.experience_shift",)),
        DriftCause.TRADE: Defined("Trade", checked_by=(), used_by=("engine.mind.values.experience_shift",)),
        DriftCause.CONQUEST: Defined("Conquest", checked_by=(), used_by=("engine.customs.revival.PRESSING", "engine.mind.values.pressure_causes")),
    },
)

LOYALTY_PART = total(
    LoyaltyPart,
    {
        LoyaltyPart.TRIBUTE: Defined("Tribute", checked_by=(), used_by=("engine.polity.loyalty.loyalty_parts",)),
        LoyaltyPart.WEARINESS: Defined("Weariness", checked_by=(), used_by=("engine.polity.loyalty.loyalty_parts",)),
        LoyaltyPart.CONQUEST: Defined("Conquest", checked_by=(), used_by=("engine.polity.loyalty.loyalty_parts",)),
        LoyaltyPart.TAX: Defined("Tax", checked_by=(), used_by=("engine.polity.loyalty.loyalty_parts",)),
        LoyaltyPart.ROUTES: Defined("Routes", checked_by=(), used_by=("engine.polity.loyalty.loyalty_parts",)),
        LoyaltyPart.VICTORIES: Defined("Victories", checked_by=(), used_by=("engine.polity.loyalty.loyalty_parts",)),
        LoyaltyPart.FAITH: Defined("Faith", checked_by=(), used_by=("engine.polity.loyalty.loyalty_parts",)),
        LoyaltyPart.PROSPERITY: Defined("Prosperity", checked_by=(), used_by=("engine.polity.loyalty.loyalty_parts",)),
        LoyaltyPart.INJUSTICE: Defined("Injustice", checked_by=(), used_by=("engine.polity.loyalty.loyalty_parts",)),
        LoyaltyPart.IDENTITY: Defined("Identity", checked_by=(), used_by=("engine.polity.loyalty.loyalty_parts",)),
        LoyaltyPart.SEPARATISM: Defined("Separatism", checked_by=(), used_by=("engine.polity.loyalty.loyalty_parts",)),
        LoyaltyPart.SUPPRESSION: Defined("Suppression", checked_by=(), used_by=("engine.polity.loyalty.loyalty_parts",)),
    },
)
