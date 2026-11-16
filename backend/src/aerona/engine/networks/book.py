from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.networks import NetworkNodeRow, NetworkProfileRow
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.networks import NetworkCarrier
from aerona.rules.registry import Rules

CARRIER_DAYS = {
    NetworkCarrier.RELAY: "relay_days",
    NetworkCarrier.WIRED: "wired_days",
    NetworkCarrier.BROADCAST: "broadcast_days",
    NetworkCarrier.MESH: "mesh_days",
    NetworkCarrier.MIND_LINK: "mind_link_days",
    NetworkCarrier.RITE_LINK: "rite_link_days",
    NetworkCarrier.GROWN_LINK: "grown_link_days",
}


def carrier_days(rules: Rules, carrier: NetworkCarrier) -> int:
    found: int = getattr(rules.networks, CARRIER_DAYS[carrier])
    return found


async def members_of(session: AsyncSession, network_id: int) -> int:
    return int(await session.scalar(select(func.count()).select_from(NetworkNodeRow).where(NetworkNodeRow.network_entity_id == network_id)) or 0)


async def homes(session: AsyncSession, node_id: int) -> list[int]:
    entity = await session.get(EntityRow, node_id)
    found = [node_id]
    if entity is not None and entity.location_id is not None:
        found.append(entity.location_id)
    return found


def running(profile: NetworkProfileRow, epoch: int) -> bool:
    return profile.down_until_epoch <= epoch


async def shared_networks(session: AsyncSession, first: int, second: int, epoch: int) -> list[NetworkProfileRow]:
    mine = select(NetworkNodeRow.network_entity_id).where(NetworkNodeRow.member_node_id.in_(await homes(session, first)))
    theirs = select(NetworkNodeRow.network_entity_id).where(NetworkNodeRow.member_node_id.in_(await homes(session, second)))
    statement = (
        select(NetworkProfileRow)
        .join(EntityRow, EntityRow.id == NetworkProfileRow.network_entity_id)
        .where(NetworkProfileRow.network_entity_id.in_(mine), NetworkProfileRow.network_entity_id.in_(theirs), EntityRow.status == EntityStatus.CANON)
        .order_by(NetworkProfileRow.network_entity_id)
    )
    return [row for row in await session.scalars(statement) if running(row, epoch)]


async def message_epochs(session: AsyncSession, rules: Rules, first: int, second: int, epoch: int) -> int | None:
    days = [row.delay_days for row in await shared_networks(session, first, second, epoch) if row.carries_messages]
    if not days:
        return None
    worlds = {await session.scalar(select(EntityRow.world_id).where(EntityRow.id == node)) for node in (first, second)}
    crossing = rules.networks.interworld_days if len(worlds) > 1 else 0
    return -(-(min(days) + crossing) // max(1, rules.networks.days_per_epoch))


async def reach_pct(session: AsyncSession, rules: Rules, node_id: int, epoch: int, *, kind: str) -> int:
    statement = (
        select(NetworkProfileRow)
        .join(NetworkNodeRow, NetworkNodeRow.network_entity_id == NetworkProfileRow.network_entity_id)
        .where(NetworkNodeRow.member_node_id.in_(await homes(session, node_id)))
    )
    best = 0
    for profile in await session.scalars(statement):
        if not running(profile, epoch) or not getattr(profile, kind):
            continue
        weight = rules.networks.rumour_pct if kind == "carries_opinion" else rules.networks.diffusion_pct
        best = max(best, profile.capacity * weight // PERCENT)
    return best
