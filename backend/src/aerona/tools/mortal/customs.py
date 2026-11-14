from typing import Any

from sqlalchemy import select

from aerona.db.tables.bonds import BondRow
from aerona.db.tables.customs import CooperativeRow, MembershipRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.customs import Membership, Naturalisation
from aerona.engine.economy.purse import take_coin
from aerona.engine.primitives.queries import connect, living_entity
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.mortal import lines


class JoinCooperativeInput(ToolInput):
    faction_id: int


class SeekCitizenshipInput(ToolInput):
    pass


async def join_cooperative(call: MortalCall, args: JoinCooperativeInput) -> str:
    pool = await call.session.get(CooperativeRow, args.faction_id)
    faction = await living_entity(call.session, args.faction_id)
    if pool is None or faction is None:
        fail(MortalResult.COOPERATIVE_DECLINED, why="there is no such cooperative")
    if faction.location_id != call.me.location_id:
        fail(MortalResult.COOPERATIVE_DECLINED, why="it pools the means of another town")
    joined = await call.session.scalar(
        select(BondRow.id)
        .where(
            BondRow.source_node_id == call.me.id, BondRow.target_node_id == faction.id, BondRow.kind == BondKind.MEMBER_OF, BondRow.state == BondState.ACTIVE
        )
        .limit(1)
    )
    if joined is not None:
        fail(MortalResult.COOPERATIVE_DECLINED, why="your means are pooled there already")
    await connect(call.session, call.me.id, faction.id, BondKind.MEMBER_OF, call.tick.epoch, description="pooled their means")
    call.target(faction.id)
    await call.chronicle(ChronicleKind.CIVILIZATION, lines.JOIN_COOPERATIVE, entity_ids=[call.me.id, faction.id], me=call.me.name, faction=faction.name)
    return result(MortalResult.COOPERATIVE_JOINED, faction=faction.name, purpose=pool.purpose.value)


async def seek_citizenship(call: MortalCall, args: SeekCitizenshipInput) -> str:
    row = await call.session.get(MembershipRow, call.me.id)
    if row is None or row.category is not Membership.RESIDENT_FOREIGNER:
        fail(MortalResult.CITIZENSHIP_DECLINED, why="the realm does not count you a foreigner")
    if "category" in row.locked:
        fail(MortalResult.CITIZENSHIP_DECLINED, why="a stronger hand holds your standing")
    if not await take_coin(call.session, call.tick.rules, call.me, call.tick.rules.citizenship.purchase_cost):
        fail(MortalResult.CITIZENSHIP_DECLINED, why="you cannot pay the fee")
    row.category, row.path, row.since_epoch = Membership.CITIZEN, Naturalisation.PURCHASE, call.tick.epoch
    realm = await living_entity(call.session, row.polity_entity_id)
    call.target(call.me.id)
    await call.chronicle(ChronicleKind.CIVILIZATION, lines.SEEK_CITIZENSHIP, entity_ids=[call.me.id], me=call.me.name)
    return result(MortalResult.CITIZENSHIP_GRANTED, realm=realm.name if realm is not None else "the realm")


def specs() -> list[ToolSpec[MortalCall, Any]]:
    mortal = AgentKind.MORTAL
    meta = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.JOIN_COOPERATIVE, mortal, JoinCooperativeInput, meta, join_cooperative),
        ToolSpec(MortalToolId.SEEK_CITIZENSHIP, mortal, SeekCitizenshipInput, meta, seek_citizenship),
    ]
