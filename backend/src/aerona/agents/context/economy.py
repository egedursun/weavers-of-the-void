from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.commodities import COMMODITIES
from aerona.db.tables.economy import CommunityStockRow, ResourceProfileRow, TradeRouteProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.economy import TradeRouteStatus
from aerona.domain.enums.entity import SOCIETY_TYPES
from aerona.domain.enums.society import Commodity
from aerona.engine.economy.materials import MaterialBook
from aerona.engine.economy.routes import LIVE_STATUSES
from aerona.engine.economy.stocks import aggregate_index
from aerona.engine.gods.queries import community_of
from aerona.prompts.contexts.mortal import StoresLine
from aerona.rules.registry import Rules

NOTABLE_LOTS = 6
SHORT_INDEX = 50


async def stores_for(session: AsyncSession, rules: Rules, me: EntityRow) -> StoresLine | None:
    home = me if me.entity_type in SOCIETY_TYPES else await community_of(session, me)
    if home is None or home.entity_type not in SOCIETY_TYPES:
        return None
    book = await MaterialBook.load(session)
    lots = list(await session.scalars(select(CommunityStockRow).where(CommunityStockRow.community_entity_id == home.id, CommunityStockRow.quantity > 0)))
    ranked = []
    for lot in lots:
        props = book.props(home.world_id, lot.material, lot.world_material_id)
        if props is None:
            continue
        ranked.append((props.base_value * lot.quantity, f"{props.label} {COMMODITIES[lot.commodity].label.lower()} ({lot.quantity}, quality {lot.quality})"))
    notable = [text for _, text in sorted(ranked, key=lambda item: (-item[0], item[1]))[:NOTABLE_LOTS]]
    short = [aggregate.value for aggregate in Commodity if await aggregate_index(session, rules, home, aggregate) < SHORT_INDEX]
    statement = select(TradeRouteProfileRow).where(
        TradeRouteProfileRow.status.in_(list(LIVE_STATUSES)),
        (TradeRouteProfileRow.first_market_id == home.id) | (TradeRouteProfileRow.second_market_id == home.id),
    )
    routes = []
    for profile in await session.scalars(statement):
        entity = await session.get(EntityRow, profile.route_entity_id)
        if entity is not None:
            routes.append(f"{entity.name}{' (blockaded)' if profile.status is TradeRouteStatus.BLOCKADED else ''}")
    return StoresLine(community=home.name, materials=notable, short=short, routes=sorted(routes))


async def resource_yield(session: AsyncSession, resource_id: int) -> str:
    profile = await session.get(ResourceProfileRow, resource_id)
    if profile is None:
        return ""
    material = profile.material.value.replace("_", " ") + " " if profile.material is not None else ""
    return f"{material}{COMMODITIES[profile.commodity].label.lower()}, reserve {profile.reserve}"
