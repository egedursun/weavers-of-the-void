from sqlalchemy import event, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.flush_batch import NUMBERED_AT_ONCE, own_key
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.facets import FacetPracticeRow
from aerona.domain.enums.facets import FacetKind
from tests.engine.core.factories import CoreWorld


async def test_new_rows_of_a_table_take_the_next_numbers_in_the_order_they_were_added_and_insert_at_once(session: AsyncSession, world: CoreWorld) -> None:
    top = int(await session.scalar(select(func.coalesce(func.max(FacetPracticeRow.id), 0))) or 0)
    facets = list(FacetKind)[: NUMBERED_AT_ONCE + 1]
    rows = [FacetPracticeRow(community_entity_id=world.people.id, facet=facet, level=10, since_epoch=0, updated_epoch=0, locked=[]) for facet in facets]
    inserts: list[str] = []
    engine = session.sync_session.get_bind()

    def seen(_connection: object, _cursor: object, statement: str, *_: object) -> None:
        if statement.startswith("INSERT INTO facet_practices"):
            inserts.append(statement)

    event.listen(engine, "before_cursor_execute", seen)
    try:
        session.add_all(rows)
        await session.flush()
    finally:
        event.remove(engine, "before_cursor_execute", seen)
    assert [row.id for row in rows] == list(range(top + 1, top + 1 + len(rows)))
    assert len(inserts) == 1


def test_only_a_table_that_numbers_its_own_rows_is_numbered_ahead() -> None:
    assert own_key(FacetPracticeRow.__mapper__) is not None
    assert own_key(EntityRow.__mapper__) is None
