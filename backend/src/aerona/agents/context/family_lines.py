from sqlalchemy import or_, select

from aerona.agents.context.cycle_lines import named
from aerona.agents.context.scope import Scope
from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.kin_dynamics import ElderSwayRow, KinBlendRow, KinDisowningRow, KinFavourRow, KinRivalryRow


async def favour_lines(scope: Scope, me: EntityRow) -> list[str]:
    found: list[str] = []
    query = select(KinFavourRow).where(or_(KinFavourRow.parent_node_id == me.id, KinFavourRow.child_node_id == me.id))
    for favour in await scope.session.scalars(query.order_by(KinFavourRow.id)):
        if favour.parent_node_id == me.id:
            found.append(f"you favour {await named(scope, favour.child_node_id)} (child {favour.child_node_id}), favour {favour.strength}")
        else:
            found.append(f"{await named(scope, favour.parent_node_id)} favours you, favour {favour.strength}")
    return found


async def strife_lines(scope: Scope, me: EntityRow) -> list[str]:
    found: list[str] = []
    mine = or_(KinRivalryRow.first_node_id == me.id, KinRivalryRow.second_node_id == me.id)
    for rivalry in await scope.session.scalars(select(KinRivalryRow).where(mine, KinRivalryRow.ended_epoch.is_(None)).order_by(KinRivalryRow.id)):
        other = rivalry.second_node_id if rivalry.first_node_id == me.id else rivalry.first_node_id
        found.append(f"you and {await named(scope, other)} are rivals in the family over {spoken(rivalry.cause)}, heat {rivalry.heat}")
    cast = or_(KinDisowningRow.disowner_node_id == me.id, KinDisowningRow.disowned_node_id == me.id)
    for disowning in await scope.session.scalars(select(KinDisowningRow).where(cast, KinDisowningRow.reconciled_epoch.is_(None)).order_by(KinDisowningRow.id)):
        if disowning.disowner_node_id == me.id:
            found.append(f"you cast out {await named(scope, disowning.disowned_node_id)} (kin {disowning.disowned_node_id}) for {spoken(disowning.reason)}")
        else:
            found.append(f"{await named(scope, disowning.disowner_node_id)} cast you out of the family for {spoken(disowning.reason)}")
    return found


async def family_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    found = [*await favour_lines(scope, me), *await strife_lines(scope, me)]
    for blend in await session.scalars(select(KinBlendRow).where(KinBlendRow.member_node_id == me.id).order_by(KinBlendRow.id)):
        found.append(f"you joined your family through a later marriage, with a standing of {blend.standing}")
    elders = select(ElderSwayRow).where(ElderSwayRow.elder_node_id == me.id, ElderSwayRow.ended_epoch.is_(None)).order_by(ElderSwayRow.id)
    for elder in await session.scalars(elders):
        found.append(f"you hold sway over your family as its elder, sway {elder.sway}")
    return found
