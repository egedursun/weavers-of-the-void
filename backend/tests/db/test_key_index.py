from aerona.db.key_index import keyed_rows
from aerona.db.session import Database
from aerona.engine.mind.thoughts import EPOCH_THOUGHTS


async def test_a_step_keeps_the_index_of_every_scope_it_asked_for(database: Database) -> None:
    async with database.steps() as steps, steps.step() as session:
        first = await keyed_rows(session, EPOCH_THOUGHTS, 1)
        second = await keyed_rows(session, EPOCH_THOUGHTS, 2)
        again = await keyed_rows(session, EPOCH_THOUGHTS, 1)
    assert first is not None and second is not None
    assert first is not second
    assert again is first
