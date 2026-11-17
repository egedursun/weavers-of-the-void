from typing import Any

from sqlalchemy import select

from aerona.core.errors import ValidationFailedError
from aerona.db.tables.operations import EchelonRow, ExpeditionMemberRow, ExpeditionRow
from aerona.db.tables.warfare import ArmyRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.operations import EchelonOrder, ExpeditionStatus
from aerona.engine.operations import control
from aerona.engine.operations.expeditions import ExpeditionTally, camp, companions_for, on_expedition, party_of
from aerona.engine.primitives.queries import living_entity
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail

UNDER_WAY = (ExpeditionStatus.UNDERWAY, ExpeditionStatus.CAMPED)


class LeadExpeditionInput(ToolInput):
    target_id: int


class MakeCampInput(ToolInput):
    pass


class OrderFormationInput(ToolInput):
    echelon_id: int
    order: EchelonOrder


async def lead_expedition(call: MortalCall, args: LeadExpeditionInput) -> str:
    target = await living_entity(call.session, args.target_id)
    if target is None or target.id == call.me.id or held(target.id):
        fail(MortalResult.EXPEDITION_DECLINED, why="there is no such place to reach")
    away = await on_expedition(call.tick)
    if call.me.id in away:
        fail(MortalResult.EXPEDITION_DECLINED, why="you already travel with an expedition")
    companions = await companions_for(call.tick, call.me, away)
    try:
        row = await control.send_expedition(call.tick, call.me.id, target.id, [mortal.id for mortal in companions], None)
    except ValidationFailedError as error:
        fail(MortalResult.EXPEDITION_DECLINED, why=str(error).rstrip("."))
    call.target(target.id)
    await call.record(
        "tools.mortal.lead_expedition",
        roles={IncidentRole.LEADER: call.me.id, IncidentRole.DESTINATION: target.id, IncidentRole.MEMBER: [mortal.id for mortal in companions]},
        facts={"party": len(companions) + 1, "legs": row.legs_total},
        place=target.id,
        cause=row.incident_id,
    )
    return result(MortalResult.EXPEDITION_LED, target=target.name, legs=row.legs_total, party=len(companions) + 1)


async def make_camp(call: MortalCall, args: MakeCampInput) -> str:
    row = await call.session.scalar(
        select(ExpeditionRow)
        .join(ExpeditionMemberRow, ExpeditionMemberRow.expedition_id == ExpeditionRow.id)
        .where(ExpeditionMemberRow.mortal_entity_id == call.me.id, ExpeditionRow.status.in_(UNDER_WAY))
        .limit(1)
    )
    if row is None or held(call.me.id):
        fail(MortalResult.CAMP_REFUSED, why="you travel with no expedition")
    party = await party_of(call.tick, row)
    tally = ExpeditionTally()
    await camp(call.tick, party, tally, force=True)
    if not tally.camps:
        fail(MortalResult.CAMP_REFUSED, why="the party has too few provisions or will not rest")
    call.target(call.me.id)
    await call.record(
        "tools.mortal.make_camp",
        roles={IncidentRole.LEADER: call.me.id},
        facts={"expedition": row.name, "provisions": row.provisions, "ambushes": tally.ambushes},
        cause=row.incident_id,
    )
    return result(MortalResult.CAMP_MADE, provisions=row.provisions, ambushed="an ambush struck it" if tally.ambushes else "the night passed quietly")


async def order_formation(call: MortalCall, args: OrderFormationInput) -> str:
    row = await call.session.get(EchelonRow, args.echelon_id)
    if row is None:
        fail(MortalResult.FORMATION_REFUSED, why="there is no such formation")
    army = await call.session.get(ArmyRow, row.army_entity_id) if row.army_entity_id is not None else None
    commands = row.commander_entity_id == call.me.id or (army is not None and army.commander_entity_id == call.me.id)
    if not commands or held(call.me.id):
        fail(MortalResult.FORMATION_REFUSED, why="you do not command it")
    if "order" not in row.locked:
        row.order = args.order
    call.target(row.army_entity_id or row.owner_entity_id)
    roles = {IncidentRole.ACTOR: call.me.id, **({IncidentRole.SUBJECT: row.army_entity_id} if row.army_entity_id is not None else {})}
    await call.record("tools.mortal.order_formation", roles=roles, facts={"formation": row.name, "order": args.order})
    return result(MortalResult.FORMATION_ORDERED, formation=row.name, order=args.order.value)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    mortal = AgentKind.MORTAL
    meta = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.LEAD_EXPEDITION, mortal, LeadExpeditionInput, meta, lead_expedition),
        ToolSpec(MortalToolId.MAKE_CAMP, mortal, MakeCampInput, meta, make_camp),
        ToolSpec(MortalToolId.ORDER_FORMATION, mortal, OrderFormationInput, meta, order_formation),
    ]
