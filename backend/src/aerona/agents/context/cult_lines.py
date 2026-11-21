from sqlalchemy import or_, select

from aerona.agents.context.cycle_lines import named
from aerona.agents.context.scope import Scope
from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.leader_cults import LeaderCultRow
from aerona.db.tables.polity import PolityMemberRow
from aerona.domain.enums.leader_cults import CultFate


async def mortal_cult_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    homes = select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == me.location_id)
    realms = list(await session.scalars(homes)) if me.location_id else []
    query = select(LeaderCultRow).where(
        LeaderCultRow.fate == CultFate.LIVING, or_(LeaderCultRow.leader_node_id == me.id, LeaderCultRow.polity_entity_id.in_(realms))
    )
    found: list[str] = []
    for cult in await session.scalars(query.order_by(LeaderCultRow.id)):
        tools = ", ".join(spoken(item) for item in cult.instruments or []) or "no instruments yet"
        whose = "your own cult" if cult.leader_node_id == me.id else f"the cult of {await named(scope, cult.leader_node_id)}"
        found.append(f"{whose} (cult {cult.id}): {tools}; intensity {cult.intensity}, sincerity of the public {cult.sincerity}")
    return found
