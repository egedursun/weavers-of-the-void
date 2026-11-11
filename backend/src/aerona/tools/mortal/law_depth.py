from typing import Any

from pydantic import Field
from sqlalchemy import select

from aerona.db.tables.justice import CrimeCaseRow
from aerona.db.tables.law_depth import OutlawRow, PrisonerRow
from aerona.db.tables.polity import OfficeRow, PolityMemberRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.justice import Verdict
from aerona.domain.enums.law_depth import RegistryKind
from aerona.domain.enums.polity import OfficeKind
from aerona.engine.law.appeals import file_appeal
from aerona.engine.law.outlawry import OutlawTally, caught, hunter_for
from aerona.engine.law.pardons import grant_pardon
from aerona.engine.law.registries import register
from aerona.engine.military.mole_hunts import MoleTally, hunt
from aerona.engine.primitives.queries import living_entity
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import EmptyInput, ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.mortal import lines

DEED_MAX = 100000


class DeedInput(ToolInput):
    counterparty_id: int
    kind: RegistryKind
    amount: int = Field(default=0, ge=0, le=DEED_MAX)


class OutlawInput(ToolInput):
    outlaw_id: int


class PardonInput(ToolInput):
    mortal_id: int


async def my_realm(call: MortalCall) -> int | None:
    if call.me.location_id is None:
        return None
    return await call.session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == call.me.location_id).limit(1))


async def office_in(call: MortalCall, kind: OfficeKind) -> OfficeRow | None:
    rows = await call.session.scalars(select(OfficeRow).where(OfficeRow.holder_entity_id == call.me.id, OfficeRow.kind == kind).limit(1))
    return rows.first()


async def register_deed(call: MortalCall, args: DeedInput) -> str:
    other = await living_entity(call.session, args.counterparty_id)
    if other is None or other.id == call.me.id:
        fail(MortalResult.DEED_REFUSED, why="there is no such living party")
    if args.kind is RegistryKind.LAND_TITLE:
        fail(MortalResult.DEED_REFUSED, why="titles to land are registered by the realm")
    holder = await my_realm(call) or call.me.location_id
    if holder is None:
        fail(MortalResult.DEED_REFUSED, why="no town or realm with a registry holds you")
    await register(call.tick, holder, args.kind, owner_id=call.me.id, counterparty_id=other.id, amount=args.amount)
    call.target(other.id)
    await call.chronicle(ChronicleKind.WORLD, lines.REGISTER_DEED, entity_ids=[call.me.id, other.id], me=call.me.name, other=other.name)
    return result(MortalResult.DEED_REGISTERED, kind=args.kind.value.replace("_", " "), name=other.name)


async def appeal_conviction(call: MortalCall, args: EmptyInput) -> str:
    case = await call.session.scalar(
        select(CrimeCaseRow)
        .where(CrimeCaseRow.accused_entity_id == call.me.id, CrimeCaseRow.verdict == Verdict.GUILTY)
        .order_by(CrimeCaseRow.closed_epoch.desc(), CrimeCaseRow.id.desc())
        .limit(1)
    )
    if case is None:
        fail(MortalResult.APPEAL_REFUSED, why="you stand convicted of nothing")
    row = await file_appeal(call.tick, case, call.me)
    if row is None:
        fail(MortalResult.APPEAL_REFUSED, why="there is no higher court, the appeal is filed already, or you cannot pay its fee")
    await call.chronicle(ChronicleKind.WORLD, lines.APPEAL, entity_ids=[call.me.id], me=call.me.name)
    return result(MortalResult.APPEAL_FILED, court=row.to_court.value.replace("_", " "), fee=row.fee)


async def claim_bounty(call: MortalCall, args: OutlawInput) -> str:
    row = await call.session.get(OutlawRow, args.outlaw_id)
    outlaw = await living_entity(call.session, args.outlaw_id)
    if row is None or outlaw is None:
        fail(MortalResult.BOUNTY_REFUSED, why="that mortal is no outlaw")
    found = await hunter_for(call.tick, row)
    if found is None or found[0].id != call.me.id:
        fail(MortalResult.BOUNTY_REFUSED, why="the realm that outlawed them has a better hunter than you")
    await caught(call.tick, row, outlaw, call.me, OutlawTally())
    call.target(outlaw.id)
    await call.chronicle(ChronicleKind.WORLD, lines.CLAIM_BOUNTY, entity_ids=[call.me.id, outlaw.id], me=call.me.name, outlaw=outlaw.name)
    return result(MortalResult.BOUNTY_CLAIMED, name=outlaw.name, bounty=row.bounty)


async def grant_mercy(call: MortalCall, args: PardonInput) -> str:
    office = await office_in(call, OfficeKind.RULER)
    if office is None:
        fail(MortalResult.PARDON_REFUSED, why="you rule no realm")
    mortal = await living_entity(call.session, args.mortal_id)
    jailed = await call.session.get(PrisonerRow, args.mortal_id)
    outlaw = await call.session.get(OutlawRow, args.mortal_id)
    if mortal is None or (jailed is None and outlaw is None):
        fail(MortalResult.PARDON_REFUSED, why="they are neither in prison nor outlawed")
    pardon = await grant_pardon(call.tick, call.me, mortal, polity_id=office.polity_entity_id, case_id=jailed.case_id if jailed is not None else None)
    call.target(mortal.id)
    await call.chronicle(ChronicleKind.WORLD, lines.GRANT_PARDON, entity_ids=[call.me.id, mortal.id], me=call.me.name, name=mortal.name)
    return result(MortalResult.PARDONED, name=mortal.name, corrupt="a favour to a friend" if pardon.corrupt else "mercy")


async def hunt_moles(call: MortalCall, args: EmptyInput) -> str:
    office = await office_in(call, OfficeKind.SPYMASTER)
    if office is None:
        fail(MortalResult.HUNT_REFUSED, why="no realm has made you its spymaster")
    tally = MoleTally()
    await hunt(call.tick, office.polity_entity_id, call.me, tally, forced=True)
    await call.chronicle(ChronicleKind.WORLD, lines.HUNT_MOLES, entity_ids=[call.me.id], me=call.me.name)
    return result(MortalResult.HUNTED, caught=tally.caught, purged=tally.purged + tally.defected, cleared=tally.cleared)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    mortal = AgentKind.MORTAL
    meta = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.REGISTER_DEED, mortal, DeedInput, meta, register_deed),
        ToolSpec(MortalToolId.APPEAL_CONVICTION, mortal, EmptyInput, meta, appeal_conviction),
        ToolSpec(MortalToolId.CLAIM_BOUNTY, mortal, OutlawInput, meta, claim_bounty),
        ToolSpec(MortalToolId.GRANT_PARDON, mortal, PardonInput, meta, grant_mercy),
        ToolSpec(MortalToolId.HUNT_MOLES, mortal, EmptyInput, meta, hunt_moles),
    ]
