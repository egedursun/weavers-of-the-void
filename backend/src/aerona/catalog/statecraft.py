from collections.abc import Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.statecraft import CouncilTask, CourtPosition, CrisisDemand, MandateKind, ResolutionKind


@dataclass(frozen=True)
class DemandSpec:
    text: str
    weight: str
    person: bool = False
    peaceful: bool = False


DEMANDS: Mapping[CrisisDemand, DemandSpec] = total(
    CrisisDemand,
    {
        CrisisDemand.CEDE_REGION: DemandSpec("cede a land", "cede_region_weight"),
        CrisisDemand.RELEASE_VASSAL: DemandSpec("release a vassal", "release_vassal_weight"),
        CrisisDemand.CONVERT: DemandSpec("take up its faith", "convert_weight"),
        CrisisDemand.PAY: DemandSpec("pay what it owes", "pay_weight"),
        CrisisDemand.HAND_OVER: DemandSpec("hand over one who shelters with it", "hand_over_weight", person=True, peaceful=True),
        CrisisDemand.DISARM: DemandSpec("cut its forces", "disarm_weight", peaceful=True),
        CrisisDemand.OPEN_TRADE: DemandSpec("open its roads and ports to trade", "open_trade_weight", peaceful=True),
    },
)

DEMAND_TEXT: Mapping[CrisisDemand, str] = total(CrisisDemand, {demand: spec.text for demand, spec in DEMANDS.items()})

PERSON_DEMANDS = frozenset(demand for demand, spec in DEMANDS.items() if spec.person)
YIELDED_DEMANDS = frozenset(demand for demand, spec in DEMANDS.items() if spec.peaceful)


@dataclass(frozen=True)
class TaskSpec:
    text: str
    effect: str
    gain: bool = False


COUNCIL_TASKS: Mapping[CouncilTask, TaskSpec] = total(
    CouncilTask,
    {
        CouncilTask.IMPROVE_RELATIONS: TaskSpec("court a neighbour", "improve_relations_effect"),
        CouncilTask.TRAIN_TROOPS: TaskSpec("drill the armies", "train_troops_effect"),
        CouncilTask.COLLECT_TAXES: TaskSpec("gather the taxes", "collect_taxes_effect"),
        CouncilTask.DISRUPT_SCHEMES: TaskSpec("break schemes against the realm", "disrupt_schemes_effect"),
        CouncilTask.CONVERT_PROVINCE: TaskSpec("turn a land to the realm's faith", "convert_province_effect"),
        CouncilTask.PURGE_CORRUPTION: TaskSpec("purge corruption", "purge_corruption_effect"),
        CouncilTask.OVERSEE_WORKS: TaskSpec("oversee the realm's works", "oversee_works_effect", gain=True),
        CouncilTask.PROMOTE_TRADE: TaskSpec("promote trade on the realm's roads", "promote_trade_effect", gain=True),
        CouncilTask.ADVANCE_LEARNING: TaskSpec("advance the realm's learning", "advance_learning_effect", gain=True),
    },
)

MANDATE_TEXT: Mapping[MandateKind, str] = total(
    MandateKind,
    {
        MandateKind.PRODUCE: "make a quota of goods",
        MandateKind.EXPORT_BAN: "keep a good from leaving",
        MandateKind.BUILD: "build a quarter",
        MandateKind.FAMINE_RELIEF: "send grain to the hungry",
        MandateKind.CURFEW: "keep folk indoors at night",
        MandateKind.SLUM_CLEARANCE: "clear the slums",
        MandateKind.PREPARE: "prepare against disaster",
        MandateKind.ENCLOSURE: "enclose the commons",
        MandateKind.RATION: "share food and fuel by rule",
        MandateKind.CORVEE: "call out labour for the works",
    },
)

POSITION_TEXT: Mapping[CourtPosition, str] = total(
    CourtPosition,
    {
        CourtPosition.STEWARD: "keeps the household's accounts",
        CourtPosition.CHAMPION: "fights in the ruler's name",
        CourtPosition.PHYSICIAN: "tends the ruler's health",
        CourtPosition.TUTOR: "teaches the heir",
        CourtPosition.CHRONICLER: "writes the reign down",
        CourtPosition.MASTER_OF_REVELS: "keeps the court's feasts",
        CourtPosition.JESTER: "may mock the ruler",
        CourtPosition.SEER: "reads signs for the court",
    },
)

RESOLUTION_TEXT: Mapping[ResolutionKind, str] = total(
    ResolutionKind,
    {
        ResolutionKind.ROUTE_SECURITY: "guard the routes between its worlds",
        ResolutionKind.EMBARGO: "embargo a realm",
        ResolutionKind.VOID_BAN: "ban rites of the void",
        ResolutionKind.SANCTION: "sanction the world of a god",
        ResolutionKind.QUARANTINE: "close the routes to a world struck by plague",
        ResolutionKind.ARBITRATION: "settle a dispute between two of its members",
        ResolutionKind.AID: "pool relief for a world struck by disaster",
    },
)
