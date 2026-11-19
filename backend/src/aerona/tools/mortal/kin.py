from typing import Any

from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.households import HouseholdMemberRow
from aerona.db.tables.kin import KinGroupMemberRow, KinGroupRow, KinRoleDutyRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.genetics import HouseholdRole
from aerona.domain.enums.kin import KinAgenda, KinDuty, KinNeed, KinRole
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.body.customs import people_of
from aerona.engine.economy.purse import shift_points
from aerona.engine.kin.duties import KinTally, avenge, breach
from aerona.engine.kin.groups import GroupTally, choose_head, members_of, share_land
from aerona.engine.kin.roles import kin_by_role
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail

NEED_DUTIES = {
    KinNeed.FOOD: KinDuty.SUPPORT,
    KinNeed.COIN: KinDuty.SUPPORT,
    KinNeed.CARE: KinDuty.SUPPORT,
    KinNeed.SHELTER: KinDuty.HOST,
    KinNeed.PROTECTION: KinDuty.PROTECT,
}
TEN = 10


class CallOnKinInput(ToolInput):
    role: KinRole
    need: KinNeed


class ConveneKinGroupInput(ToolInput):
    group_id: int
    agenda: KinAgenda


async def strength_of(call: MortalCall, folk_id: int | None, role: KinRole, duty: KinDuty) -> int:
    if folk_id is None:
        return 0
    row = await call.session.get(KinRoleDutyRow, (folk_id, role, duty))
    return row.strength if row is not None else 0


async def answer(call: MortalCall, giver: EntityRow, need: KinNeed, strength: int) -> str:
    table = call.rules.kin
    me = await call.session.get(MortalProfileRow, call.me.id)
    if need in {KinNeed.FOOD, KinNeed.COIN}:
        theirs = await call.session.get(MortalProfileRow, giver.id)
        share = round_half_up((theirs.wealth if theirs else 0) * table.help_share_pct * strength / (PERCENT * PERCENT))
        await shift_points(call.session, giver, -share)
        await shift_points(call.session, call.me, share)
        return f"{share} of their wealth"
    if need is KinNeed.SHELTER:
        home = await call.session.get(HouseholdMemberRow, giver.id)
        if home is not None and await call.session.get(HouseholdMemberRow, call.me.id) is None:
            call.session.add(HouseholdMemberRow(member_node_id=call.me.id, household_id=home.household_id, role=HouseholdRole.LODGER, joined_epoch=call.epoch))
            return "a place in their household"
        return "a roof for a while"
    if me is not None and "stress" not in (me.locked or []):
        me.stress = clamp_int(me.stress - strength // TEN, 0, PERCENT)
    return "their care and watch"


async def call_on_kin(call: MortalCall, args: CallOnKinInput) -> str:
    folk = await people_of(call.session, call.me)
    duty = NEED_DUTIES[args.need]
    strength = await strength_of(call, folk.id if folk else None, args.role, duty)
    kin = [kin_id for kin_id in await kin_by_role(call.session, call.me.id, args.role) if not held(kin_id)]
    living = [entity for kin_id in kin if (entity := await call.session.get(EntityRow, kin_id)) is not None and entity.status is EntityStatus.CANON]
    if not living:
        fail(MortalResult.KIN_REFUSED, why=f"you have no living {spoken(args.role)}")
    giver = living[0]
    await call.record(
        "kin.called_on",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.TARGET: giver.id},
        facts={"role": args.role, "need": args.need},
        place=call.me.location_id,
    )
    call.target(giver.id)
    if strength < call.rules.kin.duty_floor:
        await breach(call.tick, giver, call.me, args.role, duty)
        return result(MortalResult.KIN_DENIED, name=giver.name, duty=spoken(duty))
    gift = await answer(call, giver, args.need, strength)
    await call.record(
        "kin.duty_kept",
        roles={IncidentRole.ACTOR: giver.id, IncidentRole.TARGET: call.me.id},
        facts={"duty": duty, "role": args.role},
        place=call.me.location_id,
    )
    return result(MortalResult.KIN_ANSWERED, name=giver.name, gift=gift)


async def convene_kin_group(call: MortalCall, args: ConveneKinGroupInput) -> str:
    group = await call.session.get(KinGroupRow, args.group_id)
    if group is None or await call.session.get(KinGroupMemberRow, (args.group_id, call.me.id)) is None:
        fail(MortalResult.KIN_REFUSED, why="you belong to no such kin group")
    if held(group.people_entity_id):
        fail(MortalResult.KIN_REFUSED, why="a god holds the kin groups of your people as they are")
    members = await members_of(call.session, group.id)
    outcome = "the kin talked and parted"
    if args.agenda is KinAgenda.CHOOSE_HEAD:
        group.head_node_id = None if "head_node_id" not in (group.locked or []) else group.head_node_id
        await choose_head(call.tick, group, members, GroupTally())
        outcome = "a head was chosen"
    elif args.agenda is KinAgenda.SHARE_LAND:
        await share_land(call.tick, group, members, GroupTally())
        outcome = "the yield of the kin land was shared"
    elif args.agenda is KinAgenda.FEUD:
        tally = KinTally()
        for member in members:
            dead = await call.session.get(EntityRow, member.member_node_id)
            if dead is not None and dead.status is EntityStatus.DEAD:
                await avenge(call.tick, dead, group.people_entity_id, len(members), tally)
        outcome = "the kin took up the feud" if tally.avenged else "there was no blood to answer"
    elif args.agenda is KinAgenda.MARRIAGE and "exogamy" not in (group.locked or []):
        group.exogamy = clamp_int(group.exogamy + TEN, 0, PERCENT)
        outcome = "the rule against marrying within the kin was tightened"
    elif args.agenda is KinAgenda.MIGRATE:
        moved = 0
        for member in members:
            entity = await call.session.get(EntityRow, member.member_node_id)
            if entity is not None and entity.status is EntityStatus.CANON and not held(entity.id) and entity.id != call.me.id:
                entity.location_id = call.me.location_id
                moved += 1
        outcome = "the kin moved to your side" if moved else "no one moved"
    await call.record(
        "kin.group_convened",
        roles={IncidentRole.ACTOR: call.me.id},
        facts={"group": group.name, "agenda": args.agenda},
        place=call.me.location_id,
    )
    call.target(call.me.id)
    return result(MortalResult.KIN_CONVENED, group=group.name, outcome=outcome)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    return [
        ToolSpec(MortalToolId.CALL_ON_KIN, AgentKind.MORTAL, CallOnKinInput, ToolMeta(ActionKind.INFLUENCE, mortal_standard_action), call_on_kin),
        ToolSpec(
            MortalToolId.CONVENE_KIN_GROUP, AgentKind.MORTAL, ConveneKinGroupInput, ToolMeta(ActionKind.INFLUENCE, mortal_standard_action), convene_kin_group
        ),
    ]
