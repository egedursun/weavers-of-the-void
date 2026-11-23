from typing import Any

from sqlalchemy import select

from aerona.catalog.war_w52 import ARMY_ROLES, CAPTIVE_FATES, DEFENCES, FALL_CHOICES, MOTIVES, OPERATIONS, SIEGE_WORKS, STANCES, VETERAN_GRANTS
from aerona.core.grammar import several
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import ArmyProfileRow, CaptiveCohortRow, SpyAgentRow
from aerona.db.tables.polity import OfficeRow, PolityMemberRow
from aerona.db.tables.settlement import SettlementInfrastructureRow
from aerona.db.tables.warfare import ArmyRow, SiegeRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.honours import VeteranGrant
from aerona.domain.enums.law_depth import RecruitMotive
from aerona.domain.enums.military import AgentStatus, ArmyRole, CaptiveFate, DefenderAction, SackChoice, SiegeAction, SiegeWork, SpyOperation, Stance
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.enums.war import SiegeStatus
from aerona.engine.couplings.field import offer_terms
from aerona.engine.honours.veterans import set_policy
from aerona.engine.military.control import settle_cohort
from aerona.engine.military.siege import surrenders
from aerona.engine.military.siege_w52 import capable, floodable, progress, suborn
from aerona.engine.military.spies_w52 import motive_by_heart
from aerona.engine.military.spy_depth import loyalty_for, motive_for
from aerona.engine.military.w52_war import appoint
from aerona.engine.phases.espionage import network_for, order_spy_operation
from aerona.engine.primitives.queries import living_entity
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.mortal.support import same_region

REFUSED = MortalResult.WAR_ORDER_REFUSED


class ArmyStanceInput(ToolInput):
    army_id: int
    stance: Stance


class ArmyRoleInput(ToolInput):
    army_id: int
    mortal_id: int
    role: ArmyRole


class CaptiveFateInput(ToolInput):
    cohort_id: int
    fate: CaptiveFate


class SubornInput(ToolInput):
    siege_id: int
    target_id: int


class SiegeWorkInput(ToolInput):
    siege_id: int
    work: SiegeWork


class DefendInput(ToolInput):
    siege_id: int
    defence: DefenderAction


class FallInput(ToolInput):
    siege_id: int
    choice: SackChoice


class NegotiateInput(ToolInput):
    siege_id: int


class OperationInput(ToolInput):
    target_id: int
    operation: SpyOperation


class RecruitAgentInput(ToolInput):
    mortal_id: int
    motive: RecruitMotive


class VeteransInput(ToolInput):
    grant: VeteranGrant


async def realm_of(call: MortalCall) -> int | None:
    place = call.me.location_id if call.me.entity_type is EntityType.MORTAL else call.me.id
    found = await call.session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == place).limit(1))
    return found if found is not None else place


async def sides_of(call: MortalCall) -> set[int]:
    mine = {call.me.id}
    if call.me.location_id is not None:
        mine.add(call.me.location_id)
    realm = await realm_of(call)
    if realm is not None:
        mine.add(realm)
    return mine


async def commanded(call: MortalCall, army_id: int) -> tuple[EntityRow, ArmyRow, ArmyProfileRow]:
    row = await call.session.get(ArmyRow, army_id)
    army = await living_entity(call.session, army_id)
    profile = await call.session.get(ArmyProfileRow, army_id)
    if row is None or army is None or profile is None or row.disbanded_epoch is not None:
        fail(REFUSED, why="there is no such army")
    if row.commander_entity_id != call.me.id and row.owner_entity_id not in await sides_of(call):
        fail(REFUSED, why="you neither command nor own that army")
    if held(army.id):
        fail(REFUSED, why="that army is held")
    return army, row, profile


async def siege_for(call: MortalCall, siege_id: int, *, besieger: bool) -> SiegeRow:
    siege = await call.session.get(SiegeRow, siege_id)
    if siege is None or siege.status is not SiegeStatus.ONGOING:
        fail(REFUSED, why="there is no such siege going on")
    side = siege.besieger_entity_id if besieger else siege.besieged_entity_id
    if side not in await sides_of(call):
        fail(REFUSED, why="you stand on the other side of that siege" if besieger else "that place is not yours to defend")
    if held(siege.besieged_entity_id):
        fail(REFUSED, why="that siege is held")
    return siege


async def set_army_stance(call: MortalCall, args: ArmyStanceInput) -> str:
    army, _, profile = await commanded(call, args.army_id)
    if "stance" in profile.locked:
        fail(REFUSED, why="its stance is held")
    profile.stance = args.stance
    call.target(army.id)
    await call.record("tools.mortal.set_army_stance", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.SUBJECT: army.id}, facts={"stance": args.stance})
    return result(MortalResult.STANCE_SET, army=army.name, stance=STANCES[args.stance].label.lower())


async def assign_army_role(call: MortalCall, args: ArmyRoleInput) -> str:
    army, row, _ = await commanded(call, args.army_id)
    mortal = await living_entity(call.session, args.mortal_id)
    if mortal is None or mortal.entity_type is not EntityType.MORTAL or held(mortal.id):
        fail(REFUSED, why="that is no free mortal")
    if mortal.id != call.me.id and not await same_region(call, mortal):
        fail(REFUSED, why=f"{mortal.name} is too far from you")
    await appoint(call.tick, army.id, mortal.id, args.role)
    if args.role is ArmyRole.COMMANDER:
        row.commander_entity_id = mortal.id
    call.target(mortal.id)
    await call.record(
        "tools.mortal.assign_army_role",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.SUBJECT: army.id, IncidentRole.LEADER: mortal.id},
        facts={"role": args.role},
    )
    return result(MortalResult.ROLE_ASSIGNED, name=mortal.name, army=army.name, role=ARMY_ROLES[args.role].label.lower())


async def decide_captives(call: MortalCall, args: CaptiveFateInput) -> str:
    row = await call.session.get(CaptiveCohortRow, args.cohort_id)
    if row is None or row.fate is not CaptiveFate.HELD or row.captor_entity_id not in await sides_of(call):
        fail(REFUSED, why="you hold no such band of captives")
    if args.fate is CaptiveFate.HELD:
        fail(REFUSED, why="they are held already")
    if held(row.captor_entity_id) or "fate" in row.locked:
        fail(REFUSED, why="their fate is held")
    count = row.count
    await settle_cohort(call.tick, row.id, args.fate, None)
    call.target(row.captor_entity_id)
    await call.record("tools.mortal.decide_captives", roles={IncidentRole.ACTOR: call.me.id}, facts={"fate": args.fate, "count": count})
    return result(MortalResult.CAPTIVES_DECIDED, captives=several(count, "captive", "captives"), fate=CAPTIVE_FATES[args.fate].label.lower())


async def suborn_garrison(call: MortalCall, args: SubornInput) -> str:
    siege = await siege_for(call, args.siege_id, besieger=True)
    target = await living_entity(call.session, args.target_id)
    if target is None or siege.besieged_entity_id not in {target.id, target.location_id}:
        fail(REFUSED, why="whoever you work on must be inside the besieged place")
    walls = await call.session.get(SettlementInfrastructureRow, siege.besieged_entity_id)
    siege.last_action, siege.ordered_epoch = SiegeAction.SUBORN, call.epoch
    opened = await suborn(call.tick, siege, walls)
    call.target(siege.besieged_entity_id)
    town = await call.session.get(EntityRow, siege.besieged_entity_id)
    return result(MortalResult.SUBORNED if opened else MortalResult.SUBORN_FOUND_OUT, town=town.name if town is not None else "")


class Before:
    def __init__(self, army: EntityRow, owner: EntityRow, profile: ArmyProfileRow) -> None:
        self.army, self.owner, self.profile = army, owner, profile


async def order_siege_work(call: MortalCall, args: SiegeWorkInput) -> str:
    siege = await siege_for(call, args.siege_id, besieger=True)
    army_row = await call.session.scalar(
        select(ArmyRow).where(ArmyRow.owner_entity_id == siege.besieger_entity_id, ArmyRow.disbanded_epoch.is_(None)).order_by(ArmyRow.entity_id).limit(1)
    )
    army = await living_entity(call.session, army_row.entity_id) if army_row is not None else None
    owner = await living_entity(call.session, siege.besieger_entity_id)
    profile = await call.session.get(ArmyProfileRow, army.id) if army is not None else None
    if army is None or owner is None or profile is None:
        fail(REFUSED, why="no army of yours lies before those walls")
    if args.work not in await capable(call.tick, siege, Before(army, owner, profile), 1.0):
        fail(REFUSED, why=f"your army cannot raise {SIEGE_WORKS[args.work].label.lower()}")
    progress(call.tick, siege, [args.work])
    call.target(siege.besieged_entity_id)
    done = int((siege.works or {}).get(args.work.value, 0))
    await call.record(
        "tools.mortal.order_siege_work",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.TARGET: siege.besieged_entity_id},
        facts={"work": args.work, "done": done},
    )
    return result(MortalResult.WORK_ORDERED, work=SIEGE_WORKS[args.work].label.lower(), done=done)


async def defend_siege(call: MortalCall, args: DefendInput) -> str:
    siege = await siege_for(call, args.siege_id, besieger=False)
    walls = await call.session.get(SettlementInfrastructureRow, siege.besieged_entity_id)
    if DEFENCES[args.defence].needs_water and not await floodable(call.tick, siege.besieged_entity_id, walls):
        fail(REFUSED, why="there is no river or water works to open on the approaches")
    if "last_defence" in siege.locked:
        fail(REFUSED, why="its defence is held")
    siege.last_defence, siege.ordered_epoch = args.defence, call.epoch
    town = await call.session.get(EntityRow, siege.besieged_entity_id)
    call.target(siege.besieged_entity_id)
    await call.record(
        "tools.mortal.defend_siege", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.TARGET: siege.besieged_entity_id}, facts={"defence": args.defence}
    )
    return result(MortalResult.DEFENCE_ORDERED, town=town.name if town is not None else "", defence=DEFENCES[args.defence].label.lower())


async def decide_fall(call: MortalCall, args: FallInput) -> str:
    siege = await siege_for(call, args.siege_id, besieger=True)
    if "choice" in siege.locked:
        fail(REFUSED, why="what becomes of that place is held")
    siege.choice, siege.ordered_epoch = args.choice, call.epoch
    call.target(siege.besieged_entity_id)
    await call.record(
        "tools.mortal.decide_fall", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.TARGET: siege.besieged_entity_id}, facts={"choice": args.choice}
    )
    return result(MortalResult.FALL_DECIDED, choice=FALL_CHOICES[args.choice].label.lower())


async def negotiate_surrender(call: MortalCall, args: NegotiateInput) -> str:
    siege = await siege_for(call, args.siege_id, besieger=True)
    town = await call.session.get(EntityRow, siege.besieged_entity_id)
    name = town.name if town is not None else ""
    if not await surrenders(call.tick, siege, SiegeAction.NEGOTIATE):
        siege.last_action, siege.ordered_epoch = SiegeAction.NEGOTIATE, call.epoch
        return result(MortalResult.SURRENDER_REFUSED, town=name)
    siege.status, siege.ended_epoch = SiegeStatus.SURRENDERED, call.epoch
    await offer_terms(call.tick, siege)
    call.target(siege.besieged_entity_id)
    await call.record("tools.mortal.negotiate_surrender", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.TARGET: siege.besieged_entity_id})
    return result(MortalResult.SURRENDER_TAKEN, town=town.name if town is not None else "")


async def spymaster_realm(call: MortalCall) -> EntityRow:
    office = await call.session.scalar(
        select(OfficeRow.polity_entity_id).where(OfficeRow.holder_entity_id == call.me.id, OfficeRow.kind == OfficeKind.SPYMASTER).limit(1)
    )
    realm = await living_entity(call.session, office) if office is not None else None
    if realm is None:
        fail(REFUSED, why="only a realm's spymaster can do this")
    if held(realm.id):
        fail(REFUSED, why="your realm is held")
    return realm


async def run_operation(call: MortalCall, args: OperationInput) -> str:
    realm = await spymaster_realm(call)
    target = await living_entity(call.session, args.target_id)
    if target is None or target.id == realm.id or held(target.id):
        fail(REFUSED, why="that is no realm or community you can work against")
    text = await order_spy_operation(call.tick, realm.id, target.id, args.operation)
    call.target(target.id)
    await call.record("tools.mortal.run_operation", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.TARGET: target.id}, facts={"operation": args.operation})
    return result(MortalResult.OPERATION_RUN, operation=OPERATIONS[args.operation].label.lower(), target=target.name, told=text)


def fits(motive: RecruitMotive, found: RecruitMotive, heart: RecruitMotive | None) -> bool:
    return motive is RecruitMotive.MONEY or motive is found or motive is heart


async def recruit_agent(call: MortalCall, args: RecruitAgentInput) -> str:
    realm = await spymaster_realm(call)
    mortal = await living_entity(call.session, args.mortal_id)
    if mortal is None or mortal.entity_type is not EntityType.MORTAL or mortal.status is not EntityStatus.CANON or held(mortal.id):
        fail(REFUSED, why="that is no free mortal")
    home = mortal.location_id
    target = await living_entity(call.session, home) if home is not None else None
    if target is None or target.id == realm.id:
        fail(REFUSED, why="an agent is won among those you spy on, not your own")
    taken = await call.session.scalar(select(SpyAgentRow.id).where(SpyAgentRow.mortal_entity_id == mortal.id).limit(1))
    if taken is not None:
        fail(REFUSED, why=f"{mortal.name} already serves a network")
    network = await network_for(call.tick, realm, target, None)
    await call.session.flush()
    if not fits(args.motive, await motive_for(call.tick, network, mortal), await motive_by_heart(call.tick, network, mortal)):
        fail(REFUSED, why=f"{mortal.name} cannot be won {MOTIVES[args.motive].text}")
    agent = SpyAgentRow(
        network_id=network.id,
        mortal_entity_id=mortal.id,
        cover=network.cover,
        skill=network.depth // 2,
        exposure=0,
        motive=args.motive,
        loyalty=loyalty_for(call.tick, args.motive),
        status=AgentStatus.ACTIVE,
        since_epoch=call.epoch,
        locked=[],
    )
    call.session.add(agent)
    network.agent_ids = sorted({*network.agent_ids, mortal.id})
    if "agents" not in network.locked:
        network.agents += 1
    await call.session.flush()
    call.target(mortal.id)
    await call.record("tools.mortal.recruit_agent", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.SUBJECT: mortal.id}, facts={"motive": args.motive})
    return result(MortalResult.AGENT_RECRUITED, name=mortal.name, motive=MOTIVES[args.motive].text)


async def grant_veterans(call: MortalCall, args: VeteransInput) -> str:
    office = await call.session.scalar(
        select(OfficeRow.polity_entity_id).where(OfficeRow.holder_entity_id == call.me.id, OfficeRow.kind == OfficeKind.RULER).limit(1)
    )
    realm = await living_entity(call.session, office) if office is not None else None
    if realm is None:
        fail(REFUSED, why="only a ruler sets what veterans are granted")
    if held(realm.id):
        fail(REFUSED, why="your realm is held")
    row = await set_policy(call.tick, realm.id, args.grant)
    if row.grant is not args.grant:
        fail(REFUSED, why="what your realm grants its veterans is held")
    call.target(realm.id)
    await call.record("tools.mortal.grant_veterans", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.SUBJECT: realm.id}, facts={"grant": args.grant})
    return result(MortalResult.VETERANS_GRANTED, realm=realm.name, grant=VETERAN_GRANTS[args.grant].label.lower())


def specs() -> list[ToolSpec[MortalCall, Any]]:
    mortal = AgentKind.MORTAL
    war = ToolMeta(ActionKind.COMMAND, mortal_standard_action)
    spy = ToolMeta(ActionKind.BUILD_SPY_NETWORK, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.SET_ARMY_STANCE, mortal, ArmyStanceInput, war, set_army_stance),
        ToolSpec(MortalToolId.ASSIGN_ARMY_ROLE, mortal, ArmyRoleInput, war, assign_army_role),
        ToolSpec(MortalToolId.DECIDE_CAPTIVES, mortal, CaptiveFateInput, war, decide_captives),
        ToolSpec(MortalToolId.SUBORN_GARRISON, mortal, SubornInput, war, suborn_garrison),
        ToolSpec(MortalToolId.ORDER_SIEGE_WORK, mortal, SiegeWorkInput, war, order_siege_work),
        ToolSpec(MortalToolId.DEFEND_SIEGE, mortal, DefendInput, war, defend_siege),
        ToolSpec(MortalToolId.DECIDE_FALL, mortal, FallInput, war, decide_fall),
        ToolSpec(MortalToolId.NEGOTIATE_SURRENDER, mortal, NegotiateInput, war, negotiate_surrender),
        ToolSpec(MortalToolId.RUN_OPERATION, mortal, OperationInput, spy, run_operation),
        ToolSpec(MortalToolId.RECRUIT_AGENT, mortal, RecruitAgentInput, spy, recruit_agent),
        ToolSpec(MortalToolId.GRANT_VETERANS, mortal, VeteransInput, ToolMeta(ActionKind.COMMAND, mortal_standard_action), grant_veterans),
    ]
