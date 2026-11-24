from aerona.domain.enums.affliction import Transmission
from aerona.domain.enums.faith import HoldingKind, JudgementDoctrine, TenetKind
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.structure import StructureKind

REBIRTH_PATH_OF_JUDGEMENT_DOCTRINES = frozenset({JudgementDoctrine.DEEDS, JudgementDoctrine.FAITH})
FEAR_OF_TORMENT_VALUE_AXISS = (ValueAxis.HONOUR, ValueAxis.TRADITION)
TENDED_ROUTES = frozenset(
    {Transmission.CONTACT, Transmission.BITE, Transmission.INGESTION, Transmission.INHALATION, Transmission.BLOOD, Transmission.WATER, Transmission.INTIMATE}
)
CHURCH_WORKS = (
    (StructureKind.SCHOOL, HoldingKind.SCHOOL, TenetKind.MONASTIC_LEARNING),
    (StructureKind.HOSPITAL, HoldingKind.HOSPITAL, TenetKind.ASCETICISM),
)
