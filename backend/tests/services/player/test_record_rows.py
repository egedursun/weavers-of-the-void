import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.body import ConditionRow
from aerona.domain.enums.entity import EntityType
from aerona.services.player import record_rows
from aerona.services.player.scope import PlayerScope
from tests.services.player.factories import PlayerWorld, make_entity

MELANCHOLY = {"kind": "melancholy", "source": "player", "since_epoch": 0}


async def test_any_record_row_is_made_reshaped_held_and_unmade(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    bearer = await make_entity(session, "Tovin", EntityType.MORTAL, world_id=world.world.id, location_id=world.region.id)
    made = await record_rows.create_row(
        scope,
        record_rows.CreateRow(table="conditions", values={"bearer_node_id": bearer.id, **MELANCHOLY, "severity": 2}),
    )
    row = await session.get(ConditionRow, made.values["id"])
    assert row is not None and row.severity == 2
    await record_rows.edit_row(scope, record_rows.EditRow(table="conditions", key={"id": row.id}, values={"severity": 4, "visible": False}, hold=True))
    assert row.severity == 4 and row.visible is False
    with pytest.raises(ValidationFailedError):
        await record_rows.edit_row(scope, record_rows.EditRow(table="conditions", key={"id": row.id}, values={"kind": "not_a_kind"}))
    with pytest.raises(ValidationFailedError):
        await record_rows.edit_row(scope, record_rows.EditRow(table="conditions", key={"id": row.id}, values={"no_such_value": 1}))
    await record_rows.delete_row(scope, record_rows.RowTarget(table="conditions", key={"id": row.id}))
    assert await session.get(ConditionRow, row.id) is None


async def test_identity_tables_and_ownerless_rows_are_refused(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    with pytest.raises(NotFoundError):
        await record_rows.delete_row(scope, record_rows.RowTarget(table="entities", key={"id": world.region.id}))
    with pytest.raises(ValidationFailedError):
        await record_rows.create_row(scope, record_rows.CreateRow(table="conditions", values={**MELANCHOLY, "severity": 1}))
