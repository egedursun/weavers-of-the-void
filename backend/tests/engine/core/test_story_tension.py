from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.storyteller_depth import RegionalTensionRow, SubsystemTensionRow
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.engine.context import TickContext
from aerona.engine.storyteller.pace import drama
from aerona.engine.storyteller.regions import measure_parts
from tests.engine.core.factories import CoreWorld


async def happen(session: AsyncSession, ctx: TickContext, world: CoreWorld, key: str, *, told: ChronicleKind, times: int) -> None:
    for _ in range(times):
        line = ChronicleRow(epoch=ctx.epoch, kind=told, text=key, world_id=world.world.id, template_key=key)
        session.add(line)
        await session.flush()
        session.add(IncidentRow(kind=key, epoch=ctx.epoch, world_id=world.world.id, place_entity_id=world.regions[0].id, chronicle_id=line.id, magnitude=25))
    await session.flush()


async def test_daily_life_is_no_crisis_and_only_strife_raises_tension(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    await happen(session, ctx, world, "cuisine.invented", told=ChronicleKind.CULTURE, times=300)
    await happen(session, ctx, world, "trade_route.weather_loss", told=ChronicleKind.TRADE, times=40)
    assert await measure_parts(ctx, world.world.id) == 0
    assert await drama(ctx, world.world.id) == 0
    await happen(session, ctx, world, "battle.fought", told=ChronicleKind.WAR, times=20)
    assert await measure_parts(ctx, world.world.id) == 1
    row = await session.get(RegionalTensionRow, world.regions[0].id)
    assert row is not None and row.crisis
    assert await drama(ctx, world.world.id) >= 20 * 25
    told = list(await session.scalars(select(ChronicleRow.template_key).where(ChronicleRow.template_key == "storyteller.region_crisis")))
    assert told == ["storyteller.region_crisis"]


async def test_a_large_world_keeps_its_subsystems_apart_instead_of_filling_them_all(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    await happen(session, ctx, world, "cuisine.invented", told=ChronicleKind.CULTURE, times=400)
    await happen(session, ctx, world, "trade_route.weather_loss", told=ChronicleKind.TRADE, times=100)
    await measure_parts(ctx, world.world.id)
    parts = {row.subsystem: row.tension for row in await session.scalars(select(SubsystemTensionRow).where(SubsystemTensionRow.world_id == world.world.id))}
    assert parts["cuisine"] == 100 and parts["trade_route"] < parts["cuisine"]
