from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.context.intrigue import name_of
from aerona.core.grammar import an
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.gatherings import GatheringGuestRow, GatheringRow
from aerona.db.tables.sites import ExcavationRow, SiteRoomRow
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.gathering import GatheringStatus
from aerona.domain.enums.site import ExcavationStatus
from aerona.engine.sites.digs import diggable
from aerona.rules.registry import Rules


async def gathering_lines(session: AsyncSession, rules: Rules, me: EntityRow, epoch: int) -> list[str]:
    since = epoch - rules.collections.join_window
    came = select(GatheringGuestRow.gathering_id).where(GatheringGuestRow.node_id == me.id, GatheringGuestRow.attended.is_(True))
    found: list[str] = []
    for row in await session.scalars(
        select(GatheringRow)
        .where(or_(GatheringRow.host_node_id == me.id, GatheringRow.id.in_(came)), GatheringRow.epoch >= since)
        .order_by(GatheringRow.epoch.desc(), GatheringRow.id.desc())
        .limit(rules.gatherings.guests_max)
    ):
        kind = row.kind.value.replace("_", " ")
        when = f"epoch {row.epoch}" if row.year is None else f"epoch {row.epoch}, year {row.year}"
        if row.status is GatheringStatus.PLANNED:
            found.append(
                f"your {kind} is planned for this epoch"
                if row.host_node_id == me.id
                else f"{await name_of(session, row.host_node_id)} has invited you to their {kind}"
            )
        elif row.host_node_id == me.id:
            found.append(f"you held {an(kind)} in {when}, {row.outcome.value if row.outcome else row.status.value}")
        else:
            found.append(f"you came to the {kind} of {await name_of(session, row.host_node_id)} in {when}")
    return found


async def site_lines(session: AsyncSession, rules: Rules, me: EntityRow) -> list[str]:
    if me.location_id is None:
        return []
    found: list[str] = []
    nearby = list(
        await session.scalars(
            select(EntityRow)
            .where(or_(EntityRow.location_id == me.location_id, EntityRow.id == me.location_id), EntityRow.status == EntityStatus.CANON)
            .order_by(EntityRow.id)
        )
    )
    for site in nearby:
        rooms = list(await session.scalars(select(SiteRoomRow).where(SiteRoomRow.site_entity_id == site.id)))
        if rooms:
            cleared = sum(room.cleared_epoch is not None for room in rooms)
            found.append(f"{site.name} (id {site.id}) has {len(rooms)} rooms, {cleared} cleared")
        if not await diggable(session, site):
            continue
        dig = await session.scalar(
            select(ExcavationRow)
            .where(ExcavationRow.site_entity_id == site.id, ExcavationRow.status.in_([ExcavationStatus.OPEN, ExcavationStatus.STALLED]))
            .limit(1)
        )
        if dig is None:
            found.append(f"{site.name} (id {site.id}) can be dug by one with lore of {rules.excavations.start_lore}")
        else:
            found.append(f"a dig at {site.name} is at its {dig.stage.value.replace('_', ' ')}, {dig.progress}% through")
    return found
