from typing import Annotated, Any

from pydantic import Field
from sqlalchemy import select

from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.core.grammar import spoken
from aerona.db.tables.population import PopulationPolicyRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.population import PopulationAim
from aerona.engine.numbers.book import scope_of
from aerona.engine.numbers.policies import numbers_of
from aerona.engine.primitives.queries import living_entity
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, son_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.son.support import ensure_in_reach

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]
HOLDERS = frozenset({EntityType.POLITY, EntityType.PEOPLE, EntityType.FACTION, EntityType.CULT, EntityType.SETTLEMENT})


class MovePopulationPolicyInput(ToolInput):
    holder_node_id: int
    aim: PopulationAim
    reason: Reason


async def move_population_policy(call: SonCall, args: MovePopulationPolicyInput) -> str:
    holder = await living_entity(call.session, args.holder_node_id)
    if holder is None or holder.entity_type not in HOLDERS:
        fail(SonResult.POPULATION_REFUSED, why="that holds no numbers to steer")
    await ensure_in_reach(call, holder)
    if held(holder.id):
        fail(SonResult.POPULATION_REFUSED, why="it is held")
    policy = await call.session.scalar(
        select(PopulationPolicyRow).where(PopulationPolicyRow.holder_node_id == holder.id).order_by(PopulationPolicyRow.id).limit(1)
    )
    if policy is not None and "aim" in (policy.locked or []):
        fail(SonResult.POPULATION_REFUSED, why="its aim is held")
    if policy is None:
        policy = PopulationPolicyRow(holder_node_id=holder.id, since_epoch=call.tick.epoch, reviewed_epoch=call.tick.epoch, locked=[])
        call.session.add(policy)
    before = policy.aim
    policy.aim, policy.reason = args.aim, args.reason
    await call.session.flush()
    policy.baseline = await numbers_of(call.tick, await scope_of(call.session, policy))
    call.target(holder.id)
    await call.record(
        "population.policy_adopted",
        roles={IncidentRole.SUBJECT: holder.id, IncidentRole.ACTOR: call.son.id},
        facts={"aim": args.aim, "reason": args.reason},
        kind=ChronicleKind.CIVILIZATION,
    )
    return result(SonResult.POPULATION_MOVED, holder=holder.name, aim=spoken(args.aim), before=spoken(before))


def specs() -> list[ToolSpec[SonCall, Any]]:
    return [
        ToolSpec(
            SonToolId.MOVE_POPULATION_POLICY,
            AgentKind.SON,
            MovePopulationPolicyInput,
            ToolMeta(ActionKind.INFLUENCE, son_standard_action),
            move_population_policy,
        ),
    ]
