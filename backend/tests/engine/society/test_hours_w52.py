from aerona.db.tables.customs import TimeBudgetRow
from aerona.domain.enums.society import SocialClass
from aerona.engine.daily.life import strain_of
from tests.engine.society.factories import Realm, context


def budget(**shares: int) -> TimeBudgetRow:
    return TimeBudgetRow(people_entity_id=1, social_class=SocialClass.FARMER, **{"work": 50, "housework": 10, "sleep": 25, **shares})


async def test_short_sleep_and_heavy_housework_each_strain_a_being(realm: Realm) -> None:
    ctx = context(realm.session)
    assert strain_of(budget(), ctx, sleeps=True) == []
    keys = dict(strain_of(budget(housework=40, sleep=5), ctx, sleeps=True))
    assert set(keys) == {"daily_life.housework_stress_pct", "daily_life.short_sleep_stress_pct"}
    assert all(amount > 0 for amount in keys.values())


async def test_a_people_that_never_sleeps_feels_no_lack_of_it(realm: Realm) -> None:
    ctx = context(realm.session)
    assert strain_of(budget(sleep=0), ctx, sleeps=False) == []
    assert dict(strain_of(budget(sleep=0), ctx, sleeps=True))["daily_life.short_sleep_stress_pct"] > 0
