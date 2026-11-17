from typing import Any

from pydantic import Field
from sqlalchemy import select

from aerona.db.tables.culture import RumourRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.tellings import RumourDistortionRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.culture import RumourChannel
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import WitnessMode
from aerona.engine.lore.account_text import account_text
from aerona.engine.lore.rumours import is_carrier
from aerona.engine.lore.witnesses import fidelity_of, tell
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail

TELL = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)


class RecountInput(ToolInput):
    incident_id: int
    step_offset: int = Field(default=0, ge=0)


async def own_fidelity(call: MortalCall, incident_id: int) -> int | None:
    rows = list(
        await call.session.execute(
            select(IncidentParticipantRow.role, IncidentParticipantRow.fidelity).where(
                IncidentParticipantRow.incident_id == incident_id, IncidentParticipantRow.node_id == call.me.id
            )
        )
    )
    if not rows:
        return None
    if any(role not in (IncidentRole.WITNESS, IncidentRole.TELLER) for role, _ in rows):
        return fidelity_of(call.rules, WitnessMode.TOOK_PART)
    seen = [fidelity for role, fidelity in rows if role is IncidentRole.WITNESS and fidelity is not None]
    return max(seen) if seen else None


async def recount(call: MortalCall, args: RecountInput) -> str:
    incident = await call.session.get(IncidentRow, args.incident_id)
    if incident is None:
        fail(MortalResult.RECOUNT_REFUSED, why=f"there is no happening {args.incident_id}")
    fidelity = await own_fidelity(call, incident.id)
    if fidelity is None:
        fail(MortalResult.RECOUNT_REFUSED, why="you neither saw it nor took part in it")
    home = await is_carrier(call.session, call.me.location_id)
    if home is None:
        fail(MortalResult.RECOUNT_REFUSED, why="you live among no people to tell")
    if held(home.id):
        fail(MortalResult.RECOUNT_REFUSED, why="a stronger hand holds your people")
    rumour = await call.session.scalar(select(RumourRow).where(RumourRow.incident_id == incident.id, RumourRow.carrier_entity_id == home.id))
    if rumour is None:
        call.session.add(
            RumourRow(
                incident_id=incident.id,
                carrier_entity_id=home.id,
                channel=RumourChannel.WITNESS,
                fidelity=fidelity,
                hops=0,
                epoch=call.epoch,
                lingered=0,
                acted=False,
                planted=False,
                locked=[],
            )
        )
    elif rumour.fidelity < fidelity and "fidelity" not in rumour.locked:
        for old in await call.session.scalars(select(RumourDistortionRow).where(RumourDistortionRow.rumour_id == rumour.id)):
            await call.session.delete(old)
        rumour.fidelity = fidelity
    await call.session.flush()
    await tell(call.session, incident.id, call.me.id, [home.id], call.rules)
    await call.record(
        "event.recounted",
        roles={IncidentRole.TELLER: call.me.id, IncidentRole.WITNESS: [home.id]},
        facts={"fidelity": fidelity},
        place=home.id,
        cause=incident.id,
    )
    account = await account_text(call.session, incident.id, step_offset=args.step_offset, step_limit=call.rules.context.account_steps_shown)
    return result(MortalResult.RECOUNTED, place=home.name, account=account)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    return [ToolSpec(MortalToolId.RECOUNT, AgentKind.MORTAL, RecountInput, TELL, recount)]
