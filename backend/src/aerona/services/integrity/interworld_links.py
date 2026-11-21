from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interworld import InterworldCampaignRow, InterworldMigrationRow
from aerona.db.tables.routes import RouteRow
from aerona.domain.enums.interworld import OPEN_CAMPAIGN, CampaignStage
from aerona.engine.cosmos.routes import touches


def joins(route: RouteRow | None, first: int, second: int) -> bool:
    return route is not None and touches(route, first) and touches(route, second)


async def open_campaigns(session: AsyncSession) -> list[InterworldCampaignRow]:
    query = select(InterworldCampaignRow).where(InterworldCampaignRow.stage.in_(sorted(OPEN_CAMPAIGN)), InterworldCampaignRow.ended_epoch.is_(None))
    return list(await session.scalars(query.order_by(InterworldCampaignRow.id)))


async def astray_campaigns(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for row in await open_campaigns(session):
        route = await session.get(RouteRow, row.route_id) if row.route_id is not None else None
        if row.route_id is not None and not joins(route, row.from_world_id, row.target_world_id):
            found.append(row.id)
    return found


async def withdraw_campaign(session: AsyncSession, key: int) -> None:
    row = await session.get(InterworldCampaignRow, key)
    if row is not None:
        row.stage, row.ended_epoch = CampaignStage.WITHDRAWN, row.begun_epoch


async def stranded_landings(session: AsyncSession) -> list[int]:
    found: list[int] = []
    for row in await open_campaigns(session):
        army = await session.get(EntityRow, row.army_entity_id) if row.army_entity_id is not None else None
        if row.stage is CampaignStage.HOLDING and (army is None or army.world_id != row.target_world_id):
            found.append(row.id)
    return found


async def astray_migrations(session: AsyncSession) -> list[int]:
    found: list[int] = []
    query = select(InterworldMigrationRow).where(InterworldMigrationRow.ended_epoch.is_(None)).order_by(InterworldMigrationRow.id)
    for row in await session.scalars(query):
        route = await session.get(RouteRow, row.route_id) if row.route_id is not None else None
        if row.from_world_id == row.to_world_id or (row.route_id is not None and not joins(route, row.from_world_id, row.to_world_id)):
            found.append(row.id)
    return found


async def end_migration(session: AsyncSession, key: int) -> None:
    row = await session.get(InterworldMigrationRow, key)
    if row is not None:
        row.ended_epoch = row.begun_epoch
