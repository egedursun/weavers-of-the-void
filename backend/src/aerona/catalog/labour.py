from types import MappingProxyType

from aerona.core.total import total
from aerona.domain.enums.demography import Job
from aerona.domain.enums.labour import DisputeAct, LabourDemand, LegalStanding, WorkerBodyForm
from aerona.domain.enums.society import SocialClass

J = Job
C = SocialClass
F = WorkerBodyForm
A = DisputeAct
L = LegalStanding
D = LabourDemand

TRADE_CLASS: MappingProxyType[Job, SocialClass] = total(
    Job,
    {
        J.FARMING: C.FARMER,
        J.HERDING: C.FARMER,
        J.FISHING: C.FARMER,
        J.MINING: C.WORKER,
        J.CRAFTING: C.ARTISAN,
        J.TRADE: C.MERCHANT,
        J.SOLDIERING: C.WARRIOR,
        J.CLERGY: C.PRIEST,
        J.SCHOLARSHIP: C.SCRIBE,
        J.BUILDING: C.WORKER,
        J.SERVICE: C.WORKER,
        J.IDLE: C.UNEMPLOYED,
    },
)
TRADE_FORM: MappingProxyType[Job, WorkerBodyForm] = total(
    Job,
    {
        J.FARMING: F.MUTUAL_AID,
        J.HERDING: F.MUTUAL_AID,
        J.FISHING: F.MUTUAL_AID,
        J.MINING: F.INDUSTRIAL_UNION,
        J.CRAFTING: F.CRAFT_UNION,
        J.TRADE: F.GENERAL_UNION,
        J.SOLDIERING: F.MUTUAL_AID,
        J.CLERGY: F.MUTUAL_AID,
        J.SCHOLARSHIP: F.CRAFT_UNION,
        J.BUILDING: F.INDUSTRIAL_UNION,
        J.SERVICE: F.GENERAL_UNION,
        J.IDLE: F.GENERAL_UNION,
    },
)
STANDING_COVERAGE_PCT: MappingProxyType[LegalStanding, int] = total(LegalStanding, {L.BANNED: 15, L.TOLERATED: 35, L.RECOGNISED: 60, L.COMPULSORY: 100})
STANDING_STRENGTH: MappingProxyType[LegalStanding, int] = total(LegalStanding, {L.BANNED: -20, L.TOLERATED: 0, L.RECOGNISED: 15, L.COMPULSORY: 25})
FORM_STRENGTH: MappingProxyType[WorkerBodyForm, int] = total(
    WorkerBodyForm,
    {
        F.CRAFT_UNION: 10,
        F.INDUSTRIAL_UNION: 15,
        F.GENERAL_UNION: 5,
        F.COMPANION_SOCIETY: 5,
        F.MUTUAL_AID: 0,
        F.WORKER_COOPERATIVE: 0,
        F.MADE_MIND_COLLECTIVE: 20,
    },
)
ACT_OUTPUT_LOSS_PCT: MappingProxyType[DisputeAct, int] = total(
    DisputeAct,
    {A.STRIKE: 100, A.GO_SLOW: 40, A.LOCKOUT: 100, A.BOYCOTT: 0, A.OCCUPATION_OF_WORKS: 100, A.SABOTAGE: 60},
)
ACT_HIRER_COST_PCT: MappingProxyType[DisputeAct, int] = total(
    DisputeAct,
    {A.STRIKE: 100, A.GO_SLOW: 50, A.LOCKOUT: 60, A.BOYCOTT: 80, A.OCCUPATION_OF_WORKS: 130, A.SABOTAGE: 150},
)
ACT_PAID_PCT: MappingProxyType[DisputeAct, int] = total(
    DisputeAct,
    {A.STRIKE: 100, A.GO_SLOW: 0, A.LOCKOUT: 100, A.BOYCOTT: 0, A.OCCUPATION_OF_WORKS: 100, A.SABOTAGE: 20},
)
DEMAND_TERMS: MappingProxyType[LabourDemand, str | None] = total(
    LabourDemand,
    {D.WAGE: "wage", D.HOURS: "hours", D.SAFETY: "safety", D.REST: "rest", D.KEEP: "keep", D.RECOGNITION: None},
)
