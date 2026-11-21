from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.labour import WorkerAct

WORKER_ACT = total(
    WorkerAct,
    {
        WorkerAct.STRIKE: Defined("Strike", checked_by=(), used_by=()),
        WorkerAct.GO_SLOW: Defined("Go slow", checked_by=(), used_by=()),
        WorkerAct.BOYCOTT: Defined("Boycott", checked_by=(), used_by=()),
        WorkerAct.OCCUPATION_OF_WORKS: Defined("Occupation of works", checked_by=(), used_by=()),
        WorkerAct.SABOTAGE: Defined("Sabotage", checked_by=(), used_by=()),
    },
)
