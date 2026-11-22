from dataclasses import replace

from sqlalchemy import select

from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.daily_life import DomesticServiceRow
from aerona.db.tables.demography import CohortRow
from aerona.db.tables.households import DwellingFurnishingRow, DwellingRow, HouseholdAggregateRow, HouseholdMemberRow, HouseholdRow
from aerona.db.tables.mind import CultureEthicRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.society_depth import ClassStandingRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.demography import AgeBand, CohortCondition, Sex
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.genetics import HouseholdDecision, HouseholdRole
from aerona.domain.enums.mind import ActKind, EthicalStance, NeedKind
from aerona.domain.enums.mortal import LifeStage
from aerona.domain.enums.society import SocialClass
from aerona.domain.models.entity_stats import ItemStats
from aerona.engine.demography.basket import fed_index
from aerona.engine.households.dwelling_kinds import built_in_dwelling
from aerona.engine.households.formation import found_household, house_everyone
from aerona.engine.households.homes import home_of, sickness_factor
from aerona.engine.households.life import (
    HouseholdTally,
    furnish,
    lend_at_interest,
    match,
    members_of,
    pay_debts,
    renovate,
    servants,
    tend_aggregates,
    tend_household,
)
from aerona.engine.mind.needs import home_needs
from aerona.engine.mortal.kinship import add_parent
from aerona.engine.polity.laws import LawBook
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, context, link, make, mortal, people, settlement

RULES = Rules()


async def profile(realm: Realm, mortal_id: int, stage: LifeStage, wealth: int = 0) -> MortalProfileRow:
    row = await realm.session.get(MortalProfileRow, mortal_id)
    if row is None:
        row = MortalProfileRow(entity_id=mortal_id, life_stage=stage, wealth=wealth)
        realm.session.add(row)
    row.life_stage, row.wealth = stage, wealth
    await realm.session.flush()
    return row


async def test_every_mortal_is_housed_and_children_join_their_parents(realm: Realm) -> None:
    ctx = context(realm.session)
    town = await settlement(realm, "Lanternford")
    parent = await mortal(realm, "Ama", location_id=town.id)
    child = await mortal(realm, "Bo", location_id=town.id, age=4)
    await profile(realm, parent.id, LifeStage.ADULT, wealth=40)
    await profile(realm, child.id, LifeStage.CHILD)
    await add_parent(realm.session, parent.id, child.id, 1)
    await realm.session.flush()
    assert await house_everyone(ctx) == 2
    head = await realm.session.get(HouseholdMemberRow, parent.id)
    kid = await realm.session.get(HouseholdMemberRow, child.id)
    assert head is not None and kid is not None and head.household_id == kid.household_id
    assert head.role is HouseholdRole.HEAD and kid.role is HouseholdRole.DEPENDENT
    household = await realm.session.get(HouseholdRow, head.household_id)
    assert household is not None and household.wealth == 40
    dwelling = await realm.session.scalar(select(DwellingRow).where(DwellingRow.household_id == household.id))
    assert dwelling is not None and dwelling.quality > 0
    assert await house_everyone(ctx) == 0


async def test_a_household_keeps_its_purse_bears_its_weak_and_improves_its_home(realm: Realm) -> None:
    ctx = context(realm.session)
    town = await settlement(realm, "Millbrook")
    head = await mortal(realm, "Cass", location_id=town.id)
    elder = await mortal(realm, "Dov", location_id=town.id, age=70)
    await profile(realm, head.id, LifeStage.ADULT, wealth=20)
    await profile(realm, elder.id, LifeStage.ELDER)
    home = await found_household(ctx, head)
    realm.session.add(HouseholdMemberRow(member_node_id=elder.id, household_id=home.id, role=HouseholdRole.DEPENDENT, joined_epoch=1))
    await realm.session.flush()
    await tend_household(ctx, home, await LawBook.load(realm.session), HouseholdTally())
    assert home.income > 0 and home.expenses > 0
    assert home.burden > 0
    home.wealth = 500
    dwelling = await realm.session.scalar(select(DwellingRow).where(DwellingRow.household_id == home.id))
    assert dwelling is not None
    before = dwelling.quality
    assert await renovate(ctx, home, dwelling, HouseholdTally())
    assert dwelling.quality == min(100, before + RULES.households.renovate_gain) and home.last_decision is HouseholdDecision.RENOVATE


async def test_a_destitute_household_gives_up_an_infant_only_where_its_people_allow_it(realm: Realm) -> None:
    folk = await people(realm, "Hardwater Folk")
    town = await settlement(realm, "Hardwater")
    await link(realm.session, town.id, folk.id, BondKind.DESCENDS_FROM)
    head = await mortal(realm, "Esk", location_id=town.id)
    baby = await mortal(realm, "Fay", location_id=town.id, age=0)
    await profile(realm, head.id, LifeStage.ADULT)
    await profile(realm, baby.id, LifeStage.INFANT)
    home = await found_household(context(realm.session), head)
    realm.session.add(HouseholdMemberRow(member_node_id=baby.id, household_id=home.id, role=HouseholdRole.DEPENDENT, joined_epoch=1))
    realm.session.add(CultureEthicRow(holder_entity_id=folk.id, act=ActKind.INFANTICIDE, stance=EthicalStance.UNTHINKABLE, since_epoch=1, locked=[]))
    await realm.session.flush()
    tuned = replace(RULES, households=replace(RULES.households, infanticide_pct=100, abandon_pct=0, migrate_pct=0))
    for epoch in range(3, 6):
        await tend_household(context(realm.session, tuned, epoch=epoch), home, await LawBook.load(realm.session), HouseholdTally())
    assert baby.status is EntityStatus.CANON


async def test_usury_debts_are_paid_down_with_interest(realm: Realm) -> None:
    ctx = context(realm.session)
    town = await settlement(realm, "Coinmere")
    rich = await found_household(ctx, await mortal(realm, "Gil", location_id=town.id))
    poor = await found_household(ctx, await mortal(realm, "Hob", location_id=town.id))
    rich.wealth, poor.wealth = 0, 1000
    poor.debts = {str(rich.id): 100}
    await pay_debts(ctx, poor)
    assert poor.debts == {} and rich.wealth == 100 + 100 * RULES.households.usury_interest_pct // 100


async def test_home_quality_feeds_needs_and_squalor_breeds_sickness(realm: Realm) -> None:
    ctx = context(realm.session)
    town = await settlement(realm, "Rookery")
    head = await mortal(realm, "Ivo", location_id=town.id)
    home = await found_household(ctx, head)
    dwelling = await realm.session.scalar(select(DwellingRow).where(DwellingRow.household_id == home.id))
    assert dwelling is not None
    dwelling.quality, dwelling.rooms, dwelling.dwelling_kind_id = 95, 6, (await built_in_dwelling(realm.session, "manor")).id
    needs = {NeedKind.COMFORT: 10, NeedKind.BEAUTY: 10, NeedKind.STATUS: 10, NeedKind.REST: 50}
    await home_needs(realm.session, RULES, head, needs)
    assert needs[NeedKind.COMFORT] > 10 and needs[NeedKind.REST] > 50
    healthy = await sickness_factor(realm.session, RULES, head.id)
    dwelling.quality = 5
    assert await sickness_factor(realm.session, RULES, head.id) > healthy
    household, found, quality, members = await home_of(realm.session, RULES, head.id)
    assert household is not None and found is not None and quality == 5 and members == 1
    assert len(await members_of(ctx, home)) == 1


async def test_cohorts_become_anonymous_households_and_hunger_reads_what_was_eaten(realm: Realm) -> None:
    ctx = context(realm.session)
    town = await settlement(realm, "Grainholm")
    realm.session.add(
        CohortRow(
            community_entity_id=town.id, age_band=AgeBand.ADULT, sex=Sex.FEMALE, social_class=SocialClass.FARMER, condition=CohortCondition.NONE, count=500
        )
    )
    await realm.session.flush()
    await tend_aggregates(ctx, HouseholdTally())
    row = await realm.session.get(HouseholdAggregateRow, (town.id, SocialClass.FARMER))
    assert row is not None and row.households == 500 // RULES.households.mean_size
    realm.session.add(ClassStandingRow(community_entity_id=town.id, social_class=SocialClass.FARMER, fed_pct=90))
    await realm.session.flush()
    assert (await fed_index(realm.session, town.id) or 0) >= 85


async def test_household_money_never_moves_through_a_locked_purse(realm: Realm) -> None:
    ctx = context(realm.session)
    town = await settlement(realm, "Quillmere")
    groom = await mortal(realm, "Ezra", location_id=town.id)
    elder = await mortal(realm, "Fen", location_id=town.id)
    bride = await mortal(realm, "Gale", location_id=town.id)
    for one in (groom, elder, bride):
        await profile(realm, one.id, LifeStage.ADULT, wealth=10)
    seeker = await found_household(ctx, groom)
    giver = await found_household(ctx, elder)
    realm.session.add(HouseholdMemberRow(member_node_id=bride.id, household_id=giver.id, role=HouseholdRole.DEPENDENT, joined_epoch=1))
    giver.social_class = seeker.social_class
    seeker.wealth, giver.wealth = 100, 200
    giver.locked = ["wealth"]
    await realm.session.flush()
    assert await match(ctx, seeker, await members_of(ctx, seeker), HouseholdTally())
    assert (seeker.wealth, giver.wealth) == (100, 200)

    seeker.locked = ["wealth"]
    giver.locked = []
    seeker.debts = {str(giver.id): 50}
    await pay_debts(ctx, seeker)
    assert (seeker.wealth, giver.wealth) == (100, 200)
    giver.wealth = 10_000
    assert not await lend_at_interest(ctx, giver, elder, HouseholdTally())
    assert not await renovate(ctx, seeker, await realm.session.scalar(select(DwellingRow).where(DwellingRow.household_id == seeker.id)), HouseholdTally())
    assert (seeker.wealth, giver.wealth) == (100, 10_000)


async def test_two_who_each_head_a_household_alone_can_be_matched_and_share_one_home(realm: Realm) -> None:
    ctx = context(realm.session)
    town = await settlement(realm, "Lindmere")
    first = await mortal(realm, "Ivo", location_id=town.id)
    second = await mortal(realm, "Juna", location_id=town.id)
    for one in (first, second):
        await profile(realm, one.id, LifeStage.ADULT, wealth=10)
    seeker = await found_household(ctx, first)
    alone = await found_household(ctx, second)
    alone.social_class = seeker.social_class
    seeker.wealth = 100
    await realm.session.flush()
    assert await match(ctx, seeker, await members_of(ctx, seeker), HouseholdTally())
    moved = await realm.session.get(HouseholdMemberRow, second.id)
    assert moved is not None and moved.household_id == seeker.id and moved.role is HouseholdRole.SPOUSE
    await tend_household(ctx, alone, await LawBook.load(realm.session), HouseholdTally())
    await realm.session.flush()
    assert await realm.session.get(HouseholdRow, alone.id) is None


async def test_a_household_matches_its_single_with_the_candidate_nearest_in_age(realm: Realm) -> None:
    ctx = context(realm.session)
    town = await settlement(realm, "Ashby")
    seeker_mortal = await mortal(realm, "Kel", location_id=town.id, age=24)
    elder = await mortal(realm, "Lorn", location_id=town.id, age=66)
    youth = await mortal(realm, "Mira", location_id=town.id, age=26)
    for one in (seeker_mortal, elder, youth):
        await profile(realm, one.id, LifeStage.ADULT, wealth=10)
    seeker = await found_household(ctx, seeker_mortal)
    for one in (elder, youth):
        other = await found_household(ctx, one)
        other.social_class = seeker.social_class
    seeker.wealth = 100
    await realm.session.flush()
    assert await match(ctx, seeker, await members_of(ctx, seeker), HouseholdTally())
    joined = await realm.session.get(HouseholdMemberRow, youth.id)
    left = await realm.session.get(HouseholdMemberRow, elder.id)
    assert joined is not None and joined.household_id == seeker.id
    assert left is not None and left.household_id != seeker.id


async def test_a_wealthy_household_takes_a_poorer_neighbour_into_service_and_lets_them_go_when_it_cannot_pay(realm: Realm) -> None:
    ctx = context(realm.session)
    town = await settlement(realm, "Servewick")
    master = await mortal(realm, "Ona", location_id=town.id)
    poor_head = await mortal(realm, "Pell", location_id=town.id)
    worker = await mortal(realm, "Quin", location_id=town.id)
    for one in (master, poor_head, worker):
        await profile(realm, one.id, LifeStage.ADULT, wealth=10)
    rich = await found_household(ctx, master)
    poor = await found_household(ctx, poor_head)
    realm.session.add(HouseholdMemberRow(member_node_id=worker.id, household_id=poor.id, role=HouseholdRole.DEPENDENT, joined_epoch=1))
    rich.wealth, poor.wealth = 10_000, 5
    await realm.session.flush()
    assert await servants(ctx, rich, None, HouseholdTally())
    service = await realm.session.get(DomesticServiceRow, worker.id)
    member = await realm.session.get(HouseholdMemberRow, worker.id)
    assert service is not None and service.household_id == rich.id and service.wage == ctx.rules.daily_life.servant_wage
    assert member is not None and member.household_id == rich.id and member.role is HouseholdRole.SERVANT
    rich.income, rich.expenses = 0, 100
    assert await servants(ctx, rich, None, HouseholdTally())
    assert await realm.session.get(DomesticServiceRow, worker.id) is None


async def test_a_household_sets_the_belongings_of_its_members_in_its_home_but_not_their_arms(realm: Realm) -> None:
    ctx = context(realm.session)
    town = await settlement(realm, "Hearthby")
    owner = await mortal(realm, "Rue", location_id=town.id)
    await profile(realm, owner.id, LifeStage.ADULT, wealth=10)
    home = await found_household(ctx, owner)
    dwelling = await realm.session.scalar(select(DwellingRow).where(DwellingRow.household_id == home.id))
    assert dwelling is not None
    chest = await make(realm.session, "Oak Chest", EntityType.ITEM, ItemStats(damage=0, protection=0, might=0, curse=0), world_id=realm.world.id)
    blade = await make(realm.session, "Long Blade", EntityType.ITEM, ItemStats(damage=40, protection=0, might=0, curse=0), world_id=realm.world.id)
    for thing in (chest, blade):
        await BondRepository(realm.session).connect(BondDraft(owner.id, thing.id, BondKind.OWNS, 0))
    tally = HouseholdTally()
    await furnish(ctx, home, await members_of(ctx, home), dwelling, tally)
    placed = {row.item_node_id: row.dwelling_id for row in await realm.session.scalars(select(DwellingFurnishingRow))}
    assert placed == {chest.id: dwelling.id} and tally.furnished == 1
    await furnish(ctx, home, await members_of(ctx, home), dwelling, tally)
    assert tally.furnished == 1
