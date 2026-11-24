from sqlalchemy import select

import aerona.domain.enums.customs as customs_enums
from aerona.catalog.revivals import REVIVAL_GOALS, REVIVAL_WAYS
from aerona.db.tables.customs import RevivalRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.domain.enums.customs import RevivalGoal, RevivalStage, RevivalWay
from aerona.engine.customs.revival import GOAL_WORK, goal_for, pursue, way_for
from tests.engine.society.factories import Realm, context, people, tuned


def test_the_old_adopt_goal_is_gone_and_every_way_has_goals() -> None:
    assert not hasattr(RevivalGoal, "ADOPT_WAYS")
    assert not hasattr(customs_enums, "RevivalAim")
    assert len(REVIVAL_WAYS) == len(RevivalWay) == 6
    assert len(REVIVAL_GOALS) == len(RevivalGoal) == 6
    assert set(GOAL_WORK) == set(RevivalGoal)
    assert all(spec.goals and spec.goals <= set(RevivalGoal) for spec in REVIVAL_WAYS.values())


async def test_a_people_takes_the_only_way_its_rules_leave_and_a_goal_that_way_seeks(realm: Realm) -> None:
    only_wait = tuned(revival={"restore_weight": 0, "synthesis_weight": 0, "adopt_weight": 0, "await_weight": 100, "withdraw_weight": 0})
    ctx = context(realm.session, only_wait)
    way = way_for(ctx, {}, "test.way")
    assert way is RevivalWay.AWAIT
    assert goal_for(ctx, way, "test.goal") in REVIVAL_WAYS[RevivalWay.AWAIT].goals


async def test_a_revival_for_rule_with_no_ruler_over_it_meets_its_goal(realm: Realm) -> None:
    folk = await people(realm, "The Tellers")
    row = RevivalRow(
        people_entity_id=folk.id,
        way=RevivalWay.RESTORE,
        goal=RevivalGoal.RESTORE_RULE,
        stage=RevivalStage.REVITALISATION,
        strength=50,
        started_epoch=1,
        locked=[],
    )
    realm.session.add(row)
    await realm.session.flush()
    assert await pursue(context(realm.session), row, folk)
    await realm.session.flush()
    assert row.stage is RevivalStage.NEW_STEADY and row.ended_epoch == 3
    assert "revival.goal_met" in set(await realm.session.scalars(select(IncidentRow.kind)))
