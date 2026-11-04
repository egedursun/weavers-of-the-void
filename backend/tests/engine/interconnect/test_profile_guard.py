from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.profile_guard import profile_held, profile_key, shape_of_table
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import PlaceEnvironmentRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import PlaceCover, WaterSource
from aerona.domain.enums.modifier import ModifierOp, ModifierSource
from aerona.engine.context import TickContext
from aerona.engine.interconnect.guards import run_guarded
from aerona.engine.interconnect.registry import suppression_key
from aerona.engine.phase import Phase
from aerona.engine.primitives.modifiers import ModifierDraft, add_modifier
from aerona.rules.registry import Rules
from tests.engine.warfare.factories import make, make_ctx

TABLE = "place_environment"


async def _place(session: AsyncSession, world_id: int, locked: list[str] | None = None) -> PlaceEnvironmentRow:
    place = await make(session, "Grey Ford", EntityType.REGION, world_id)
    row = PlaceEnvironmentRow(
        entity_id=place.id,
        cover=PlaceCover.OPEN,
        water_source=WaterSource.NONE,
        height_advantage=10,
        soil_fertility=40,
        locked=list(locked or []),
    )
    session.add(row)
    await session.flush()
    return row


async def _guard(session: AsyncSession, node_id: int, key: str, source: ModifierSource) -> None:
    await add_modifier(session, ModifierDraft(node_id, key, ModifierOp.ADD, 0, source, "guard.test", start_epoch=1))


async def test_a_held_profile_column_survives_an_engine_write(session: AsyncSession, world_id: int) -> None:
    row = await _place(session, world_id, locked=["height_advantage"])

    async def run(ctx: TickContext) -> None:
        row.height_advantage = 80
        row.soil_fertility = 70

    await run_guarded(Phase("test_writer", run), make_ctx(session, Rules(), epoch=5))
    assert row.height_advantage == 10
    assert row.soil_fertility == 70


async def test_a_pinned_profile_column_survives_an_autoflush_inside_the_phase(session: AsyncSession, world_id: int) -> None:
    row = await _place(session, world_id)
    await _guard(session, row.entity_id, profile_key(TABLE, "soil_fertility"), ModifierSource.PIN)

    async def run(ctx: TickContext) -> None:
        row.soil_fertility = 90
        await ctx.session.scalar(select(EntityRow.id).limit(1))
        row.height_advantage = 50

    await run_guarded(Phase("test_writer", run), make_ctx(session, Rules(), epoch=5))
    await session.refresh(row)
    assert row.soil_fertility == 40
    assert row.height_advantage == 50


async def test_a_suppressed_mechanic_cannot_write_profile_columns(session: AsyncSession, world_id: int) -> None:
    row = await _place(session, world_id)
    await _guard(session, row.entity_id, suppression_key("test_writer"), ModifierSource.SUPPRESSION)

    async def run(ctx: TickContext) -> None:
        row.chokepoint = True

    await run_guarded(Phase("test_writer", run), make_ctx(session, Rules(), epoch=5))
    assert row.chokepoint is False


async def test_holds_do_not_bind_the_player_outside_engine_phases(session: AsyncSession, world_id: int) -> None:
    row = await _place(session, world_id, locked=["height_advantage"])
    row.height_advantage = 60
    await session.flush()
    await session.refresh(row)
    assert row.height_advantage == 60
    assert profile_held(row, "height_advantage")
    assert not profile_held(row, "soil_fertility")


def test_profile_tables_are_found_by_their_entity_key() -> None:
    shape = shape_of_table(TABLE)
    assert shape is not None
    assert shape.node_column == "entity_id"
    assert shape.lockable
    assert "locked" not in shape.columns
    assert shape_of_table("modifiers") is None
