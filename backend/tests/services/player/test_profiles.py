import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.ledger_undo import UndoRun
from aerona.db.tables.environment import PlaceEnvironmentRow
from aerona.db.tables.interconnect import ModifierRow
from aerona.domain.enums.environment import PlaceCover, WaterSource
from aerona.domain.enums.modifier import ModifierSource
from aerona.services.ledger import changes_of
from aerona.services.ledger_narration import label_names, node_names
from aerona.services.player import profiles
from aerona.services.player.scope import PlayerScope
from tests.services.player.factories import PlayerWorld

TABLE = "place_environment"


async def _place(session: AsyncSession, world: PlayerWorld) -> PlaceEnvironmentRow:
    row = PlaceEnvironmentRow(entity_id=world.region.id, cover=PlaceCover.OPEN, water_source=WaterSource.NONE, height_advantage=10, soil_fertility=40)
    session.add(row)
    await session.flush()
    return row


async def test_a_profile_value_is_set_held_and_released(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    row = await _place(session, world)
    await profiles.set_profile_value(scope, profiles.SetProfileValue(node_id=row.entity_id, table=TABLE, column="cover", value="heavy"))
    assert row.cover is PlaceCover.HEAVY
    assert row.locked == ["cover"]
    tables = {table.table: table for table in await profiles.profile_tables(session, row.entity_id)}
    cover = next(column for column in tables[TABLE].columns if column.name == "cover")
    assert cover.held and cover.kind == profiles.CHOICE_KIND and "light" in cover.options
    await profiles.release_profile_value(scope, profiles.ReleaseProfileValue(node_id=row.entity_id, table=TABLE, column="cover"))
    assert row.locked == []
    with pytest.raises(ValidationFailedError):
        await profiles.release_profile_value(scope, profiles.ReleaseProfileValue(node_id=row.entity_id, table=TABLE, column="cover"))


async def test_bad_profile_values_are_refused(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    row = await _place(session, world)
    with pytest.raises(ValidationFailedError):
        await profiles.set_profile_value(scope, profiles.SetProfileValue(node_id=row.entity_id, table=TABLE, column="cover", value="dense"))
    with pytest.raises(ValidationFailedError):
        await profiles.set_profile_value(scope, profiles.SetProfileValue(node_id=row.entity_id, table=TABLE, column="height_advantage", value=500))
    with pytest.raises(ValidationFailedError):
        await profiles.set_profile_value(scope, profiles.SetProfileValue(node_id=row.entity_id, table=TABLE, column="chokepoint", value=3))
    with pytest.raises(NotFoundError):
        await profiles.set_profile_value(scope, profiles.SetProfileValue(node_id=row.entity_id, table="modifiers", column="magnitude", value=3))
    await session.refresh(row)
    assert row.height_advantage == 10


async def test_a_profile_without_a_lock_list_is_held_by_a_pin(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    row = await _place(session, world)
    await profiles.pin_profile(scope, row.entity_id, "place_environment.nexus")
    pins = list(await session.scalars(select(ModifierRow).where(ModifierRow.source_kind == ModifierSource.PIN, ModifierRow.target_node_id == row.entity_id)))
    assert [pin.target_key for pin in pins] == ["place_environment.nexus"]
    await profiles.release_profile_value(scope, profiles.ReleaseProfileValue(node_id=row.entity_id, table=TABLE, column="nexus"))
    assert not list(await session.scalars(select(ModifierRow).where(ModifierRow.source_kind == ModifierSource.PIN)))


async def test_setting_a_profile_value_is_undoable(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    row = await _place(session, world)
    outcome = await profiles.set_profile_value(scope, profiles.SetProfileValue(node_id=row.entity_id, table=TABLE, column="height_advantage", value=70))
    assert outcome.ledger_entry_id is not None
    changes = await changes_of(session, outcome.ledger_entry_id)
    report = await UndoRun(session, world.cosmos.epoch, changes, label_names(changes, await node_names(session, changes))).run()
    assert report.conflicts == []
    await session.refresh(row)
    assert row.height_advantage == 10
    assert row.locked == []
