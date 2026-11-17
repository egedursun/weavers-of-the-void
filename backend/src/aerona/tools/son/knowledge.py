from typing import Annotated, Any

from pydantic import Field

from aerona.catalog.gates import Gate
from aerona.catalog.theories import DOMAINS
from aerona.constants.tool_inputs import DESCRIPTION_MAX, DESCRIPTION_MIN, NAME_MAX, NAME_MIN, REASON_MAX, REASON_MIN
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.discovery import TheoryDomain
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.gods.progress import power_ceiling
from aerona.engine.lore.theories import Revelation, reveal
from aerona.engine.phases.knowledge_levels import shift_level
from aerona.engine.primitives.knowledge import knowledge_level
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, gate, son_standard_action
from aerona.tools.framework.validation import fail, require_canon, require_type
from aerona.tools.son.support import ensure_in_reach, grant


class AdvanceInput(ToolInput):
    knowledge_id: int
    how: Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]


async def advance_knowledge(call: SonCall, args: AdvanceInput) -> str:
    table = call.rules.knowledge
    knowledge = await require_canon(call.session, args.knowledge_id)
    require_type(knowledge, {EntityType.KNOWLEDGE}, SonResult.NOT_KNOWLEDGE)
    await ensure_in_reach(call, knowledge)
    ceiling = min(table.level_cap, power_ceiling(call.rules, call.son) * table.son_level_per_power)
    if knowledge_level(call.rules, knowledge) >= ceiling:
        fail(SonResult.KNOWLEDGE_CEILING, name=knowledge.name, ceiling=ceiling)
    if call.son.essence < table.son_advance_cost:
        fail(SonResult.TEACH_ESSENCE, cost=table.son_advance_cost)
    level = shift_level(call.rules, knowledge, 1)
    if level is None:
        fail(SonResult.KNOWLEDGE_CEILING, name=knowledge.name, ceiling=table.level_cap)
    call.spend_essence(table.son_advance_cost)
    call.target(knowledge.id)
    gained = await grant(call, call.son, call.rules.son_tools.knowledge_xp, call.rules.son_tools.knowledge_renown)
    await call.record(
        "tools.son.advance_knowledge",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.SUBJECT: knowledge.id},
        facts={"level": level, "how": str(args.how)},
        kind=ChronicleKind.KNOWLEDGE,
    )
    return result(SonResult.KNOWLEDGE_ADVANCED, name=knowledge.name, level=level, gained=gained)


class RevealInput(ToolInput):
    community_id: int
    domain: TheoryDomain
    theory_id: int | None = None
    name: Annotated[str, Field(min_length=NAME_MIN, max_length=NAME_MAX)] | None = None
    claim: Annotated[str, Field(min_length=DESCRIPTION_MIN, max_length=DESCRIPTION_MAX)] | None = None


async def reveal_truth(call: SonCall, args: RevealInput) -> str:
    table = call.rules.theories
    community = await require_canon(call.session, args.community_id)
    require_type(community, set(COMMUNITY_TYPES), SonResult.REVEAL_PLACE)
    await ensure_in_reach(call, community)
    if args.theory_id is not None:
        theory = await require_canon(call.session, args.theory_id)
        require_type(theory, {EntityType.THEORY}, SonResult.NOT_A_THEORY)
    if call.son.essence < table.reveal_cost:
        fail(SonResult.TEACH_ESSENCE, cost=table.reveal_cost)
    domain_label = DOMAINS[args.domain].label.lower()
    told = Revelation(
        son_id=call.son.id,
        theory_id=args.theory_id,
        domain=args.domain,
        name=args.name or f"The true account of {domain_label}",
        claim=args.claim or f"What is true of {DOMAINS[args.domain].subject}.",
    )
    profile = await reveal(call.tick, community, told)
    theory_row = await call.session.get_one(EntityRow, profile.theory_entity_id)
    call.spend_essence(table.reveal_cost)
    call.target(theory_row.id)
    gained = await grant(call, call.son, call.rules.son_tools.knowledge_xp, call.rules.son_tools.knowledge_renown)
    domain = DOMAINS[profile.domain].label.lower()
    await call.record(
        "tools.son.reveal_truth",
        roles={IncidentRole.ACTOR: call.son.id, IncidentRole.PLACE: community.id, IncidentRole.SUBJECT: theory_row.id},
        facts={"domain": domain},
        place=community.id,
        kind=ChronicleKind.KNOWLEDGE,
    )
    return result(SonResult.TRUTH_REVEALED, place=community.name, id=theory_row.id, name=theory_row.name, domain=domain, gained=gained)


def specs() -> list[ToolSpec[SonCall, Any]]:
    return [
        ToolSpec(
            SonToolId.ADVANCE_KNOWLEDGE,
            AgentKind.SON,
            AdvanceInput,
            ToolMeta(
                ActionKind.ADVANCE_KNOWLEDGE,
                son_standard_action,
                essence_cost=lambda rules: rules.knowledge.son_advance_cost,
                rarity_gate=gate(Gate.INFLUENCE_TOOLS),
            ),
            advance_knowledge,
        ),
        ToolSpec(
            SonToolId.REVEAL_TRUTH,
            AgentKind.SON,
            RevealInput,
            ToolMeta(
                ActionKind.ADVANCE_KNOWLEDGE,
                son_standard_action,
                essence_cost=lambda rules: rules.theories.reveal_cost,
                rarity_gate=gate(Gate.INFLUENCE_TOOLS),
            ),
            reveal_truth,
        ),
    ]
