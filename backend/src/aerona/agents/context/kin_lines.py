from sqlalchemy import select

from aerona.agents.context.cycle_lines import named
from aerona.agents.context.scope import Scope
from aerona.core.grammar import an, spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.kin import KinGroupMemberRow, KinGroupRow, KinRoleDutyRow
from aerona.domain.enums.kin import KinRole
from aerona.engine.body.customs import people_of
from aerona.engine.kin.roles import kin_by_role
from aerona.engine.mortal.kin import godchildren_of


async def mortal_kin_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    found: list[str] = []
    folk = await people_of(session, me)
    if folk is not None:
        duties: dict[KinRole, list[str]] = {}
        for row in await session.scalars(
            select(KinRoleDutyRow)
            .where(KinRoleDutyRow.people_entity_id == folk.id, KinRoleDutyRow.strength >= scope.rules.kin.duty_floor)
            .order_by(KinRoleDutyRow.role, KinRoleDutyRow.duty)
        ):
            duties.setdefault(row.role, []).append(f"{spoken(row.duty)} {row.strength}")
        for role, owed in duties.items():
            kin = await kin_by_role(session, me.id, role)
            names = ", ".join([await named(scope, kin_id) for kin_id in kin]) if kin else "none living"
            found.append(f"your {spoken(role)} ({names}): your people bind them to {'; '.join(owed)} of 100")
    godchildren = await godchildren_of(session, me.id)
    if godchildren:
        found.append(f"your godchildren: {', '.join([await named(scope, child) for child in godchildren])}")
    groups = await session.execute(
        select(KinGroupRow, KinGroupMemberRow.adopted)
        .join(KinGroupMemberRow, KinGroupMemberRow.group_id == KinGroupRow.id)
        .where(KinGroupMemberRow.member_node_id == me.id)
        .order_by(KinGroupRow.id)
    )
    for group, adopted in groups:
        head = await named(scope, group.head_node_id) if group.head_node_id is not None else "no head"
        land = f", holding {await named(scope, group.land_region_id)}" if group.land_region_id is not None else ""
        joined = " (adopted)" if adopted else ""
        found.append(
            f"your kin group {group.name}{joined}: {an(spoken(group.form))} by {spoken(group.membership)}, head {head}, exogamy {group.exogamy} of 100{land}"
        )
    return found
