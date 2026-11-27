from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.presence import PresenceExchangeRow, PresenceSessionRow
from aerona.domain.enums.presence import PresenceExchangeStatus, PresenceGuise, PresenceRecord
from aerona.engine.gods.reputation import compute_reputation
from aerona.rules.registry import Rules
from tests.engine.gods.factories import GodsWorld, make_son


async def audience(session: AsyncSession, son_id: int, epoch: int, guise: PresenceGuise, record: PresenceRecord) -> None:
    meeting = PresenceSessionRow(node_id=son_id, guise=guise, record=record, opened_epoch=epoch)
    session.add(meeting)
    await session.flush()
    session.add(PresenceExchangeRow(session_id=meeting.id, ordinal=1, epoch=epoch, player_text="Speak.", status=PresenceExchangeStatus.DONE))
    await session.flush()


async def test_an_audience_with_the_creator_is_the_son_last_contact(session: AsyncSession, rules: Rules, world: GodsWorld) -> None:
    son = await make_son(session, "Tidekeeper", world.world.id)
    await audience(session, son.id, 10, PresenceGuise.CREATOR, PresenceRecord.ON_RECORD)
    reputation = await compute_reputation(session, rules, son, 10, world.creator)
    assert reputation.last_contact == 10


async def test_a_disguised_or_unrecorded_visit_is_no_contact_with_the_creator(session: AsyncSession, rules: Rules, world: GodsWorld) -> None:
    son = await make_son(session, "Tidekeeper", world.world.id)
    await audience(session, son.id, 9, PresenceGuise.ORDINARY, PresenceRecord.ON_RECORD)
    await audience(session, son.id, 10, PresenceGuise.CREATOR, PresenceRecord.OFF_RECORD)
    reputation = await compute_reputation(session, rules, son, 10, world.creator)
    assert reputation.last_contact == son.birth_epoch
