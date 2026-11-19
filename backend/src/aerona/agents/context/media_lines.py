from sqlalchemy import select

from aerona.agents.context.cycle_lines import named
from aerona.agents.context.scope import Scope
from aerona.core.grammar import spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.media import MediaItemRow, MediaOutletRow, RecordMediumRow


async def outlet_line(scope: Scope, outlet: MediaOutletRow, mine: bool) -> str:
    medium = await scope.session.get(RecordMediumRow, outlet.medium_id) if outlet.medium_id is not None else None
    by = f" by {medium.name}" if medium is not None else ""
    lean = f", leaning {outlet.lean} on {spoken(outlet.stance)}" if outlet.stance is not None else ""
    censored = ", censored" if outlet.censored else ""
    owner = "you own" if mine else f"{await named(scope, outlet.owner_node_id)} owns"
    return f"{owner} {outlet.name} (outlet {outlet.id}){by}: reach {outlet.reach}, trust {outlet.trust}{lean}, paid by {spoken(outlet.funding)}{censored}"


async def mortal_media_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    found: list[str] = []
    seen: set[int] = set()
    for outlet in await session.scalars(select(MediaOutletRow).where(MediaOutletRow.owner_node_id == me.id).order_by(MediaOutletRow.id)):
        found.append(await outlet_line(scope, outlet, True))
        seen.add(outlet.id)
    if me.location_id is not None:
        for outlet in await session.scalars(select(MediaOutletRow).where(MediaOutletRow.seat_entity_id == me.location_id).order_by(MediaOutletRow.id)):
            if outlet.id in seen:
                continue
            found.append(await outlet_line(scope, outlet, False))
            item = await session.scalar(
                select(MediaItemRow).where(MediaItemRow.outlet_id == outlet.id).order_by(MediaItemRow.epoch.desc(), MediaItemRow.id.desc()).limit(1)
            )
            if item is not None:
                subject = f" about {await named(scope, item.subject_node_id)}" if item.subject_node_id is not None else ""
                false = ", found false" if item.exposed else ""
                found.append(f"its latest {spoken(item.kind)}{subject} leans {item.slant}, accuracy {item.accuracy}{false}")
    return found
