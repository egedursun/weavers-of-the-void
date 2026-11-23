from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.divine import CouncilSeat, DivineCost

COUNCIL_SEAT = total(
    CouncilSeat,
    {
        CouncilSeat.BY_RIGHT: Defined(
            "Sits by right",
            checked_by=("engine.divine.council_order.enact_expel", "engine.divine.council_order.foreign_members"),
            used_by=("db.tables.council_order.DivineSeatRow", "engine.divine.council_order.exclusion", "engine.divine.council_order.seat_gods"),
        ),
        CouncilSeat.INVITED: Defined("Invited", checked_by=(), used_by=("engine.divine.council_order.enact_admit", "services.player.council_order.SeatSet")),
        CouncilSeat.BY_PACT: Defined("Sits by a pact", checked_by=(), used_by=("engine.divine.council_order.seat_gods",)),
        CouncilSeat.RECOGNISED: Defined("Recognised by the gods", checked_by=(), used_by=("engine.divine.council_order.enact_recognise",)),
    },
)

DIVINE_COST = total(
    DivineCost,
    {
        DivineCost.ESSENCE: Defined(
            "Essence",
            checked_by=("engine.divine.grammar.pay",),
            used_by=(
                "db.tables.divine_powers.DivinePowerRow",
                "engine.divine.grammar.grant_by_worship",
                "engine.divine.grammar.preset_row",
                "services.player.divine_powers.DivinePowerCreate",
            ),
        ),
        DivineCost.ATTENTION: Defined("Attention", checked_by=("engine.divine.grammar.pay",), used_by=()),
        DivineCost.STANDING: Defined("Standing", checked_by=("engine.divine.grammar.pay",), used_by=()),
        DivineCost.DOMAIN: Defined("Strength of its domain", checked_by=("engine.divine.grammar.pay",), used_by=()),
        DivineCost.SACRIFICE: Defined("A sacrifice by the faithful", checked_by=("engine.divine.grammar.pay",), used_by=()),
    },
)
