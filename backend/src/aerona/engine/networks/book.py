from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.read_memo import memoized
from aerona.db.tables.economy import CurrencyRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.networks import NetworkNodeRow, NetworkProfileRow
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.networks import NetworkCarrier
from aerona.engine.primitives.numbers import clamp_percent
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


async def shake_ledger(session: AsyncSession, rules: Rules, network_id: int) -> None:
    for ledger in await session.scalars(select(CurrencyRow).where(CurrencyRow.issuer_entity_id == network_id, CurrencyRow.metal.is_(None))):
        if not ledger.held:
            ledger.trust = clamp_percent(ledger.trust - rules.networks.ledger_shock)


async def networked_with(session: AsyncSession, communities: set[int]) -> set[int]:
    if not communities:
        return set()
    shared = select(NetworkNodeRow.network_entity_id).where(NetworkNodeRow.member_node_id.in_(communities))
    found = set(await session.scalars(select(NetworkNodeRow.member_node_id).where(NetworkNodeRow.network_entity_id.in_(shared))))
    return found - communities


async def command_factor(session: AsyncSession, rules: Rules, owner_id: int, epoch: int) -> float:
    owned = select(NetworkProfileRow).where(NetworkProfileRow.owner_node_id == owner_id, NetworkProfileRow.carries_control.is_(True))
    networks = list(await session.scalars(owned))
    if not networks:
        return 1.0
    if any(running(row, epoch) for row in networks):
        return 1 + rules.networks.command_pct / PERCENT
    return 1 - rules.networks.confusion_pct / PERCENT


@memoized(NetworkProfileRow, NetworkNodeRow, EntityRow)
async def reaching_capacities(session: AsyncSession, node_id: int, epoch: int, kind: str) -> tuple[int, ...]:
    statement = (
        select(NetworkProfileRow)
        .join(NetworkNodeRow, NetworkNodeRow.network_entity_id == NetworkProfileRow.network_entity_id)
        .where(NetworkNodeRow.member_node_id.in_(await homes(session, node_id)))
    )
    return tuple(profile.capacity for profile in await session.scalars(statement) if running(profile, epoch) and getattr(profile, kind))


async def reach_pct(session: AsyncSession, rules: Rules, node_id: int, epoch: int, *, kind: str) -> int:
    weight = rules.networks.rumour_pct if kind == "carries_opinion" else rules.networks.diffusion_pct
    return max([0, *(capacity * weight // PERCENT for capacity in await reaching_capacities(session, node_id, epoch, kind))])
