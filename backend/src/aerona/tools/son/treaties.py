from typing import Any

from aerona.catalog.pacts import BREAKABLE_STATES
from aerona.db.tables.polity import TreatyProfileRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import TreatyBreach, TreatyKind
from aerona.engine.polity.accords import Clause, sign
from aerona.engine.polity.treaties import breach
from aerona.engine.services.community_relations import change_relation
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.rules.registry import Rules
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec
from aerona.tools.framework.treaty_inputs import ClauseInput, PartyInput
from aerona.tools.framework.validation import fail, require_canon
from aerona.tools.son import lines
from aerona.tools.son.support import ensure_in_reach, require_essence


class SealTreatyInput(ToolInput):
    kind: TreatyKind
    parties: list[PartyInput]
    clauses: list[ClauseInput] | None = None
    epochs: int | None = None


class VoidTreatyInput(ToolInput):
    treaty_id: int
    breaker_id: int


async def seal_treaty(call: SonCall, args: SealTreatyInput) -> str:
    tools = call.rules.son_tools
    if len(args.parties) < 2:
        fail(SonResult.TREATY_TARGETS)
    entities = []
    for party in args.parties:
        entity = await require_canon(call.session, party.party_id)
        await ensure_in_reach(call, entity)
        entities.append(entity)
    require_essence(call, tools.treaty_cost)
    clauses = [Clause(item.kind, item.obligor_id, item.beneficiary_id, item.params or {}) for item in args.clauses or []]
    epochs = max(1, min(tools.treaty_max_epochs, args.epochs)) if args.epochs else None
    treaty = await sign(
        call.tick, args.kind, [(party.party_id, party.role) for party in args.parties], clauses=clauses, until=call.epoch + epochs if epochs else None
    )
    first, second = entities[0], entities[1]
    await change_relation(call.tick, first.id, second.id, tools.treaty_relation, MemoryKind.ALLIED_WITH, note=lines.TREATY_EVENT)
    call.spend_essence(tools.treaty_cost)
    call.target(treaty.id)
    await call.record(
        "tools.son.sealed",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: [treaty.id, *[treaty.id, *[entity.id for entity in entities]]]},
        kind=ChronicleKind.DIPLOMACY,
    )
    return result(SonResult.TREATY_SEALED, name=treaty.name)


async def void_treaty(call: SonCall, args: VoidTreatyInput) -> str:
    profile = await call.session.get(TreatyProfileRow, args.treaty_id)
    if profile is None or profile.status not in BREAKABLE_STATES:
        fail(SonResult.NO_TREATY)
    breaker = await require_canon(call.session, args.breaker_id)
    await ensure_in_reach(call, breaker)
    require_essence(call, call.rules.son_tools.treaty_cost)
    await breach(call.tick, profile, breaker.id, clause=None, reason=TreatyBreach.GOD_COMMANDED, occasion=call.son.id)
    call.spend_essence(call.rules.son_tools.treaty_cost)
    call.target(profile.treaty_entity_id)
    return result(SonResult.TREATY_VOIDED, name=breaker.name)


def treaty_cost(rules: Rules) -> int:
    return rules.son_tools.treaty_cost


def specs() -> list[ToolSpec[SonCall, Any]]:
    son = AgentKind.SON
    return [
        ToolSpec(
            SonToolId.SEAL_TREATY,
            son,
            SealTreatyInput,
            ToolMeta(ActionKind.PROPOSE_TREATY, lambda rules: rules.son_tools.treaty_ap, essence_cost=treaty_cost),
            seal_treaty,
        ),
        ToolSpec(
            SonToolId.VOID_TREATY,
            son,
            VoidTreatyInput,
            ToolMeta(ActionKind.BREAK_TREATY, lambda rules: rules.son_tools.treaty_ap, essence_cost=treaty_cost),
            void_treaty,
        ),
    ]
