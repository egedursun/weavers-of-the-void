from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionMembershipRow
from aerona.db.tables.governance import OrgGovernanceRow
from aerona.db.tables.kin import KinGroupMemberRow, KinGroupRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.gathering import GatheringKind
from aerona.domain.enums.governance import HeadSelection
from aerona.domain.enums.kin import KinGroupForm
from aerona.domain.enums.mortal import LifeStage
from aerona.engine.context import TickContext
from aerona.engine.gatherings.occasions import deaths
from aerona.engine.governance.heads import candidates
from aerona.engine.kin.groups import GroupTally, choose_head
from aerona.engine.phases.exploration import explores
from aerona.engine.phases.heroes import load_hero_world
from aerona.engine.primitives.maturity import of_age, under_age
from aerona.engine.sacred.bureau import petitioner_in
from tests.engine.core.factories import CoreWorld, bond, mortal, settlement

GIFTED = {"intellect": 95, "agility": 95, "strength": 95, "charisma": 95}


async def town_of(session: AsyncSession, world: CoreWorld) -> EntityRow:
    if "town" not in world.extra:
        world.extra["town"] = await settlement(session, "Ardun", world, world.regions[0])
    return world.extra["town"]


async def person(session: AsyncSession, world: CoreWorld, name: str, stage: LifeStage, renown: int = 0) -> EntityRow:
    being = await mortal(session, name, world, (await town_of(session, world)).id, age=5 if stage is LifeStage.CHILD else 30, **GIFTED)
    session.add(MortalProfileRow(entity_id=being.id, life_stage=stage, renown=renown, locked=[]))
    await session.flush()
    return being


async def test_only_infants_and_children_are_under_age(session: AsyncSession, world: CoreWorld) -> None:
    child = await person(session, world, "Kel", LifeStage.CHILD)
    youth = await person(session, world, "Avo", LifeStage.YOUTH)
    elder = await person(session, world, "Orin", LifeStage.ELDER)
    assert await under_age(session, [child.id, youth.id, elder.id, None]) == {child.id}
    assert [await of_age(session, node) for node in (child.id, youth.id, world.people.id, None)] == [False, True, True, False]


async def test_a_child_member_never_heads_an_org_unless_the_head_is_inherited(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    town = await town_of(session, world)
    child = await person(session, world, "Kel", LifeStage.CHILD)
    grown = await person(session, world, "Ama", LifeStage.ADULT)
    session.add_all(FactionMembershipRow(faction_entity_id=town.id, mortal_entity_id=member.id, locked=[]) for member in (child, grown))
    elected = OrgGovernanceRow(org_node_id=town.id, head_selection=HeadSelection.ELECTED_BY_MEMBERS, locked=[])
    session.add(elected)
    await session.flush()
    assert [entity.id for entity in await candidates(ctx, elected)] == [grown.id]
    elected.head_selection = HeadSelection.INHERITED
    assert sorted(entity.id for entity in await candidates(ctx, elected)) == sorted([child.id, grown.id])


async def test_a_kin_group_never_takes_a_child_for_its_head(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    child = await person(session, world, "Kel", LifeStage.CHILD, renown=90)
    grown = await person(session, world, "Ama", LifeStage.ADULT, renown=10)
    group = KinGroupRow(people_entity_id=world.people.id, name="Kin of the Ford", form=KinGroupForm.CLAN, head_node_id=child.id, locked=[])
    session.add(group)
    await session.flush()
    members = [KinGroupMemberRow(group_id=group.id, member_node_id=member.id, locked=[]) for member in (child, grown)]
    session.add_all(members)
    await session.flush()
    await choose_head(ctx, group, members, GroupTally())
    assert group.head_node_id == grown.id


async def test_a_wake_is_hosted_by_grown_kin_and_the_children_mourn_as_guests(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    dead = await person(session, world, "Riv", LifeStage.ADULT)
    child = await person(session, world, "Kel", LifeStage.CHILD)
    spouse = await person(session, world, "Ama", LifeStage.ADULT)
    await bond(session, dead.id, child.id, BondKind.PARENT_OF)
    await bond(session, dead.id, spouse.id, BondKind.SPOUSE_OF)
    dead.status = EntityStatus.DEAD
    dead.end_epoch = ctx.epoch
    await session.flush()
    wakes = [occasion for occasion in await deaths(ctx) if occasion.honoured_id == dead.id]
    assert [(occasion.kind in {GatheringKind.WAKE, GatheringKind.FUNERAL}, occasion.host_id) for occasion in wakes] == [(True, spouse.id)]
    assert [guest.node_id for guest in wakes[0].guests] == [child.id]


async def test_a_gifted_child_neither_explores_nor_counts_as_a_hero(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    child = await person(session, world, "Kel", LifeStage.CHILD)
    grown = await person(session, world, "Ama", LifeStage.ADULT)
    assert [await explores(ctx, child), await explores(ctx, grown)] == [False, True]
    heroes = {hero.id for hero in (await load_hero_world(ctx)).heroes}
    assert child.id not in heroes and grown.id in heroes


async def test_a_child_never_files_a_petition_for_the_town(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    town = await town_of(session, world)
    child = await person(session, world, "Kel", LifeStage.CHILD)
    assert await petitioner_in(ctx, town) == town.id
    grown = await person(session, world, "Ama", LifeStage.ADULT)
    assert await petitioner_in(ctx, town) == grown.id
    assert child.id in set(await session.scalars(select(MortalProfileRow.entity_id)))
