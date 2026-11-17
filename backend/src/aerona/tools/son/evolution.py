from typing import Annotated, Any

from pydantic import Field

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityType
from aerona.domain.enums.evolution import PlagueResponse
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.disease.responses import take_up
from aerona.engine.ecology.lineages import BLESSING, TAINT, mark
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail, require_canon, require_type
from aerona.tools.son.support import ensure_in_reach

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]
TAINTING = frozenset({Domain.DEATH, Domain.PLAGUE, Domain.MADNESS, Domain.SHADOW, Domain.BLOOD, Domain.HUNGER})
INSPIRED = 70


class MarkLineageInput(ToolInput):
    species_id: int
    taint: bool = False
    reason: Reason


class MovePlagueResponseInput(ToolInput):
    community_id: int
    disease_id: int
    response: PlagueResponse
    reason: Reason


async def mark_lineage(call: SonCall, args: MarkLineageInput) -> str:
    species = require_type(
        await require_canon(call.session, args.species_id), frozenset({EntityType.SPECIES}), SonResult.LINEAGE_REFUSED, why="only a species has a line"
    )
    await ensure_in_reach(call, species)
    if args.taint and not {call.son.domain_primary, call.son.domain_secondary} & TAINTING:
        fail(SonResult.LINEAGE_REFUSED, why="tainting a line is not in your domains")
    await mark(call.tick, species, TAINT if args.taint else BLESSING, blessing=not args.taint, source_node_id=call.son.id)
    call.target(species.id)
    word = "tainted" if args.taint else "blessed"
    await call.record(
        "tools.son.mark_lineage",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: species.id},
        facts={"word": str(word), "reason": args.reason},
        kind=ChronicleKind.WORLD,
    )
    return result(SonResult.LINEAGE_MARKED, name=species.name, word=word)


async def move_plague_response(call: SonCall, args: MovePlagueResponseInput) -> str:
    community = require_type(
        await require_canon(call.session, args.community_id), COMMUNITY_TYPES, SonResult.PLAGUE_RESPONSE_REFUSED, why="only a community answers a sickness"
    )
    disease = require_type(
        await require_canon(call.session, args.disease_id), frozenset({EntityType.DISEASE}), SonResult.PLAGUE_RESPONSE_REFUSED, why="that is no sickness"
    )
    await ensure_in_reach(call, community)
    await take_up(call.tick, community, disease.id, args.response, strength=INSPIRED)
    call.target(community.id)
    response = args.response.value.replace("_", " ")
    await call.record(
        "tools.son.move_plague_response",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: [community.id, disease.id]},
        facts={"response": str(response), "reason": args.reason},
        kind=ChronicleKind.WORLD,
    )
    return result(SonResult.PLAGUE_RESPONSE_MOVED, name=community.name, response=response)


def specs() -> list[ToolSpec[SonCall, Any]]:
    son = AgentKind.SON
    meta = ToolMeta(ActionKind.INFLUENCE, son_standard_action)
    return [
        ToolSpec(SonToolId.MARK_LINEAGE, son, MarkLineageInput, meta, mark_lineage),
        ToolSpec(SonToolId.MOVE_PLAGUE_RESPONSE, son, MovePlagueResponseInput, meta, move_plague_response),
    ]
