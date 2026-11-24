from aerona.db.tables.customs import TIME_FIELDS, TimeBudgetRow
from aerona.db.tables.households import HouseholdMemberRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.domain.enums.daily_life import HouseDuty, LeisureKind
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.society import SocialClass
from aerona.engine.customs.time_budgets import shares_for
from aerona.engine.daily.w52_ways import WaysTally, give_time, tend_sick
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, context, mortal

RULES = Rules()


def test_eleven_duties_sixteen_pursuits_twelve_shares() -> None:
    assert len(HouseDuty) == 13 and len(LeisureKind) == 19 and len(TIME_FIELDS) == 15
    assert {"civic", "training"} <= set(TIME_FIELDS)


def test_a_lawful_martial_people_gives_time_to_civic_duty_and_training_and_the_year_stays_whole() -> None:
    shares = shares_for({ValueAxis.LAW: 80, ValueAxis.MARTIAL: 80}, RULES)
    assert shares["civic"] > 0 and shares["training"] > 0
    assert sum(shares.values()) == 100


def test_giving_time_takes_it_from_work_and_keeps_the_year_whole() -> None:
    row = TimeBudgetRow(
        people_entity_id=1,
        social_class=SocialClass.WARRIOR,
        work=55,
        rest=20,
        worship=10,
        leisure=10,
        travel=3,
        service=2,
        learning=0,
        care=0,
        art=0,
        housework=0,
        sleep=0,
        civic=0,
        training=0,
        locked=[],
    )
    assert give_time(row, "training", 10)
    assert row.training == 10 and sum(getattr(row, name) for name in TIME_FIELDS) == 100
    row.locked = ["civic"]
    assert not give_time(row, "civic", 5)


async def test_care_of_the_sick_mends_them(realm: Realm) -> None:
    sick = await mortal(realm, "Sick")
    profile = MortalProfileRow(entity_id=sick.id, health=20, locked=[])
    realm.session.add(profile)
    await realm.session.flush()
    tally = WaysTally()
    await tend_sick(context(realm.session), [HouseholdMemberRow(household_id=1, member_node_id=sick.id)], tally)
    assert profile.health > 20 and tally.tended == 1
