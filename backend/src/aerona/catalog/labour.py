from dataclasses import dataclass
from types import MappingProxyType

from aerona.core.total import total
from aerona.domain.enums.demography import Job
from aerona.domain.enums.labour import DisputeAct, LabourDemand, LegalStanding, WorkerBodyForm
from aerona.domain.enums.society import KnowledgeBranch, SocialClass
from aerona.domain.enums.society_depth import LabourReason

J = Job
C = SocialClass
F = WorkerBodyForm
A = DisputeAct
L = LegalStanding
D = LabourDemand
K = KnowledgeBranch
R = LabourReason

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
        J.TRANSPORT: C.WORKER,
        J.ADMINISTRATION: C.OFFICIAL,
        J.GATHERING: C.FARMER,
        J.INDUSTRY: C.WORKER,
        J.ARTS: C.ARTISAN,
        J.HEALING: C.PROFESSIONAL,
        J.TEACHING: C.SCRIBE,
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
        J.TRANSPORT: F.GENERAL_UNION,
        J.ADMINISTRATION: F.CRAFT_UNION,
        J.GATHERING: F.MUTUAL_AID,
        J.INDUSTRY: F.INDUSTRIAL_UNION,
        J.ARTS: F.COMPANION_SOCIETY,
        J.HEALING: F.CRAFT_UNION,
        J.TEACHING: F.CRAFT_UNION,
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


@dataclass(frozen=True)
class ReasonSpec:
    label: str
    phrase: str
    chosen: bool


REASONS: MappingProxyType[LabourReason, ReasonSpec] = total(
    LabourReason,
    {
        R.CLASS: ReasonSpec("Class", "by the custom of their class", False),
        R.PRICE: ReasonSpec("Price", "drawn by prices", True),
        R.STRUCTURE: ReasonSpec("Workshop", "drawn by a workshop", True),
        R.RESOURCE: ReasonSpec("Deposit", "drawn by a worked deposit", True),
        R.NO_STRUCTURE: ReasonSpec("No workshop", "turned out for want of a workshop", False),
        R.CORVEE: ReasonSpec("Corvee", "taken by a corvee", False),
        R.HELD: ReasonSpec("Held", "held by a god", False),
        R.LAW: ReasonSpec("Law", "kept by statute, caste or guild right", False),
        R.SKILL: ReasonSpec("Skill", "drawn by what their people know", True),
        R.DEBT: ReasonSpec("Debt", "bound to a creditor's work", False),
        R.KIN_DUTY: ReasonSpec("Kin duty", "set by household and kin by role", False),
    },
)

JOB_BRANCH: MappingProxyType[Job, KnowledgeBranch | None] = total(
    Job,
    {
        J.FARMING: K.AGRICULTURE,
        J.HERDING: K.AGRICULTURE,
        J.FISHING: K.SEAFARING,
        J.MINING: K.METALLURGY,
        J.CRAFTING: K.METALLURGY,
        J.TRADE: K.TRADE,
        J.SOLDIERING: K.WARFARE,
        J.CLERGY: None,
        J.SCHOLARSHIP: K.WRITING,
        J.BUILDING: K.ARCHITECTURE,
        J.SERVICE: None,
        J.IDLE: None,
        J.TRANSPORT: K.PATHFINDING,
        J.ADMINISTRATION: K.CIVICS,
        J.GATHERING: K.AGRICULTURE,
        J.INDUSTRY: K.METALLURGY,
        J.ARTS: None,
        J.HEALING: K.MEDICINE,
        J.TEACHING: K.WRITING,
    },
)
