from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.transform import TransformationRow
from aerona.domain.enums.entity import EntityType, MortalRole
from aerona.engine.primitives.manual import manual_context
from aerona.engine.transform.beings import curse_into_beast, former_role
from aerona.engine.transform.ledger import TYPE_BOUND, Ledger
from tests.engine.core.factories import CoreWorld, mortal, tuned_rules


def test_every_column_bound_to_one_kind_of_record_is_known_to_the_retyping() -> None:
    assert TYPE_BOUND["mortal_role"] == "mortal" and TYPE_BOUND["death_event_entity_id"] == "mortal" and len(TYPE_BOUND) >= 7


async def test_a_mortal_with_a_role_is_cursed_into_a_beast_and_keeps_its_role_to_come_back_to(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "beast", tuned_rules())
    cursed = await mortal(session, "Haldis Rook", world, None)
    cursed.mortal_role = MortalRole.WARRIOR
    await session.flush()
    ledger = Ledger()
    await curse_into_beast(ctx, cursed.id, ledger)
    await session.flush()
    assert cursed.entity_type is EntityType.BEAST and cursed.mortal_role is None
    assert former_role(TransformationRow(undo=ledger.steps)) is MortalRole.WARRIOR
