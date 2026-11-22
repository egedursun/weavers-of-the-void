from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.kin_dynamics import ElderSwayRow, KinBlendRow, KinDisowningRow, KinFavourRow, KinRivalryRow
from aerona.db.tables.lifecycle import DesignatedHeirRow
from aerona.db.tables.polity import HouseMemberRow, HouseProfileRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.demography import InheritanceCustom, MartialStyle
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.kin_dynamics import DisownReason, RivalryCause
from aerona.domain.models.entity_stats import HouseStats
from aerona.engine.context import TickContext
from aerona.engine.kin_dynamics.acts import disown, reconcile, rival
from aerona.engine.kin_dynamics.book import KinTally, dynamic_of
from aerona.engine.kin_dynamics.tend import heat_rivalries, tend_kin, weigh_tension
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.records import heir_of
from tests.engine.core.factories import CoreWorld, bond, entity, mortal, settlement, tuned_rules

Family = tuple[EntityRow, EntityRow, list[EntityRow]]


async def family(session: AsyncSession, world: CoreWorld, custom: InheritanceCustom = InheritanceCustom.ELECTIVE) -> Family:
    town = await settlement(session, "Kinhold", world, world.regions[0], population=3000)
    await bond(session, town.id, world.people.id, BondKind.DESCENDS_FROM)
    session.add(
        PeopleCultureRow(
            people_entity_id=world.people.id, cohesion=50, literacy=10, urbanisation=10, martial_style=next(iter(MartialStyle)), inheritance=custom, locked=[]
        )
    )
    head = await mortal(session, "Orlan Vey", world, town.id, age=60)
    children = [await mortal(session, name, world, town.id, age=30) for name in ("Ise Vey", "Tam Vey", "Rho Vey")]
    house = await entity(session, "House Vey", EntityType.HOUSE, HouseStats(), world_id=world.world.id)
    session.add(HouseProfileRow(house_entity_id=house.id, founder_entity_id=head.id, head_entity_id=head.id, locked=[]))
    for member in (head, *children):
        session.add(HouseMemberRow(house_entity_id=house.id, mortal_entity_id=member.id))
    for child in children:
        await bond(session, head.id, child.id, BondKind.PARENT_OF)
    await session.flush()
    return house, head, children


async def test_a_head_favours_a_child_whom_siblings_resent_and_whom_a_ruler_names_heir(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "favour", tuned_rules(kin_dynamics={"favour_chance_pct": 100, "rivalry_from_favour_pct": 100}))
    _house, head, children = await family(session, world)
    await bond(session, head.id, world.regions[0].id, BondKind.RULES)
    tally = await tend_kin(ctx)
    favour = await session.scalar(select(KinFavourRow).where(KinFavourRow.parent_node_id == head.id))
    assert favour is not None and favour.child_node_id in {child.id for child in children} and tally.favoured >= 1
    assert tally.rivalries == 2
    named = await session.get(DesignatedHeirRow, head.id)
    assert named is not None and named.heir_entity_id == favour.child_node_id and tally.designated == 1
    heir = await heir_of(session, head, favour_reach=ctx.rules.kin_dynamics.favour_inheritance_pct)
    assert heir is not None and heir.id == favour.child_node_id


async def test_a_hot_rivalry_between_siblings_splits_the_house_and_one_with_a_parent_ends_in_disowning(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "split", tuned_rules(kin_dynamics={"split_threshold": 30, "line_chance_pct": 0}))
    house, head, children = await family(session, world)
    dynamic = await dynamic_of(ctx, house=house.id)
    tally = KinTally()
    siblings = await rival(ctx, dynamic, children[0].id, children[1].id, RivalryCause.INHERITANCE, tally=tally)
    against = await rival(ctx, dynamic, head.id, children[2].id, RivalryCause.LOVE, tally=tally)
    siblings.heat = against.heat = 25
    await heat_rivalries(ctx, dynamic, tally)
    assert tally.splits == 1 and siblings.ended_epoch == ctx.epoch
    assert await session.get(HouseMemberRow, (house.id, children[1].id)) is None
    cast = await session.scalar(select(KinDisowningRow).where(KinDisowningRow.disowned_node_id == children[2].id))
    assert cast is not None and cast.reason is DisownReason.RIVALRY and tally.disowned == 1
    assert await session.get(HouseMemberRow, (house.id, children[2].id)) is None


async def test_the_disowned_lose_the_inheritance_until_they_are_taken_back(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    house, head, children = await family(session, world, InheritanceCustom.PRIMOGENITURE)
    dynamic = await dynamic_of(ctx, house=house.id)
    tally = KinTally()
    await disown(ctx, dynamic, head.id, children[0], DisownReason.DISOBEDIENCE, tally=tally)
    criminal = await disown(ctx, dynamic, head.id, children[1], DisownReason.CRIME, tally=tally)
    heir = await heir_of(session, head)
    assert heir is not None and heir.id == children[2].id
    assert not criminal.reversible and not await reconcile(ctx, criminal, tally)
    cast = await session.scalar(select(KinDisowningRow).where(KinDisowningRow.disowned_node_id == children[0].id))
    assert cast is not None and await reconcile(ctx, cast, tally)
    assert await session.get(HouseMemberRow, (house.id, children[0].id)) is not None and tally.reconciled == 1


async def test_step_kin_join_through_a_later_marriage_and_an_elder_holds_sway_until_overthrown(session: AsyncSession, world: CoreWorld) -> None:
    rules = tuned_rules(kin_dynamics={"overthrow_chance_pct": 100, "sway_decay": 40, "favour_chance_pct": 0})
    ctx = await manual_context(session, "blend", rules)
    house, head, children = await family(session, world)
    spouse = await mortal(session, "Mera Ash", world, children[0].location_id or world.regions[0].id, age=50)
    stepchild = await mortal(session, "Pell Ash", world, children[0].location_id or world.regions[0].id, age=20)
    await bond(session, head.id, spouse.id, BondKind.SPOUSE_OF)
    await bond(session, spouse.id, stepchild.id, BondKind.PARENT_OF)
    session.add(HouseMemberRow(house_entity_id=house.id, mortal_entity_id=stepchild.id, by_marriage=True))
    elder = await mortal(session, "Old Vey", world, children[0].location_id or world.regions[0].id, age=85)
    await bond(session, elder.id, head.id, BondKind.PARENT_OF)
    await session.flush()
    tally = await tend_kin(ctx)
    blended = await session.scalar(select(KinBlendRow).where(KinBlendRow.member_node_id == stepchild.id))
    assert blended is not None and blended.joined_by_node_id == spouse.id and tally.blends == 1
    sway = await session.scalar(select(ElderSwayRow).where(ElderSwayRow.elder_node_id == elder.id))
    assert sway is not None and tally.elders == 1 and tally.steered == 1
    await tend_kin(ctx)
    assert sway.ended_epoch == ctx.epoch
    assert await session.scalar(select(KinRivalryRow.id).where(KinRivalryRow.cause == RivalryCause.LOVE)) is None


async def test_a_familys_tension_is_its_hottest_rivalry_and_its_unmended_disownings(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "tension", tuned_rules(kin_dynamics={"disowning_tension": 15, "split_threshold": 100}))
    house, head, children = await family(session, world)
    dynamic = await dynamic_of(ctx, house=house.id)
    tally = KinTally()
    hot = await rival(ctx, dynamic, children[0].id, children[1].id, RivalryCause.INHERITANCE, tally=tally)
    hot.heat = 40
    await disown(ctx, dynamic, head.id, children[2], DisownReason.CRIME, tally=tally)
    await weigh_tension(ctx, dynamic)
    assert dynamic.tension == 55
    hot.ended_epoch = ctx.epoch
    await weigh_tension(ctx, dynamic)
    assert dynamic.tension == 15
