from aerona.catalog.kinds.definition import Defined
from aerona.core.total import total
from aerona.domain.enums.fossil import FossilReading

FOSSIL_READING = total(
    FossilReading,
    {
        FossilReading.UNREAD: Defined(
            "Unread", checked_by=("engine.ecology.fossils.reveal",), used_by=("db.tables.fossils.FossilBedRow", "engine.ecology.fossils.reading_of")
        ),
        FossilReading.LEGEND: Defined("Remains of legend", checked_by=("engine.ecology.fossils.told",), used_by=("engine.ecology.fossils.READINGS",)),
        FossilReading.RELIC: Defined("Sacred relics", checked_by=("engine.ecology.fossils.told",), used_by=("engine.ecology.fossils.READINGS",)),
        FossilReading.DEEP_TIME: Defined("Evidence of deep time", checked_by=("engine.ecology.fossils.told",), used_by=("engine.ecology.fossils.READINGS",)),
    },
)
