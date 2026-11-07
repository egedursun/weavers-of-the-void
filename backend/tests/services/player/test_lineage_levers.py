import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.genetics import AllelePoolRow, GenomeRow, HouseResemblanceRow
from aerona.db.tables.households import DwellingFurnishingRow, HouseholdAggregateRow, HouseholdMemberRow, HouseholdRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.genetics import DwellingKind, GiftStance, HouseholdRole, Locus
from aerona.domain.enums.society import SocialClass
from aerona.domain.models.entity_stats import HouseStats, ItemStats
from aerona.services.player import genetics, households
from aerona.services.player.scope import PlayerScope
from tests.services.player.factories import PlayerWorld, make_entity


async def test_the_god_writes_shapes_and_strikes_a_mortal_s_blood(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    town = await make_entity(session, "Varnhold", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    hero = await make_entity(session, "Ysolde", EntityType.MORTAL, world_id=world.world.id, location_id=town.id)
    await genetics.found(scope, genetics.GenomeTarget(mortal_id=hero.id))
    row = await session.get(GenomeRow, hero.id)
    assert row is not None and Locus.HAIR_COLOUR.value in row.genes
    await genetics.set_gene(scope, genetics.SetGene(mortal_id=hero.id, locus=Locus.HAIR_COLOUR, first="copper", second="copper"))
    assert row.genes[Locus.HAIR_COLOUR.value] == ["copper", "copper"] and "genes" in row.locked
    with pytest.raises(ValidationFailedError):
        await genetics.set_gene(scope, genetics.SetGene(mortal_id=hero.id, locus=Locus.HAIR_COLOUR, first="violet", second="copper"))
    await genetics.edit(scope, genetics.EditGenome(mortal_id=hero.id, beauty=90, inbreeding=10))
    assert row.beauty == 90 and row.inbreeding == 10 and {"beauty", "inbreeding"} <= set(row.locked)
    await genetics.redraw(scope, genetics.GenomeTarget(mortal_id=hero.id))
    await genetics.remove(scope, genetics.GenomeTarget(mortal_id=hero.id))
    assert await session.get(GenomeRow, hero.id) is None
    with pytest.raises(NotFoundError):
        await genetics.remove(scope, genetics.GenomeTarget(mortal_id=hero.id))


async def test_the_god_sets_a_people_s_pool_and_how_it_reads_the_gift(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    folk = await make_entity(session, "Vale Folk", EntityType.PEOPLE, world_id=world.world.id, location_id=world.region.id)
    await genetics.found_pool(scope, genetics.PoolTarget(people_id=folk.id))
    await genetics.set_frequency(scope, genetics.SetFrequency(people_id=folk.id, locus=Locus.GIFT_STORM, allele="gifted", frequency=40))
    row = await session.get(AllelePoolRow, folk.id)
    assert row is not None and row.frequencies[Locus.GIFT_STORM.value]["gifted"] == 40
    assert abs(sum(row.frequencies[Locus.GIFT_STORM.value].values()) - 100) <= 1
    await genetics.set_stance(scope, genetics.SetGiftStance(people_id=folk.id, stance=GiftStance.PERSECUTED))
    await genetics.edit_share(scope, genetics.EditGiftShare(people_id=folk.id, gifted_share=12, cohort="noble", cohort_share=30))
    assert row.gift_stance is GiftStance.PERSECUTED and row.gifted_share == 12 and row.cohort_shares["noble"] == 30
    await genetics.remove_pool(scope, genetics.PoolTarget(people_id=folk.id))
    assert await session.get(AllelePoolRow, folk.id) is None


async def test_the_god_marks_a_house_by_a_look(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    house = await make_entity(session, "House Varn", EntityType.HOUSE, world_id=world.world.id, stats=HouseStats())
    await genetics.set_resemblance(scope, genetics.SetResemblance(house_id=house.id, locus=Locus.HAIR_COLOUR, allele="copper", share=80))
    row = await session.get(HouseResemblanceRow, house.id)
    assert row is not None and row.allele == "copper" and row.share == 80
    with pytest.raises(ValidationFailedError):
        await genetics.set_resemblance(scope, genetics.SetResemblance(house_id=house.id, locus=Locus.MADNESS, allele="touched"))
    await genetics.remove_resemblance(scope, genetics.ResemblanceTarget(house_id=house.id))
    assert await session.get(HouseResemblanceRow, house.id) is None


async def test_the_god_founds_shapes_furnishes_and_dissolves_a_household(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    town = await make_entity(session, "Lanternford", EntityType.SETTLEMENT, world_id=world.world.id, location_id=world.region.id)
    head = await make_entity(session, "Ilsa", EntityType.MORTAL, world_id=world.world.id, location_id=town.id)
    kin = await make_entity(session, "Oren", EntityType.MORTAL, world_id=world.world.id, location_id=town.id)
    lamp = await make_entity(
        session, "Ledger Lamp", EntityType.ITEM, world_id=world.world.id, location_id=town.id, stats=ItemStats(damage=0, protection=0, might=5, curse=0)
    )
    made = await households.found(scope, households.FoundHousehold(head_id=head.id))
    home = await session.get(HouseholdRow, made.values["household_id"])
    assert home is not None
    other = await session.get(HouseholdRow, (await households.found(scope, households.FoundHousehold(head_id=kin.id))).values["household_id"])
    assert other is not None
    await households.set_member(scope, households.SetMember(household_id=home.id, mortal_id=kin.id, role=HouseholdRole.CARER, cares_for_id=head.id))
    member = await session.get(HouseholdMemberRow, kin.id)
    assert member is not None and member.household_id == home.id and member.locked
    await households.edit(scope, households.EditHousehold(household_id=home.id, wealth=120, burden=30, social_class=SocialClass.MERCHANT))
    assert home.wealth == 120 and home.burden == 30 and {"wealth", "burden"} <= set(home.locked)
    await households.set_debt(scope, households.SetDebt(household_id=home.id, lender_household_id=other.id, amount=50))
    assert home.debts == {str(other.id): 50}
    await households.hold(scope, households.HoldHousehold(household_id=home.id, fields=["decisions"]))
    assert "decisions" in home.locked
    await households.set_dwelling(scope, households.SetDwelling(household_id=home.id, kind=DwellingKind.MANOR, quality=80, rooms=9))
    await households.furnish(scope, households.Furnish(household_id=home.id, item_id=lamp.id))
    assert await session.get(DwellingFurnishingRow, lamp.id) is not None
    await households.unfurnish(scope, households.FurnishingTarget(item_id=lamp.id))
    await households.remove_dwelling(scope, households.HouseholdTarget(household_id=home.id))
    await households.release(scope, households.MemberTarget(mortal_id=kin.id))
    assert await session.get(HouseholdMemberRow, kin.id) is None
    await households.remove(scope, households.HouseholdTarget(household_id=home.id))
    assert await session.get(HouseholdRow, home.id) is None
    await households.edit_aggregate(scope, households.EditAggregate(community_id=town.id, social_class=SocialClass.FARMER, households=40, quality=35))
    aggregate = await session.get(HouseholdAggregateRow, (town.id, SocialClass.FARMER))
    assert aggregate is not None and aggregate.households == 40
    await households.remove_aggregate(scope, households.AggregateTarget(community_id=town.id, social_class=SocialClass.FARMER))
    assert await session.get(HouseholdAggregateRow, (town.id, SocialClass.FARMER)) is None
