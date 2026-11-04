from typing import Annotated, Any

from pydantic import Field

from aerona.catalog.gates import Gate
from aerona.constants.tool_inputs import NAME_MAX, NAME_MIN, REASON_MAX, REASON_MIN
from aerona.db.repositories.names import NameRepository
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.disease import ClimateAffinity, DiseaseTarget, DiseaseVector
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityType
from aerona.engine.disease.book import DiseaseBook
from aerona.engine.disease.control import DiseaseDesign, ProfileValue, land_of, loose
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, gate, son_standard_action
from aerona.tools.framework.validation import fail, require_canon, require_type
from aerona.tools.son import lines
from aerona.tools.son.support import ensure_in_reach, require_essence

PERCENT = 100
INCUBATION_MAX = 20
DISEASE_TARGETS = frozenset({EntityType.REGION, *COMMUNITY_TYPES})


class LooseDiseaseInput(ToolInput):
    target_id: int
    name: Annotated[str, Field(min_length=NAME_MIN, max_length=NAME_MAX)]
    vector: DiseaseVector
    target_functions: Annotated[list[DiseaseTarget], Field(min_length=1)]
    virulence: Annotated[int, Field(ge=1, le=PERCENT)] = 40
    lethality: Annotated[int, Field(ge=1, le=PERCENT)] = 30
    incubation: Annotated[int, Field(ge=0, le=INCUBATION_MAX)] = 1
    chronic_rate: Annotated[int, Field(ge=0, le=PERCENT)] = 10
    climate_affinity: ClimateAffinity = ClimateAffinity.ANY
    host_species_id: int | None = None
    severity: Annotated[int, Field(ge=1, le=PERCENT)] = 50
    reason: Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


def design_of(args: LooseDiseaseInput) -> DiseaseDesign:
    values: dict[str, ProfileValue] = {
        "vector": args.vector.value,
        "target_functions": [item.value for item in args.target_functions],
        "virulence": args.virulence,
        "lethality": args.lethality,
        "incubation": args.incubation,
        "chronic_rate": args.chronic_rate,
        "climate_affinity": args.climate_affinity.value,
    }
    if args.host_species_id is not None:
        values["host_species_id"] = args.host_species_id
    return DiseaseDesign(name=" ".join(args.name.split()), values=values, hold=False)


async def loose_disease(call: SonCall, args: LooseDiseaseInput) -> str:
    target = require_type(await require_canon(call.session, args.target_id), DISEASE_TARGETS, SonResult.DISEASE_TARGET)
    await ensure_in_reach(call, target)
    if await NameRepository(call.session).is_taken(args.name):
        fail(SonResult.NAME_IN_USE)
    cost = call.rules.son_tools.loose_disease_essence
    require_essence(call, cost)
    land = await land_of(call.tick, await DiseaseBook.load(call.session, call.rules, call.epoch), target)
    disease, _event = await loose(call.tick, target.id, disease_id=None, severity=args.severity, son_id=call.son.id, design=design_of(args))
    call.remember_creation(disease.id)
    call.spend_essence(cost)
    call.target(target.id)
    await call.chronicle(
        ChronicleKind.DISASTER,
        lines.LOOSE_DISEASE,
        entity_ids=[disease.id, target.id],
        son=call.son.name,
        disease=disease.name,
        target=target.name,
        reason=args.reason,
    )
    return result(SonResult.DISEASE_LOOSED, id=disease.id, name=disease.name, land=land.name, target=target.name, severity=args.severity)


def specs() -> list[ToolSpec[SonCall, Any]]:
    return [
        ToolSpec(
            SonToolId.LOOSE_DISEASE,
            AgentKind.SON,
            LooseDiseaseInput,
            ToolMeta(
                ActionKind.CURSE,
                son_standard_action,
                essence_cost=lambda rules: rules.son_tools.loose_disease_essence,
                rarity_gate=gate(Gate.RARE_TOOLS),
            ),
            loose_disease,
        )
    ]
