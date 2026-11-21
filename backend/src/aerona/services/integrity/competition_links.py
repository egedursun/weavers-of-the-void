from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.competition import CartelRow, MarketStructureRow, PriceWarRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.competition import PriceWarOutcome
from aerona.domain.enums.entity import EntityStatus
from aerona.engine.governance.seats import apportioned


async def uneven_shares(session: AsyncSession) -> list[int]:
    return [
        row.id
        for row in await session.scalars(select(MarketStructureRow).order_by(MarketStructureRow.id))
        if row.sellers and sum(int(share) for share in row.sellers.values()) + row.small_sellers_pct != PERCENT
    ]


async def even_shares(session: AsyncSession, key: int) -> None:
    row = await session.get(MarketStructureRow, key)
    if row is None or not row.sellers:
        return
    weights = {node: float(max(1, int(share))) for node, share in row.sellers.items()}
    row.sellers = dict(apportioned(weights, PERCENT - row.small_sellers_pct))


async def outside_members(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for cartel in await session.scalars(select(CartelRow).where(CartelRow.broken_epoch.is_(None)).order_by(CartelRow.id)):
        sellers: set[int] = set()
        for structure in await session.scalars(
            select(MarketStructureRow).where(MarketStructureRow.commodity == cartel.commodity, MarketStructureRow.market_entity_id.in_(cartel.markets or []))
        ):
            sellers |= {int(node) for node in structure.sellers or {}}
        if any(member not in sellers for member in cartel.members or []):
            found.append(cartel.id)
    return found


async def drop_outsiders(session: AsyncSession, key: int) -> None:
    cartel = await session.get(CartelRow, key)
    if cartel is None:
        return
    sellers: set[int] = set()
    for structure in await session.scalars(
        select(MarketStructureRow).where(MarketStructureRow.commodity == cartel.commodity, MarketStructureRow.market_entity_id.in_(cartel.markets or []))
    ):
        sellers |= {int(node) for node in structure.sellers or {}}
    cartel.members = [member for member in cartel.members or [] if member in sellers]


async def marketless_wars(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for war in await session.scalars(select(PriceWarRow).where(PriceWarRow.outcome == PriceWarOutcome.ONGOING).order_by(PriceWarRow.id)):
        market = await session.get(EntityRow, war.market_entity_id)
        if market is None or market.status is not EntityStatus.CANON:
            found.append(war.id)
    return found


async def call_off_war(session: AsyncSession, key: int) -> None:
    war = await session.get(PriceWarRow, key)
    if war is not None:
        war.outcome = PriceWarOutcome.CALLED_OFF
