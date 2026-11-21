from typing import Annotated, Any

from pydantic import Field
from sqlalchemy import select

from aerona.constants.tool_inputs import NAME_MAX, NAME_MIN
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.honours import HONOUR_RANK_MAX, HonourHeldRow, HonourKindRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.honours import HonourPrivilege
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.honours.persons import HonourTally, confer, head_of, holders_of, holds, revoke
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail

Name = Annotated[str, Field(min_length=NAME_MIN, max_length=NAME_MAX)]
PRIVILEGES_MAX = 6
LIMIT_MAX = 1000


class ConferHonourInput(ToolInput):
    honour_kind_id: int
    holder_id: int
    deed_incident_id: int


class RevokeHonourInput(ToolInput):
    honour_id: int


class FoundHonourInput(ToolInput):
    conferrer_id: int
    name_reason: Name
    privileges: list[HonourPrivilege] = Field(default_factory=list, max_length=PRIVILEGES_MAX)
    limit: int = Field(default=0, ge=0, le=LIMIT_MAX)


async def headed(call: MortalCall, conferrer_id: int) -> None:
    if await head_of(call.session, conferrer_id) != call.me.id:
        fail(MortalResult.HONOUR_REFUSED, why="only the head of the realm, faith or order that confers it can do so")
    if held(conferrer_id):
        fail(MortalResult.HONOUR_REFUSED, why="a god holds it unchanged")


async def confer_honour_tool(call: MortalCall, args: ConferHonourInput) -> str:
    kind = await call.session.get(HonourKindRow, args.honour_kind_id)
    holder = await call.session.get(EntityRow, args.holder_id)
    if kind is None or holder is None or holder.status is not EntityStatus.CANON:
        fail(MortalResult.HONOUR_REFUSED, why="there is no such honour or no such living one to receive it")
    await headed(call, kind.conferrer_node_id)
    if await call.session.get(IncidentRow, args.deed_incident_id) is None:
        fail(MortalResult.HONOUR_REFUSED, why="an honour is conferred for a deed on record")
    if held(holder.id) or await holds(call.session, holder.id, kind.id):
        fail(MortalResult.HONOUR_REFUSED, why="they hold it already, or a god holds them")
    if kind.holder_limit and len(await holders_of(call.session, kind.id)) >= kind.holder_limit:
        fail(MortalResult.HONOUR_REFUSED, why="all its places are filled")
    await confer(call.tick, kind, holder, tally=HonourTally(), by=call.me.id, deed=args.deed_incident_id)
    call.target(holder.id)
    return result(MortalResult.HONOUR_CONFERRED, honour=kind.name, holder=holder.name)


async def revoke_honour_tool(call: MortalCall, args: RevokeHonourInput) -> str:
    row = await call.session.get(HonourHeldRow, args.honour_id)
    kind = await call.session.get(HonourKindRow, row.kind_id) if row is not None else None
    if row is None or kind is None or row.revoked_epoch is not None:
        fail(MortalResult.HONOUR_REFUSED, why="there is no such honour still held")
    await headed(call, kind.conferrer_node_id)
    if held(row.holder_node_id) or "revoked_epoch" in row.locked:
        fail(MortalResult.HONOUR_REFUSED, why="a god holds it unchanged")
    await revoke(call.tick, row, HonourTally())
    call.target(row.holder_node_id)
    return result(MortalResult.HONOUR_REVOKED, honour=kind.name)


async def found_honour_tool(call: MortalCall, args: FoundHonourInput) -> str:
    await headed(call, args.conferrer_id)
    ranks = list(await call.session.scalars(select(HonourKindRow.rank).where(HonourKindRow.conferrer_node_id == args.conferrer_id)))
    kind = HonourKindRow(
        conferrer_node_id=args.conferrer_id,
        name=args.name_reason,
        rank=min(HONOUR_RANK_MAX, len(ranks) + 1),
        privileges=sorted({value.value for value in args.privileges}),
        holder_limit=args.limit,
        founded_epoch=call.tick.epoch,
        locked=[],
    )
    call.session.add(kind)
    await call.session.flush()
    call.target(args.conferrer_id)
    await call.record("honour.founded", roles={IncidentRole.ACTOR: args.conferrer_id}, facts={"honour": kind.name, "rank": kind.rank})
    return result(MortalResult.HONOUR_FOUNDED, honour=kind.name, rank=kind.rank)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    act = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.CONFER_HONOUR, AgentKind.MORTAL, ConferHonourInput, act, confer_honour_tool),
        ToolSpec(MortalToolId.REVOKE_HONOUR, AgentKind.MORTAL, RevokeHonourInput, act, revoke_honour_tool),
        ToolSpec(MortalToolId.FOUND_HONOUR, AgentKind.MORTAL, FoundHonourInput, act, found_honour_tool),
    ]
