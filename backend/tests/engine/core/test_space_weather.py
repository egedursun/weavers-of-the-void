from dataclasses import replace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.means import NavigationKitRow
from aerona.db.tables.space_weather import SpaceWeatherEventRow, WorldFieldRow
from aerona.db.write_guard import HELD_SCOPE, HeldScope
from aerona.domain.enums.means import NavigationAid
from aerona.domain.enums.space_weather import SpaceWeatherKind
from aerona.engine.context import TickContext
from aerona.engine.means.navigation import aid_works
from aerona.engine.space_weather.weather import SpaceWeatherTally, keep_space_weather
from tests.engine.core.factories import CoreWorld, tuned_rules


def stormy(ctx: TickContext, **values: int) -> TickContext:
    table = {"burst_base_pct": 100, "outage_threshold": 0, "reversal_chance_per_epoch_pct": 0, **values}
    return replace(ctx, environment=replace(ctx.environment, rules=tuned_rules(space_weather=table)))


async def test_a_burst_through_a_weak_shield_reaches_the_ground_and_silences_the_world(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    world.world.magnetism = 0
    session.add(WorldFieldRow(world_id=world.world.id, shielding=0, locked=[]))
    await session.flush()
    tally = SpaceWeatherTally()
    await keep_space_weather(stormy(ctx), tally)
    event = await session.scalar(select(SpaceWeatherEventRow).where(SpaceWeatherEventRow.world_id == world.world.id))
    assert event is not None and event.kind is SpaceWeatherKind.COSMIC_RAY_BURST and event.dose > 0
    field = await session.get(WorldFieldRow, world.world.id)
    assert field is not None and field.compass_error >= event.dose
    kinds = set(await session.scalars(select(IncidentRow.kind)))
    assert {"sky.cosmic_ray_burst", "sky.outage"} <= kinds


async def test_a_field_reversal_weakens_the_shield_for_its_years_and_is_told(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    await keep_space_weather(stormy(ctx, burst_base_pct=0, reversal_chance_per_epoch_pct=100), SpaceWeatherTally())
    field = await session.get(WorldFieldRow, world.world.id)
    assert field is not None and field.reversal_left > 0 and field.reversal_epoch == ctx.epoch
    assert await session.scalar(select(IncidentRow.id).where(IncidentRow.kind == "sky.field_reversal")) is not None


async def test_a_held_world_takes_no_weather(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    token = HELD_SCOPE.set(HeldScope(None, frozenset({world.world.id})))
    try:
        await keep_space_weather(stormy(ctx), SpaceWeatherTally())
    finally:
        HELD_SCOPE.reset(token)
    assert await session.scalar(select(SpaceWeatherEventRow.id)) is None


async def test_a_compass_errs_once_the_field_errs_past_its_threshold(world: CoreWorld, ctx: TickContext) -> None:
    kit = NavigationKitRow(holder_entity_id=world.people.id, aid=NavigationAid.COMPASS, quality=50, since_epoch=0, locked=[])
    world.world.magnetism = 100
    threshold = ctx.rules.space_weather.compass_error_threshold
    assert aid_works(ctx.rules, kit, world.world, threshold - 1)
    assert not aid_works(ctx.rules, kit, world.world, threshold)
