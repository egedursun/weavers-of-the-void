from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.interpretation import InterpretedEvent

INTERPRETED_EVENT = total(
    InterpretedEvent,
    {
        InterpretedEvent.PARLEY: Defined("Parley", checked_by=(), used_by=("db.tables.interpretation.InterpretationRow", "engine.couplings.field.parley")),
        InterpretedEvent.TREATY: Defined("Treaty", checked_by=(), used_by=("engine.polity.accords.misread",)),
        InterpretedEvent.TRIAL: Defined("Trial", checked_by=(), used_by=("engine.polity.trials.heard",)),
        InterpretedEvent.TRADE: Defined("Trade", checked_by=(), used_by=("engine.economy.routes.spoken_capacity",)),
        InterpretedEvent.SERMON: Defined("Sermon", checked_by=(), used_by=("engine.phases.religion_spread.preaching_barrier",)),
    },
)
