from sqlalchemy import text
from sqlalchemy.dialects import sqlite

from aerona.db.session import Database
from aerona.engine.lore.tellings import earlier_incidents_of


async def test_the_earlier_incidents_of_a_cast_are_read_from_the_index_by_node_and_incident(database: Database) -> None:
    statement = earlier_incidents_of([14, 17, 16], 900000, 899000)
    sql = str(statement.compile(dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True}))
    async with database.read() as session:
        plan = " | ".join(str(row[-1]) for row in (await session.execute(text(f"EXPLAIN QUERY PLAN {sql}"))).all())
    assert "ix_incident_participants_node_id_incident_id (node_id=? AND incident_id<?)" in plan, plan
