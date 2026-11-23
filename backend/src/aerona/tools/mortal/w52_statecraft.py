from typing import Any

from sqlalchemy import select

from aerona.catalog.statecraft import POSITION_TEXT
from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.tables.affairs import CourtPositionRow
from aerona.db.tables.customs import CooperativeRow, EvidenceRow, MembershipCategoryRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionGoalRow, FactionProfileRow
from aerona.db.tables.justice import CrimeCaseRow
from aerona.db.tables.polity import ClaimRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.customs import CoopPurpose, EvidenceKind, MemberRight, Membership
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.faction import FactionGoalKind
from aerona.domain.enums.justice import CaseStage
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import ClaimBasis, OathBreach, OathKind
from aerona.domain.enums.regime import ClientRole
from aerona.domain.enums.statecraft import CourtPosition
from aerona.engine.lifecycle.succession import designate_heir
from aerona.engine.polity.oaths import break_oath, swear
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.regime.control import bind_client
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail, require_canon
from aerona.tools.mortal.ruler import throne_of

CLIENT_STRENGTH = 40
PRESS_GAIN = 10
TESTIMONY_RELIABILITY = 50


class AppointCourtInput(ToolInput):
    position: CourtPosition
    mortal_id: int


class TakeClientInput(ToolInput):
    client_id: int
    role: ClientRole


class SetRightsInput(ToolInput):
    category: Membership
    right: MemberRight
    granted: bool = True


class PressClaimInput(ToolInput):
    realm_id: int
    basis: ClaimBasis


class DesignateHeirInput(ToolInput):
    heir_id: int


class FoundCoopInput(ToolInput):
    purpose: CoopPurpose


class TestifyInput(ToolInput):
    case_id: int
    kind: EvidenceKind
    sworn: bool = True


class FactionGoalInput(ToolInput):
    goal: FactionGoalKind
    target_id: int | None = None


async def appoint_court(call: MortalCall, args: AppointCourtInput) -> str:
    realm = await throne_of(call)
    chosen = await require_canon(call.session, args.mortal_id)
    if chosen.entity_type is not EntityType.MORTAL or chosen.id == call.me.id:
        fail(MortalResult.COURT_REFUSED, why="name another mortal of your court")
    row = await call.session.get(CourtPositionRow, (realm.entity.id, args.position))
    if row is not None and row.locked:
        fail(MortalResult.COURT_REFUSED, why="that place at court is held")
    if held(chosen.id):
        fail(MortalResult.COURT_REFUSED, why="that mortal is held")
    if row is None:
        row = CourtPositionRow(polity_entity_id=realm.entity.id, position=args.position, since_epoch=call.epoch)
        call.session.add(row)
    row.holder_entity_id, row.since_epoch = chosen.id, call.epoch
    await call.session.flush()
    call.target(chosen.id)
    await call.record(
        "tools.mortal.appoint_court",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.TARGET: chosen.id, IncidentRole.AUTHORITY: realm.entity.id},
        facts={"position": args.position},
    )
    return result(MortalResult.COURT_APPOINTED, name=chosen.name, position=spoken(args.position), duty=POSITION_TEXT[args.position])


async def take_client(call: MortalCall, args: TakeClientInput) -> str:
    client = await require_canon(call.session, args.client_id)
    if client.entity_type is not EntityType.MORTAL or client.id == call.me.id or client.location_id != call.me.location_id:
        fail(MortalResult.CLIENT_REFUSED, why="only another mortal of your own place can be taken as a client")
    if held(client.id):
        fail(MortalResult.CLIENT_REFUSED, why="that mortal is held")
    await bind_client(call.tick, call.me.id, client.id, args.role, CLIENT_STRENGTH)
    call.target(client.id)
    await call.record("tools.mortal.take_client", roles={IncidentRole.PATRON: call.me.id, IncidentRole.MEMBER: client.id}, facts={"role": args.role})
    return result(MortalResult.CLIENT_TAKEN, name=client.name, role=spoken(args.role))


async def set_rights(call: MortalCall, args: SetRightsInput) -> str:
    realm = await throne_of(call)
    row = await call.session.get(MembershipCategoryRow, (realm.entity.id, args.category))
    if row is None:
        row = MembershipCategoryRow(polity_entity_id=realm.entity.id, category=args.category, rights=[], locked=[])
        call.session.add(row)
    if "rights" in row.locked:
        fail(MortalResult.RIGHTS_REFUSED, why="the rights of that standing are held")
    rights = [item for item in row.rights if item != args.right.value]
    row.rights = sorted([*rights, args.right.value]) if args.granted else rights
    await call.session.flush()
    call.target(realm.entity.id)
    await call.record(
        "law.right_changed",
        roles={IncidentRole.AUTHORITY: realm.entity.id, IncidentRole.ACTOR: call.me.id},
        facts={"category": args.category, "right": args.right},
    )
    return result(MortalResult.RIGHTS_SET, category=spoken(args.category), right=spoken(args.right), state="granted" if args.granted else "taken away")


async def press_claim(call: MortalCall, args: PressClaimInput) -> str:
    claim = await call.session.scalar(
        select(ClaimRow).where(
            ClaimRow.claimant_entity_id == call.me.id, ClaimRow.polity_entity_id == args.realm_id, ClaimRow.basis == args.basis, ClaimRow.ended_epoch.is_(None)
        )
    )
    if claim is None:
        fail(MortalResult.CLAIM_PRESS_REFUSED, why=f"you hold no claim by {spoken(args.basis)} on that realm")
    if "pressed" in claim.locked or "strength" in claim.locked:
        fail(MortalResult.CLAIM_PRESS_REFUSED, why="that claim is held")
    claim.pressed = True
    claim.strength = clamp_int(claim.strength + PRESS_GAIN, 0, PERCENT)
    await call.session.flush()
    call.target(args.realm_id)
    await call.record(
        "tools.mortal.press_claim",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.AUTHORITY: args.realm_id},
        facts={"basis": args.basis, "strength": claim.strength},
    )
    return result(MortalResult.CLAIM_PRESSED, basis=spoken(args.basis), strength=claim.strength)


async def designate(call: MortalCall, args: DesignateHeirInput) -> str:
    realm = await throne_of(call)
    heir = await require_canon(call.session, args.heir_id)
    if heir.entity_type is not EntityType.MORTAL or heir.id == call.me.id:
        fail(MortalResult.HEIR_REFUSED, why="name another living mortal")
    if held(heir.id) or "heir" in realm.profile.locked:
        fail(MortalResult.HEIR_REFUSED, why="the succession of your realm is held")
    await designate_heir(call.tick, call.me.id, heir.id)
    call.target(heir.id)
    await call.record("succession.designated", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.SUCCESSOR: heir.id, IncidentRole.AUTHORITY: realm.entity.id})
    return result(MortalResult.HEIR_NAMED, name=heir.name, realm=realm.entity.name)


async def found_coop(call: MortalCall, args: FoundCoopInput) -> str:
    town = call.me.location_id
    if town is None:
        fail(MortalResult.COOP_REFUSED, why="you live in no town")
    pooled = set(await call.session.scalars(select(CooperativeRow.faction_entity_id)))
    faction = await call.session.scalar(
        select(EntityRow)
        .where(
            EntityRow.entity_type == EntityType.FACTION,
            EntityRow.status == EntityStatus.CANON,
            EntityRow.location_id == town,
            EntityRow.id.not_in(list(pooled)),
        )
        .order_by(EntityRow.id)
        .limit(1)
    )
    if faction is None or held(faction.id) or held(town):
        fail(MortalResult.COOP_REFUSED, why="no body of your town is free to pool its means")
    call.session.add(CooperativeRow(faction_entity_id=faction.id, purpose=args.purpose, locked=[]))
    await call.session.flush()
    call.target(faction.id)
    await call.record("tools.mortal.found_coop", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.PRODUCT: faction.id}, facts={"purpose": args.purpose})
    return result(MortalResult.COOP_FOUNDED, name=faction.name, purpose=spoken(args.purpose))


async def testify(call: MortalCall, args: TestifyInput) -> str:
    case = await call.session.get(CrimeCaseRow, args.case_id)
    if case is None or case.stage not in (CaseStage.INVESTIGATION, CaseStage.TRIAL) or case.settlement_entity_id != call.me.location_id:
        fail(MortalResult.TESTIMONY_REFUSED, why="there is no open case in your town by that number")
    if case.settlement_entity_id is not None and held(case.settlement_entity_id):
        fail(MortalResult.TESTIMONY_REFUSED, why="that town is held")
    call.session.add(
        EvidenceRow(
            case_id=case.id,
            kind=args.kind,
            points_to_node_id=case.accused_entity_id,
            reliability=TESTIMONY_RELIABILITY,
            sworn=args.sworn,
            found_epoch=call.epoch,
            locked=[],
        )
    )
    if args.sworn:
        oath = await swear(call.tick, call.me, OathKind.TESTIMONY, recipient_id=case.polity_entity_id, note_text="sworn before giving evidence")
        if case.culprit_entity_id is not None and case.accused_entity_id is not None and case.culprit_entity_id != case.accused_entity_id:
            await break_oath(call.tick, oath, OathBreach.FALSE_WITNESS, cause=case.id)
    await call.session.flush()
    call.target(case.accused_entity_id or call.me.id)
    await call.record(
        "tools.mortal.testify", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.ACCUSED: case.accused_entity_id}, facts={"evidence": args.kind}
    )
    return result(MortalResult.TESTIMONY_GIVEN, kind=spoken(args.kind), sworn="under oath" if args.sworn else "unsworn")


async def set_faction_goal(call: MortalCall, args: FactionGoalInput) -> str:
    profile = await call.session.scalar(select(FactionProfileRow).where(FactionProfileRow.leader_entity_id == call.me.id).limit(1))
    if profile is None:
        fail(MortalResult.FACTION_GOAL_REFUSED, why="you lead no faction")
    if held(profile.faction_entity_id) or "goals" in profile.locked:
        fail(MortalResult.FACTION_GOAL_REFUSED, why="your faction's aims are held")
    call.session.add(
        FactionGoalRow(
            faction_entity_id=profile.faction_entity_id,
            kind=args.goal,
            target_node_id=args.target_id,
            priority=PERCENT,
            progress=0,
            since_epoch=call.epoch,
            set_by_player=False,
            locked=[],
        )
    )
    await call.session.flush()
    call.target(profile.faction_entity_id)
    await call.record("tools.mortal.set_faction_goal", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.TARGET: args.target_id}, facts={"goal": args.goal})
    return result(MortalResult.FACTION_GOAL_SET, goal=spoken(args.goal))


def specs() -> list[ToolSpec[MortalCall, Any]]:
    mortal = AgentKind.MORTAL
    meta = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.APPOINT_COURT, mortal, AppointCourtInput, meta, appoint_court),
        ToolSpec(MortalToolId.TAKE_CLIENT, mortal, TakeClientInput, meta, take_client),
        ToolSpec(MortalToolId.SET_RIGHTS, mortal, SetRightsInput, meta, set_rights),
        ToolSpec(MortalToolId.PRESS_CLAIM, mortal, PressClaimInput, meta, press_claim),
        ToolSpec(MortalToolId.DESIGNATE_HEIR, mortal, DesignateHeirInput, meta, designate),
        ToolSpec(MortalToolId.FOUND_COOP, mortal, FoundCoopInput, meta, found_coop),
        ToolSpec(MortalToolId.TESTIFY, mortal, TestifyInput, meta, testify),
        ToolSpec(MortalToolId.SET_FACTION_GOAL, mortal, FactionGoalInput, meta, set_faction_goal),
    ]
