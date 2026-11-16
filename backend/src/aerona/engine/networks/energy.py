from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.industry import CommunityIndustryRow
from aerona.db.tables.networks import NetworkNodeRow, NetworkProfileRow
from aerona.domain.enums.industry import EnergyKind
from aerona.domain.enums.networks import NetworkCarrier
from aerona.engine.context import TickContext
from aerona.engine.economy.book import EconomyBook
from aerona.engine.industry.energy import draw, unmet_pct
from aerona.engine.networks.book import running

CARRIER_ENERGY = total(
    NetworkCarrier,
    {
        NetworkCarrier.RELAY: EnergyKind.MUSCLE,
        NetworkCarrier.WIRED: EnergyKind.ELECTRIC,
        NetworkCarrier.BROADCAST: EnergyKind.ELECTRIC,
        NetworkCarrier.MESH: EnergyKind.ELECTRIC,
        NetworkCarrier.MIND_LINK: EnergyKind.MAGIC,
        NetworkCarrier.RITE_LINK: EnergyKind.MAGIC,
        NetworkCarrier.GROWN_LINK: EnergyKind.FEED,
    },
)


async def draw_networks(ctx: TickContext, book: EconomyBook) -> int:
    drawn = 0
    joined = select(NetworkProfileRow, NetworkNodeRow.member_node_id).join(
        NetworkNodeRow, NetworkNodeRow.network_entity_id == NetworkProfileRow.network_entity_id
    )
    for profile, member in (await ctx.session.execute(joined.order_by(NetworkNodeRow.id))).all():
        if member not in book.industry or not running(profile, ctx.epoch):
            continue
        drawn += draw(book, member, CARRIER_ENERGY[profile.carrier], ctx.rules.networks.energy_draw * profile.capacity // PERCENT)
    return drawn


async def starved(session: AsyncSession, town_id: int | None, kind: EnergyKind, threshold: int) -> bool:
    row = await session.get(CommunityIndustryRow, town_id) if town_id is not None else None
    return row is not None and unmet_pct(row, kind) >= threshold
