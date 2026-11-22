from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.civilization import TierCapability

TIER_CAPABILITY = total(
    TierCapability,
    {
        TierCapability.EXPEDITION: Defined(
            "Expedition",
            checked_by=(),
            used_by=(
                "catalog.civilization.TIER_UNLOCKS",
                "engine.phases.travel.send_expedition",
                "engine.phases.travel.spontaneous_expeditions",
                "tools.mortal.registry.TIER_GATES",
            ),
        ),
        TierCapability.COLONY: Defined(
            "Colony",
            checked_by=(),
            used_by=(
                "catalog.civilization.TIER_UNLOCKS",
                "catalog.life.phases.INTENT_CAPABILITY",
                "catalog.life.tools.INTENT_TIERS",
                "engine.interworld.migrations.blocked",
                "engine.phases.travel.choose_intent",
            ),
        ),
        TierCapability.CONQUEST: Defined(
            "Conquest", checked_by=(), used_by=("catalog.civilization.TIER_UNLOCKS", "catalog.life.phases.INTENT_CAPABILITY", "catalog.life.tools.INTENT_TIERS")
        ),
        TierCapability.ROUTE_SEARCH: Defined(
            "Route search",
            checked_by=(),
            used_by=("catalog.civilization.TIER_UNLOCKS", "engine.phases.exploration.cosmic_exploration", "tools.mortal.registry.TIER_GATES"),
        ),
        TierCapability.SHIPBUILDING: Defined("Shipbuilding", checked_by=(), used_by=("catalog.civilization.TIER_UNLOCKS", "tools.mortal.registry.TIER_GATES")),
        TierCapability.INTERWORLD_TREATY: Defined(
            "Interworld treaty", checked_by=(), used_by=("catalog.civilization.TIER_UNLOCKS", "engine.phases.civilization._top_communities")
        ),
        TierCapability.FEDERATION: Defined(
            "Federation", checked_by=(), used_by=("catalog.civilization.TIER_UNLOCKS", "engine.phases.civilization.federations")
        ),
        TierCapability.LOAN: Defined(
            "Loan", checked_by=(), used_by=("catalog.civilization.TIER_UNLOCKS", "engine.phases.civilization.may_lend", "tools.mortal.registry.TIER_GATES")
        ),
        TierCapability.EXPLORATION: Defined(
            "Exploration",
            checked_by=(),
            used_by=("catalog.civilization.TIER_UNLOCKS", "engine.phases.exploration._may_explore", "tools.mortal.registry.TIER_GATES"),
        ),
        TierCapability.DEPOSIT_CLAIM: Defined(
            "Deposit claim", checked_by=(), used_by=("catalog.civilization.TIER_UNLOCKS", "tools.mortal.production.claim_resource")
        ),
    },
)
