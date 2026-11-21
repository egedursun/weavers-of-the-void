from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.orders import OrderLabour, OwnershipRegime, SavingForm, TouristSight

ORDER_LABOUR = total(
    OrderLabour,
    {
        OrderLabour.FREE: Defined(
            "Free",
            checked_by=(),
            used_by=(
                "db.tables.orders.EconomicOrderRow",
                "engine.orders.economy.BUILT_IN",
                "engine.orders.economy.FREE_LABOUR",
                "engine.orders.economy.TARGETS",
                "engine.orders.economy.read_order",
                "services.player.orders.EconomicOrderDraft",
                "services.player.orders.EconomicOrderKindDraft",
            ),
        ),
        OrderLabour.KIN: Defined("Kin", checked_by=(), used_by=("engine.orders.economy.BUILT_IN",)),
        OrderLabour.CORVEE: Defined(
            "Corvée",
            checked_by=(),
            used_by=(
                "engine.orders.economy.BOUND_LABOUR",
                "engine.orders.economy.BUILT_IN",
                "engine.orders.economy.read_order",
                "engine.orders.pressures.BOUND_LABOUR",
            ),
        ),
        OrderLabour.SERF: Defined(
            "Tied to the land",
            checked_by=("engine.orders.economy.read_order",),
            used_by=(
                "engine.orders.economy.BOUND_LABOUR",
                "engine.orders.economy.BUILT_IN",
                "engine.orders.economy.read_order",
                "engine.orders.pressures.BOUND_LABOUR",
            ),
        ),
        OrderLabour.BOUND: Defined("Bound", checked_by=(), used_by=("engine.orders.economy.BOUND_LABOUR", "engine.orders.pressures.BOUND_LABOUR")),
        OrderLabour.ENSLAVED: Defined(
            "Enslaved",
            checked_by=(),
            used_by=("engine.orders.economy.BOUND_LABOUR", "engine.orders.economy.read_order", "engine.orders.pressures.BOUND_LABOUR"),
        ),
        OrderLabour.CONSCRIPTED: Defined("Conscripted", checked_by=(), used_by=("engine.orders.economy.BOUND_LABOUR", "engine.orders.economy.BUILT_IN")),
        OrderLabour.COOPERATIVE: Defined("Cooperative", checked_by=(), used_by=("engine.orders.economy.FREE_LABOUR",)),
        OrderLabour.MADE: Defined("Made minds", checked_by=(), used_by=()),
    },
)

OWNERSHIP_REGIME = total(
    OwnershipRegime,
    {
        OwnershipRegime.HOUSEHOLD: Defined(
            "Households",
            checked_by=("engine.orders.economy.owner_for",),
            used_by=(
                "db.tables.orders.EconomicOrderRow",
                "engine.orders.economy.BUILT_IN",
                "engine.orders.economy.TARGETS",
                "engine.orders.economy.read_order",
                "engine.orders.economy.transfer_holdings",
                "services.player.orders.EconomicOrderDraft",
                "services.player.orders.EconomicOrderKindDraft",
            ),
        ),
        OwnershipRegime.KIN_GROUP: Defined("Kin groups", checked_by=("engine.orders.economy.owner_for",), used_by=("engine.orders.economy.BUILT_IN",)),
        OwnershipRegime.COMMUNITY: Defined("The community", checked_by=("engine.orders.economy.owner_for",), used_by=("engine.orders.pressures.CENTRAL_LAND",)),
        OwnershipRegime.TEMPLE: Defined(
            "Temples", checked_by=(), used_by=("engine.orders.economy.BUILT_IN", "engine.orders.economy.read_order", "engine.orders.pressures.HELD_LAND")
        ),
        OwnershipRegime.RULER: Defined(
            "The ruler",
            checked_by=("engine.orders.economy.owner_for",),
            used_by=(
                "engine.orders.economy.BUILT_IN",
                "engine.orders.economy.read_order",
                "engine.orders.pressures.CENTRAL_LAND",
                "engine.orders.pressures.HELD_LAND",
            ),
        ),
        OwnershipRegime.STATE: Defined(
            "The state",
            checked_by=("engine.orders.economy.owner_for",),
            used_by=("engine.orders.economy.BUILT_IN", "engine.orders.economy.TARGETS", "engine.orders.pressures.CENTRAL_LAND"),
        ),
        OwnershipRegime.PRIVATE: Defined(
            "Private owners", checked_by=("engine.orders.economy.owner_for",), used_by=("engine.orders.economy.TARGETS", "engine.orders.pressures.HELD_LAND")
        ),
        OwnershipRegime.COOPERATIVE: Defined("Cooperatives", checked_by=("engine.orders.economy.owner_for",), used_by=("engine.orders.economy.TARGETS",)),
        OwnershipRegime.COMPANY: Defined("Companies", checked_by=("engine.orders.economy.owner_for",), used_by=("engine.orders.pressures.HELD_LAND",)),
        OwnershipRegime.COMMON: Defined("Held in common", checked_by=("engine.orders.economy.owner_for",), used_by=()),
        OwnershipRegime.NONE: Defined("No one", checked_by=(), used_by=()),
    },
)

SAVING_FORM = total(
    SavingForm,
    {
        SavingForm.HOARD: Defined(
            "Buried hoard",
            checked_by=("engine.orders.savings.put_by",),
            used_by=("db.tables.orders.SavingRow", "engine.orders.savings.form_for", "services.player.orders.SavingDraft"),
        ),
        SavingForm.DEPOSIT: Defined("Bank deposit", checked_by=("engine.orders.savings.put_by",), used_by=("engine.orders.savings.form_for",)),
        SavingForm.INVESTMENT: Defined("Investment", checked_by=(), used_by=("engine.orders.savings.form_for",)),
    },
)

TOURIST_SIGHT = total(
    TouristSight,
    {
        TouristSight.WONDER: Defined("Wonder", checked_by=(), used_by=("engine.orders.tourism.SIGHT_KINDS", "services.player.orders.TouristFlowDraft")),
        TouristSight.BATHS: Defined("Baths", checked_by=(), used_by=("engine.orders.tourism.SIGHT_KINDS",)),
        TouristSight.SACRED: Defined("Holy place", checked_by=(), used_by=("engine.orders.tourism.SIGHT_KINDS",)),
        TouristSight.BATTLEFIELD: Defined("Battlefield", checked_by=(), used_by=("engine.orders.tourism.sights_of",)),
        TouristSight.CITY: Defined("Great city", checked_by=(), used_by=("engine.orders.tourism.sights_of",)),
        TouristSight.COLLECTION: Defined("Collection", checked_by=(), used_by=("engine.orders.tourism.sights_of",)),
        TouristSight.GARDEN: Defined("Garden", checked_by=(), used_by=("engine.orders.tourism.sights_of",)),
    },
)
