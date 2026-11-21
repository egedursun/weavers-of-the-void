from enum import StrEnum


class ReckoningMeasure(StrEnum):
    TRIBUNAL = "tribunal"
    TRUTH_INQUIRY = "truth_inquiry"
    OFFICE_BAR = "office_bar"
    AMNESTY = "amnesty"
    AMNESTY_FOR_CONFESSION = "amnesty_for_confession"
    RESTITUTION = "restitution"
    REPARATION_TO_VICTIMS = "reparation_to_victims"
    MEMORIAL = "memorial"
    RECORD_OPENING = "record_opening"


class MeasureStage(StrEnum):
    PLANNED = "planned"
    ACTIVE = "active"
    DONE = "done"


class CaseOutcome(StrEnum):
    PENDING = "pending"
    CONVICTED = "convicted"
    ACQUITTED = "acquitted"
    PARDONED = "pardoned"
    CONFESSED = "confessed"
    BARRED = "barred"


HARSH_MEASURES = frozenset({ReckoningMeasure.TRIBUNAL, ReckoningMeasure.OFFICE_BAR})
