from sqlalchemy import select

from aerona.db.tables.statecraft import CrisisBackerRow, CrisisRow, PolityRegardRow
from aerona.domain.enums.polity import RegionalStanding
from aerona.domain.enums.statecraft import CrisisDemand, CrisisSide, CrisisState
from aerona.engine.polity.crises import CrisisTally, ripe_crises, trust_of
from tests.engine.society.factories import Realm, context, tuned
from tests.engine.statecraft.test_statecraft import polity
from tests.engine.warfare.factories import society


async def test_neighbours_take_sides_and_a_balanced_crisis_escalates_toward_war(realm: Realm) -> None:
    ctx = context(realm.session, tuned(statecraft={"back_down_ratio_pct": 0, "crisis_steps": 3}))
    demander, _ = await polity(realm, "Wolf Throne")
    target, _ = await polity(realm, "Bear Throne")
    friend, _ = await polity(realm, "Owl Throne")
    great, _ = await polity(realm, "Sun Crown", standing=RegionalStanding.GREAT_POWER)
    aloof, _ = await polity(realm, "Far Throne")
    assert await trust_of(ctx, friend.id, target.id) == 50
    realm.session.add(PolityRegardRow(holder_entity_id=friend.id, subject_entity_id=target.id, trust=100))
    crisis = CrisisRow(demander_entity_id=demander.id, target_entity_id=target.id, demand=CrisisDemand.PAY, amount=10, opened_epoch=1, locked=[])
    realm.session.add(crisis)
    await realm.session.flush()
    assert await trust_of(ctx, friend.id, target.id) == 100
    tally = CrisisTally()
    assert await ripe_crises(ctx, tally) == []
    assert crisis.escalation == 1 and tally.escalated == 1
    backers = {row.backer_entity_id: row for row in await realm.session.scalars(select(CrisisBackerRow).where(CrisisBackerRow.crisis_id == crisis.id))}
    assert backers[friend.id].side is CrisisSide.TARGET
    assert backers[great.id].side is CrisisSide.DEMANDER and backers[great.id].swing
    assert aloof.id not in backers
    assert await ripe_crises(ctx, tally) == []
    verdicts = await ripe_crises(ctx, tally)
    assert [verdict.state for verdict in verdicts] == [CrisisState.WAR]


async def test_a_lopsided_crisis_ends_in_a_concession_or_a_climb_down(realm: Realm) -> None:
    ctx = context(realm.session, tuned(statecraft={"back_down_ratio_pct": 100}))
    demander, strong = await polity(realm, "Wolf Throne")
    target, _ = await polity(realm, "Bear Throne")
    await society(realm.session, strong.id, warrior=40.0)
    crisis = CrisisRow(demander_entity_id=demander.id, target_entity_id=target.id, demand=CrisisDemand.PAY, amount=10, opened_epoch=1, locked=[])
    realm.session.add(crisis)
    await realm.session.flush()
    verdicts = await ripe_crises(ctx, CrisisTally())
    assert len(verdicts) == 1 and verdicts[0].state is CrisisState.CONCEDED
    crisis.locked = ["state"]
    assert await ripe_crises(ctx, CrisisTally()) == []
