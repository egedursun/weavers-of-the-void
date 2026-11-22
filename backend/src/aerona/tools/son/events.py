from typing import Any, NoReturn

from pydantic import Field
from sqlalchemy import select

from aerona.catalog.life.tools import DISTORTION_ROW_RUMOUR_DISTORTIONS
from aerona.catalog.life_traits import RUMOUR_DISTORTION_TRAITS, having
from aerona.core.grammar import several
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import RumourRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.records import IncidentStepRow
from aerona.db.tables.tellings import RumourDistortionRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import RumourChannel
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus
from aerona.domain.enums.life_traits import RumourDistortionTrait
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import RumourDistortion, StepAction, StepOutcome
from aerona.engine.lore.account_text import account_text, difference_text
from aerona.engine.lore.tellings import Telling, node_names, telling_of
from aerona.engine.lore.witnesses import tell
from aerona.prompts import SonToolId
from aerona.prompts.tools.results import SonResult, result
from aerona.tools.framework.call import SonCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, no_cost, son_standard_action
from aerona.tools.framework.validation import fail

READ = ToolMeta(ActionKind.OTHER, no_cost, read_only=True)
TELL = ToolMeta(ActionKind.INFLUENCE, son_standard_action)
DISTORTIONS_MAX = 6
SWAPS = having(RUMOUR_DISTORTION_TRAITS, RumourDistortionTrait.SWAPS)
STEP_KINDS = having(RUMOUR_DISTORTION_TRAITS, RumourDistortionTrait.STEP_KINDS)


class RecallEventInput(ToolInput):
    incident_id: int
    step_offset: int = Field(default=0, ge=0)


class DistortionInput(ToolInput):
    kind: RumourDistortion
    role: IncidentRole | None = None
    fact: str | None = None
    step_id: int | None = None
    told_id: int | None = None
    told_amount: float | None = None
    told_year: int | None = None
    told_action: StepAction | None = None
    told_outcome: StepOutcome | None = None
    told_value: str | None = None
    told_cause_id: int | None = None


class RetellEventInput(ToolInput):
    incident_id: int
    distortions: list[DistortionInput] = Field(default_factory=list, max_length=DISTORTIONS_MAX)


async def knows(call: SonCall, incident: IncidentRow) -> bool:
    involved = await call.session.scalar(
        select(IncidentParticipantRow.node_id).where(IncidentParticipantRow.incident_id == incident.id, IncidentParticipantRow.node_id == call.son.id).limit(1)
    )
    if involved is not None:
        return True
    return incident.world_id is None or call.world_id is None or incident.world_id == call.world_id or await call.reachable_world(incident.world_id)


async def known_incident(call: SonCall, incident_id: int) -> IncidentRow:
    incident = await call.session.get(IncidentRow, incident_id)
    if incident is None or not await knows(call, incident):
        fail(SonResult.EVENT_UNKNOWN, id=incident_id)
    return incident


async def recall_event(call: SonCall, args: RecallEventInput) -> str:
    incident = await known_incident(call, args.incident_id)
    return await account_text(call.session, incident.id, step_offset=args.step_offset, step_limit=call.rules.context.account_steps_shown)


def refuse(why: str) -> NoReturn:
    fail(SonResult.RETELL_REFUSED, why=why)


async def checked_step(call: SonCall, incident: IncidentRow, step_id: int | None) -> int:
    if step_id is None:
        refuse("name the step by its id")
    found = await call.session.get(IncidentStepRow, step_id)
    if found is None or found.incident_id != incident.id:
        refuse(f"step {step_id} is not a step of this happening")
    return found.id


async def swapped(call: SonCall, telling: Telling, given: DistortionInput, row: RumourDistortionRow) -> RumourDistortionRow:
    if given.role is None or not any(part.role is given.role for part in telling.roles):
        refuse("name a role someone held in it")
    if given.told_id is None or await call.session.get(EntityRow, given.told_id) is None:
        refuse("name the record told in their place")
    row.role, row.told_node_id = given.role, given.told_id
    return row


async def stepped(call: SonCall, incident: IncidentRow, given: DistortionInput, row: RumourDistortionRow) -> RumourDistortionRow:
    row.step_id = await checked_step(call, incident, given.step_id)
    row.role = given.role
    row.told_action, row.told_outcome, row.told_enum_value, row.told_node_id = given.told_action, given.told_outcome, given.told_value, given.told_id
    if given.kind is RumourDistortion.STEP_ADDED and given.told_action is None:
        refuse("say what is told to have been done")
    return row


def factual(telling: Telling, given: DistortionInput, row: RumourDistortionRow) -> RumourDistortionRow:
    if given.fact is None or not any(fact.key == given.fact for fact in telling.facts):
        refuse("name a fact the happening holds")
    if given.kind is RumourDistortion.AMOUNT_CHANGED and given.told_amount is None:
        refuse("give the amount told instead")
    if given.kind is RumourDistortion.OUTCOME_CHANGED and given.told_value is None:
        refuse("give the value told instead")
    row.fact_key, row.told_number, row.told_enum_value = given.fact, given.told_amount, given.told_value
    return row


async def framed(call: SonCall, given: DistortionInput, row: RumourDistortionRow) -> RumourDistortionRow:
    if given.kind is RumourDistortion.PLACE_CHANGED:
        if given.told_id is None or await call.session.get(EntityRow, given.told_id) is None:
            refuse("name the place told instead")
        row.told_node_id = given.told_id
    elif given.kind is RumourDistortion.MOMENT_CHANGED:
        if given.told_year is None:
            refuse("give the year told instead")
        row.told_year = given.told_year
    else:
        if given.told_cause_id is None or await call.session.get(IncidentRow, given.told_cause_id) is None:
            refuse("name the happening told as its cause")
        row.told_incident_id = given.told_cause_id
    return row


async def distortion_row(call: SonCall, incident: IncidentRow, telling: Telling, given: DistortionInput) -> RumourDistortionRow:
    row = RumourDistortionRow(distortion=given.kind, epoch=call.epoch, locked=[])
    if given.kind in SWAPS and given.step_id is None:
        return await swapped(call, telling, given, row)
    if given.kind in STEP_KINDS or given.step_id is not None:
        return await stepped(call, incident, given, row)
    if given.kind in DISTORTION_ROW_RUMOUR_DISTORTIONS:
        return factual(telling, given, row)
    return await framed(call, given, row)


async def worshippers(call: SonCall) -> list[int]:
    rows = await call.session.execute(
        select(BondRow.source_node_id)
        .join(EntityRow, EntityRow.id == BondRow.source_node_id)
        .where(
            BondRow.target_node_id == call.son.id,
            BondRow.kind == BondKind.WORSHIPS,
            BondRow.state == BondState.ACTIVE,
            EntityRow.status == EntityStatus.CANON,
            EntityRow.entity_type.in_(list(COMMUNITY_TYPES)),
        )
        .order_by(BondRow.source_node_id)
    )
    return [node for (node,) in rows if not held(node)]


async def retell_event(call: SonCall, args: RetellEventInput) -> str:
    incident = await known_incident(call, args.incident_id)
    telling = await telling_of(call.session, incident.id)
    if telling is None:
        fail(SonResult.EVENT_UNKNOWN, id=args.incident_id)
    drafts = [await distortion_row(call, incident, telling, given) for given in args.distortions]
    hearers = await worshippers(call)
    if not hearers:
        refuse("no living people worships you to hear it")
    fidelity = call.rules.records.fidelity_told
    for carrier in hearers:
        rumour = await call.session.scalar(select(RumourRow).where(RumourRow.incident_id == incident.id, RumourRow.carrier_entity_id == carrier))
        if rumour is None:
            rumour = RumourRow(
                incident_id=incident.id,
                carrier_entity_id=carrier,
                channel=RumourChannel.PLANTED,
                fidelity=fidelity,
                hops=0,
                epoch=call.epoch,
                lingered=0,
                acted=False,
                planted=True,
                locked=[],
            )
            call.session.add(rumour)
            await call.session.flush()
        else:
            for old in await call.session.scalars(select(RumourDistortionRow).where(RumourDistortionRow.rumour_id == rumour.id)):
                await call.session.delete(old)
            rumour.fidelity, rumour.planted, rumour.epoch = fidelity, True, call.epoch
        for position, draft in enumerate(drafts):
            call.session.add(
                RumourDistortionRow(
                    rumour_id=rumour.id,
                    position=position,
                    distortion=draft.distortion,
                    role=draft.role,
                    fact_key=draft.fact_key,
                    step_id=draft.step_id,
                    told_node_id=draft.told_node_id,
                    told_number=draft.told_number,
                    told_enum_value=draft.told_enum_value,
                    told_year=draft.told_year,
                    told_incident_id=draft.told_incident_id,
                    told_action=draft.told_action,
                    told_outcome=draft.told_outcome,
                    epoch=call.epoch,
                    locked=[],
                )
            )
    await call.session.flush()
    await tell(call.session, incident.id, call.son.id, hearers, call.rules)
    await call.record(
        "event.retold", roles={IncidentRole.TELLER: call.son.id, IncidentRole.WITNESS: hearers}, facts={"changes": len(drafts)}, cause=incident.id
    )
    names = await node_names(call.session, [draft.told_node_id for draft in drafts])
    return result(
        SonResult.RETOLD,
        id=incident.id,
        peoples=several(len(hearers), "people that worships you", "peoples that worship you"),
        changes="; ".join(difference_text(draft, names) for draft in drafts),
    )


def specs() -> list[ToolSpec[SonCall, Any]]:
    son = AgentKind.SON
    return [
        ToolSpec(SonToolId.RECALL_EVENT, son, RecallEventInput, READ, recall_event),
        ToolSpec(SonToolId.RETELL_EVENT, son, RetellEventInput, TELL, retell_event),
    ]
