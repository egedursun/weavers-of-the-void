from typing import Annotated, Any

from pydantic import Field
from sqlalchemy import delete, select

from aerona.catalog.life.tools import THRONES
from aerona.constants.tool_inputs import REASON_MAX, REASON_MIN
from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.tables.polity import OfficeRow
from aerona.db.tables.population import PopulationInstrumentRow, PopulationPolicyRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.population import PopulationAim, PopulationInstrument
from aerona.engine.numbers.book import scope_of, towns_in
from aerona.engine.numbers.policies import numbers_of
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail

Reason = Annotated[str, Field(min_length=REASON_MIN, max_length=REASON_MAX)]
INSTRUMENTS_MAX = len(PopulationInstrument)


class InstrumentWeight(ToolInput):
    instrument: PopulationInstrument
    strength: int = Field(ge=0, le=PERCENT)


class SetPopulationPolicyInput(ToolInput):
    aim: PopulationAim
    instruments: list[InstrumentWeight] = Field(default_factory=list, max_length=INSTRUMENTS_MAX)
    target_node_id: int | None = None
    reason: Reason


async def realm_ruled_by(call: MortalCall) -> int | None:
    found = await call.session.scalar(
        select(OfficeRow.polity_entity_id).where(OfficeRow.holder_entity_id == call.me.id, OfficeRow.kind.in_(list(THRONES))).order_by(OfficeRow.id).limit(1)
    )
    return int(found) if found is not None else None


async def set_population_policy(call: MortalCall, args: SetPopulationPolicyInput) -> str:
    realm = await realm_ruled_by(call)
    if realm is None:
        fail(MortalResult.POPULATION_REFUSED, why="only one who rules a realm sets its policy on numbers")
    if held(realm):
        fail(MortalResult.POPULATION_REFUSED, why="a god holds your realm as it is")
    if args.target_node_id is not None and not set(await towns_in(call.session, args.target_node_id)) & set(await towns_in(call.session, realm)):
        fail(MortalResult.POPULATION_REFUSED, why="the policy may aim only at people or places within your realm")
    policy = await call.session.scalar(select(PopulationPolicyRow).where(PopulationPolicyRow.holder_node_id == realm).order_by(PopulationPolicyRow.id).limit(1))
    if policy is not None and {"aim", "target_node_id"} & set(policy.locked or []):
        fail(MortalResult.POPULATION_REFUSED, why="a god holds your realm's policy as it is")
    if policy is None:
        policy = PopulationPolicyRow(holder_node_id=realm, since_epoch=call.epoch, reviewed_epoch=call.epoch, locked=[])
        call.session.add(policy)
    policy.aim, policy.target_node_id, policy.reason = args.aim, args.target_node_id, args.reason
    await call.session.flush()
    policy.baseline = await numbers_of(call.tick, await scope_of(call.session, policy))
    await call.session.execute(delete(PopulationInstrumentRow).where(PopulationInstrumentRow.policy_id == policy.id))
    weights = {item.instrument: item.strength for item in args.instruments}
    call.session.add_all(
        PopulationInstrumentRow(policy_id=policy.id, instrument=kind, holder_node_id=realm, strength=strength, locked=[])
        for kind, strength in sorted(weights.items())
    )
    call.target(realm)
    await call.record(
        "population.policy_adopted",
        roles={IncidentRole.SUBJECT: realm, IncidentRole.ACTOR: call.me.id},
        facts={"aim": args.aim, "reason": args.reason},
    )
    told = ", ".join(f"{spoken(kind)} {strength}" for kind, strength in sorted(weights.items())) or "no instruments"
    return result(MortalResult.POPULATION_SET, aim=spoken(args.aim), instruments=told)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    return [
        ToolSpec(
            MortalToolId.SET_POPULATION_POLICY,
            AgentKind.MORTAL,
            SetPopulationPolicyInput,
            ToolMeta(ActionKind.ENACT_LAW, mortal_standard_action),
            set_population_policy,
        ),
    ]
