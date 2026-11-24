from collections.abc import Mapping
from types import MappingProxyType

from aerona.domain.enums.demography import Job
from aerona.domain.enums.disease import DiseaseTarget
from aerona.domain.enums.evolution import PlagueResponse
from aerona.domain.enums.mind import ValueAxis

TARGET_JOBS: Mapping[DiseaseTarget, frozenset[Job]] = MappingProxyType(
    {
        DiseaseTarget.BREATH: frozenset({Job.FARMING, Job.HERDING, Job.FISHING, Job.MINING, Job.BUILDING, Job.SOLDIERING}),
        DiseaseTarget.VITAL: frozenset(Job),
        DiseaseTarget.COGNITION: frozenset({Job.SCHOLARSHIP, Job.CLERGY, Job.TRADE, Job.CRAFTING}),
        DiseaseTarget.SIGHT: frozenset({Job.CRAFTING, Job.SCHOLARSHIP, Job.FISHING, Job.HERDING}),
        DiseaseTarget.SKIN: frozenset({Job.TRADE, Job.CLERGY}),
    }
)


LEANINGS: dict[PlagueResponse, tuple[ValueAxis, ...]] = {
    PlagueResponse.CLOSE_BORDERS: (ValueAxis.TRADITION, ValueAxis.LOYALTY),
    PlagueResponse.QUARANTINE: (ValueAxis.LAW, ValueAxis.KNOWLEDGE),
    PlagueResponse.BURN_DEAD: (ValueAxis.PURITY,),
    PlagueResponse.EXPEL_SICK: (ValueAxis.PURITY, ValueAxis.HIERARCHY),
    PlagueResponse.PRAYER: (ValueAxis.PIETY, ValueAxis.SUPERSTITION),
    PlagueResponse.SEEK_CURE: (ValueAxis.KNOWLEDGE, ValueAxis.MERCY),
    PlagueResponse.SANITATION: (ValueAxis.KNOWLEDGE, ValueAxis.PURITY),
    PlagueResponse.FLEE: (ValueAxis.KINSHIP,),
    PlagueResponse.INOCULATE: (ValueAxis.KNOWLEDGE,),
    PlagueResponse.CLOSE_GATHERINGS: (ValueAxis.LAW, ValueAxis.KNOWLEDGE),
}
