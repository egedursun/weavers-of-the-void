from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.biology import BiologyRow
from aerona.db.tables.customs import TimeBudgetRow
from aerona.db.tables.daily_life import CareCustomRow, DomesticServiceRow, HouseworkRow, LeisurePursuitRow, SpaceNormRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.households import HouseholdMemberRow, HouseholdRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.society import CommunityRelationRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.daily_life import (
    DistanceNorm,
    HouseDuty,
    LeisureKind,
    PostureForm,
    ServiceTerms,
    TouchNorm,
    WashFrequency,
    WashPlace,
    WasteHandling,
)
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.genetics import HouseholdRole
from aerona.domain.enums.mortal import LifeStage
from aerona.domain.enums.settlement import SizeTier
from aerona.domain.enums.society import SocialClass
from aerona.domain.models.entity_stats import PeopleStats
from aerona.engine.context import TickContext
from aerona.engine.customs.time_budgets import shares_for
from aerona.engine.daily.life import keep_daily_life
from aerona.engine.daily.seed import seed_daily
from tests.engine.core.factories import CoreWorld, bond, entity, mortal, settlement


async def kinds_of(session: AsyncSession, prefix: str) -> list[str]:
    return list(await session.scalars(select(IncidentRow.kind).where(IncidentRow.kind.startswith(prefix)).order_by(IncidentRow.id)))


async def folk_town(session: AsyncSession, world: CoreWorld) -> int:
    town = await settlement(session, "Ardun", world, world.regions[0])
    await bond(session, town.id, world.people.id, BondKind.DESCENDS_FROM)
    session.add(SettlementProfileRow(settlement_entity_id=town.id, size_tier=SizeTier.TOWN, sanitation=20, locked=[]))
    await session.flush()
    return town.id


async def folk_mortal(session: AsyncSession, world: CoreWorld, town_id: int, name: str, **profile: object) -> int:
    being = await mortal(session, name, world, town_id)
    being.social_class = SocialClass.FARMER
    await bond(session, being.id, world.people.id, BondKind.DESCENDS_FROM)
    session.add(MortalProfileRow(entity_id=being.id, locked=[], **profile))
    await session.flush()
    return being.id


async def test_long_work_strains_and_leisure_gladdens(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    town = await folk_town(session, world)
    worker = await folk_mortal(session, world, town, "Ama")
    session.add(TimeBudgetRow(people_entity_id=world.people.id, social_class=SocialClass.FARMER, life_stage=LifeStage.ADULT, work=75, leisure=25, locked=[]))
    await session.flush()
    await keep_daily_life(ctx)
    profile = await session.get(MortalProfileRow, worker)
    assert profile is not None and profile.stress > 0 and profile.mood_score > 0


async def test_care_customs_pull_sanitation_toward_what_the_people_keeps(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    town = await folk_town(session, world)
    session.add(
        CareCustomRow(
            people_entity_id=world.people.id,
            wash_frequency=WashFrequency.DAILY,
            wash_place=WashPlace.BATH_HOUSE,
            cleanliness=90,
            waste_handling=WasteHandling.SEWERS,
            locked=[],
        )
    )
    await session.flush()
    await keep_daily_life(ctx)
    profile = await session.get(SettlementProfileRow, town)
    assert profile is not None and profile.sanitation > 20


async def test_heavy_housework_takes_schooling_from_the_young_and_servants_lift_it(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    town = await folk_town(session, world)
    head = await folk_mortal(session, world, town, "Dun")
    child = await folk_mortal(session, world, town, "Kel", life_stage=LifeStage.CHILD, education=30)
    household = HouseholdRow(name="House of Dun", head_node_id=head, settlement_node_id=town, wealth=0, locked=[])
    session.add(household)
    await session.flush()
    session.add_all(
        [
            HouseholdMemberRow(member_node_id=head, household_id=household.id, role=HouseholdRole.HEAD),
            HouseholdMemberRow(member_node_id=child, household_id=household.id, role=HouseholdRole.DEPENDENT),
            *(
                HouseworkRow(household_id=household.id, duty=duty, doer_node_id=child, doer_role=HouseholdRole.DEPENDENT, load=20, locked=[])
                for duty in HouseDuty
            ),
        ]
    )
    await session.flush()
    await keep_daily_life(ctx)
    profile = await session.get(MortalProfileRow, child)
    assert profile is not None and profile.education < 30 and profile.stress > 0
    household.servants = 10
    profile.education = 30
    await session.flush()
    await keep_daily_life(ctx)
    assert profile.education == 30


async def test_an_unpaid_servant_leaves(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    town = await folk_town(session, world)
    head = await folk_mortal(session, world, town, "Iro")
    servant = await folk_mortal(session, world, town, "Pell")
    household = HouseholdRow(name="House of Iro", head_node_id=head, settlement_node_id=town, wealth=1, locked=[])
    session.add(household)
    await session.flush()
    session.add(DomesticServiceRow(servant_node_id=servant, household_id=household.id, terms=ServiceTerms.WAGE, wage=5, locked=[]))
    await session.flush()
    await keep_daily_life(ctx)
    assert await session.get(DomesticServiceRow, servant) is None
    assert "daily.servant_left" in await kinds_of(session, "daily.")


async def test_travel_for_pleasure_spends_coin_where_the_traveller_goes(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    town = await folk_town(session, world)
    traveller = await folk_mortal(session, world, town, "Sora", wealth=100)
    session.add(LeisurePursuitRow(holder_node_id=traveller, kind=LeisureKind.TOURISM, share=100, venue_node_id=town, locked=[]))
    await session.flush()
    await keep_daily_life(ctx)
    profile = await session.get(MortalProfileRow, traveller)
    assert profile is not None and profile.wealth < 100
    assert "daily.tourism_season" in await kinds_of(session, "daily.")


async def test_peoples_who_do_not_share_norms_of_space_lose_trust(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    other = await entity(session, "Velm Folk", EntityType.PEOPLE, PeopleStats(population=900), world_id=world.world.id)
    first, second = sorted((world.people.id, other.id))
    session.add_all(
        [
            SpaceNormRow(people_entity_id=first, distance=DistanceNorm.CLOSE, touch=TouchNorm.OPEN, posture=PostureForm.SIT_FLOOR, locked=[]),
            SpaceNormRow(people_entity_id=second, distance=DistanceNorm.WIDE, touch=TouchNorm.FORBIDDEN, posture=PostureForm.STAND, locked=[]),
            CommunityRelationRow(entity_a_id=first, entity_b_id=second, value=10),
        ]
    )
    await session.flush()
    await keep_daily_life(ctx)
    relation = await session.get(CommunityRelationRow, (first, second))
    assert relation is not None and relation.value < 10
    assert "daily.norms_clashed" in await kinds_of(session, "daily.") and "daily.norm_breach" not in await kinds_of(session, "daily.")


async def test_every_people_and_household_gets_its_daily_life_and_sleepless_beings_keep_no_sleep(
    session: AsyncSession, world: CoreWorld, ctx: TickContext
) -> None:
    town = await folk_town(session, world)
    head = await folk_mortal(session, world, town, "Bel")
    household = HouseholdRow(name="House of Bel", head_node_id=head, settlement_node_id=town, locked=[])
    session.add(household)
    await session.flush()
    session.add(HouseholdMemberRow(member_node_id=head, household_id=household.id, role=HouseholdRole.HEAD))
    session.add(TimeBudgetRow(people_entity_id=world.people.id, social_class=SocialClass.FARMER, life_stage=LifeStage.ADULT, locked=[]))
    await session.flush()
    await seed_daily(ctx)
    assert await session.get(CareCustomRow, world.people.id) is not None
    assert await session.get(SpaceNormRow, world.people.id) is not None
    assert await session.scalar(select(LeisurePursuitRow.id).where(LeisurePursuitRow.holder_node_id == world.people.id).limit(1)) is not None
    assert await session.scalar(select(HouseworkRow.id).where(HouseworkRow.household_id == household.id).limit(1)) is not None
    assert await session.get(TimeBudgetRow, (world.people.id, SocialClass.FARMER, LifeStage.CHILD)) is not None
    asleep = shares_for({}, ctx.rules)
    awake = shares_for({}, ctx.rules, sleeps=False)
    assert asleep["sleep"] > 0 and awake["sleep"] == 0 and sum(awake.values()) == sum(asleep.values()) == 100
    session.add(BiologyRow(holder_entity_id=world.people.id, sleeps=False, locked=[]))
    await session.flush()


async def test_a_household_weighed_down_by_its_housework_takes_on_help_when_it_can_pay(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    town = await folk_town(session, world)
    head = await folk_mortal(session, world, town, "Oren")
    household = HouseholdRow(name="House of Oren", head_node_id=head, settlement_node_id=town, wealth=ctx.rules.daily_life.burdened_hire_wealth, locked=[])
    session.add(household)
    await session.flush()
    session.add(HouseholdMemberRow(member_node_id=head, household_id=household.id, role=HouseholdRole.HEAD))
    session.add_all(
        HouseworkRow(household_id=household.id, duty=duty, doer_node_id=head, doer_role=HouseholdRole.HEAD, load=20, locked=[]) for duty in HouseDuty
    )
    await session.flush()
    await keep_daily_life(ctx)
    assert household.servants == 1
    assert "daily.help_taken" in await kinds_of(session, "daily.")


async def test_a_gone_doer_hands_the_duty_on_and_the_household_of_the_dead_tells_nothing(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    town = await folk_town(session, world)
    head = await folk_mortal(session, world, town, "Maren")
    gone = await folk_mortal(session, world, town, "Tobin")
    dead_head = await folk_mortal(session, world, town, "Ulla")
    living = HouseholdRow(name="House of Maren", head_node_id=head, settlement_node_id=town, locked=[])
    mourned = HouseholdRow(name="House of Ulla", head_node_id=dead_head, settlement_node_id=town, locked=[])
    session.add_all([living, mourned])
    await session.flush()
    session.add(HouseholdMemberRow(member_node_id=head, household_id=living.id, role=HouseholdRole.HEAD))
    session.add(HouseholdMemberRow(member_node_id=dead_head, household_id=mourned.id, role=HouseholdRole.HEAD))
    handed = HouseworkRow(household_id=living.id, duty=HouseDuty.FOOD, doer_node_id=gone, doer_role=HouseholdRole.DEPENDENT, load=20, locked=[])
    left = HouseworkRow(household_id=mourned.id, duty=HouseDuty.FOOD, doer_node_id=dead_head, doer_role=HouseholdRole.HEAD, load=20, locked=[])
    session.add_all([handed, left])
    ulla = await session.get(EntityRow, dead_head)
    assert ulla is not None
    ulla.status, ulla.end_epoch = EntityStatus.DEAD, ctx.epoch
    await session.flush()
    await keep_daily_life(ctx)
    assert handed.doer_node_id == head
    assert "daily.duty_breached" not in await kinds_of(session, "daily.")
