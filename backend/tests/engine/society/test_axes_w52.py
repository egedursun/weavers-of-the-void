from sqlalchemy import select

from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.renown import ReputationRow
from aerona.domain.enums.renown import ReputationAxis
from aerona.engine.renown.axes import honour_axis, powerful, renown_share
from tests.engine.society.factories import Realm, context, mortal, settlement


async def test_mercy_renown_is_won_heard_and_read(realm: Realm) -> None:
    town = await settlement(realm, "Gate", population=4000)
    ruler = await mortal(realm, "Ruler", location_id=town.id)
    ctx = context(realm.session)
    raised = await honour_axis(ctx, ruler.id, ReputationAxis.MERCY, 40, town.id)
    await realm.session.flush()
    assert raised >= 1
    row = await realm.session.scalar(select(ReputationRow).where(ReputationRow.subject_node_id == ruler.id, ReputationRow.axis == ReputationAxis.MERCY))
    assert row is not None and row.value == 40
    assert await renown_share(realm.session, ruler.id, [town.id], ReputationAxis.MERCY) == 0.4
    assert "renown.gained" in set(await realm.session.scalars(select(IncidentRow.kind)))


async def test_justice_counts_double_against_the_powerful(realm: Realm) -> None:
    lord = await mortal(realm, "Lord")
    lord.importance = 80
    assert powerful(lord)
    lord.importance = None
    assert not powerful(lord)
