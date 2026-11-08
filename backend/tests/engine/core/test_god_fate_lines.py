from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.foreign_gods import GodConflictRow
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.war import GodConflictOutcome
from aerona.engine.cosmos.foreign_gods import NewForeignGod, add_foreign_god
from aerona.engine.primitives.manual import manual_context
from aerona.services.books.history import god_fate
from tests.engine.core.factories import CoreWorld, tuned_rules

RULES = tuned_rules()


async def test_an_old_gods_fate_tells_its_fights_and_who_slew_it(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "fate", RULES)
    god = await add_foreign_god(session, RULES, ctx.rng(), ctx.epoch, NewForeignGod("Ormuhl", world.world.id, (Domain.EARTH, None), power=5))
    son = world.son
    won, draw = GodConflictOutcome.ATTACKER_WON, GodConflictOutcome.DRAW
    session.add(GodConflictRow(epoch=2, attacker_node_id=god.id, defender_node_id=son.id, outcome=won, attacker_score=9, defender_score=3))
    session.add(GodConflictRow(epoch=3, attacker_node_id=son.id, defender_node_id=god.id, outcome=draw, attacker_score=5, defender_score=5))
    session.add(GodConflictRow(epoch=4, attacker_node_id=son.id, defender_node_id=god.id, outcome=won, attacker_score=9, defender_score=1, duel=True))
    god.defeated_epoch, god.death_epoch = 4, 4
    await session.flush()
    lines = await god_fate(session, god, {son.id: son.name})
    assert lines[0].startswith("Status: ") and f"Arose in Epoch {god.created_epoch}" in lines
    assert "Defeated in Epoch 4" in lines
    assert f"Epoch 2: conflict, defeated {son.name}" in lines
    assert f"Epoch 3: conflict, drew with {son.name}" in lines
    assert f"Epoch 4: duel, fell to {son.name}" in lines
    assert lines[-1] == f"Died in Epoch 4, slain by {son.name}"
