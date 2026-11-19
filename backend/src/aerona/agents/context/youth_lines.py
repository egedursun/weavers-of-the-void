from sqlalchemy import select

from aerona.agents.context.cycle_lines import named
from aerona.agents.context.scope import Scope
from aerona.core.grammar import several, spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.youth import YouthGroupMemberRow, YouthGroupRow, YouthStandingRow
from aerona.engine.body.customs import people_of


async def mortal_youth_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    found: list[str] = []
    folk = await people_of(session, me)
    standing = await session.get(YouthStandingRow, folk.id) if folk is not None else None
    if standing is not None:
        found.append(
            f"among your people youth runs from {standing.youth_from} to {standing.youth_to}, spent in {spoken(standing.place)}, "
            f"with freedom {standing.freedom} and duty {standing.duty} of 100"
        )
    mine = select(YouthGroupMemberRow.group_id).where(YouthGroupMemberRow.member_node_id == me.id)
    for group in await session.scalars(select(YouthGroupRow).where(YouthGroupRow.id.in_(mine)).order_by(YouthGroupRow.id)):
        leader = "you" if group.leader_node_id == me.id else await named(scope, group.leader_node_id) if group.leader_node_id is not None else "no one"
        count = len(list(await session.scalars(select(YouthGroupMemberRow.member_node_id).where(YouthGroupMemberRow.group_id == group.id))))
        found.append(
            f"you belong to {group.name} (group {group.id}), for {spoken(group.purpose)}, led by {leader}, "
            f"{several(count, 'member', 'members')}, standing {group.standing}"
        )
    if me.location_id is not None:
        others = await session.scalars(
            select(YouthGroupRow).where(YouthGroupRow.settlement_entity_id == me.location_id, YouthGroupRow.id.not_in(mine)).order_by(YouthGroupRow.id)
        )
        for group in others:
            found.append(f"the youth group {group.name} (group {group.id}) of your town is for {spoken(group.purpose)}, standing {group.standing}")
    return found
