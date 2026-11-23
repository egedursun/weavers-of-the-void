from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.ledger_capture import capture_changes
from aerona.db.tables.ages import IrregularSeasonRow, WinterForecastRow
from aerona.domain.enums.entity import EntityType
from tests.db.factories import make_entity


async def seeded_spell(session: AsyncSession, world_id: int) -> tuple[IrregularSeasonRow, list[WinterForecastRow]]:
    spell = IrregularSeasonRow(world_id=world_id, locked=[])
    session.add(spell)
    await session.flush()
    forecasts = []
    for name in ("Amber Folk", "Coral Folk"):
        people = await make_entity(session, name, EntityType.PEOPLE, world_id=world_id)
        forecast = WinterForecastRow(long_season_id=spell.id, world_id=world_id, people_entity_id=people.id, locked=[])
        session.add(forecast)
        forecasts.append(forecast)
    await session.flush()
    return spell, forecasts


async def test_children_deleted_with_their_parent_in_one_flush_leave_cleanly(session: AsyncSession, world_id: int) -> None:
    spell, forecasts = await seeded_spell(session, world_id)
    for forecast in forecasts:
        await session.delete(forecast)
    await session.delete(spell)
    await session.flush()
    assert await session.scalar(select(IrregularSeasonRow).where(IrregularSeasonRow.world_id == world_id)) is None
    assert list(await session.scalars(select(WinterForecastRow).where(WinterForecastRow.world_id == world_id))) == []


async def test_children_deleted_with_their_parent_are_recorded(session: AsyncSession, world_id: int) -> None:
    spell, forecasts = await seeded_spell(session, world_id)
    async with capture_changes(session) as capture:
        await session.delete(spell)
        for forecast in forecasts:
            await session.delete(forecast)
        await session.flush()
        changes = await capture.changes()
    removed = [change for change in changes if change.table_name == WinterForecastRow.__tablename__]
    assert len(removed) == len(forecasts)
