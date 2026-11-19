from dataclasses import replace

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.cycles import KinshipSystemRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.households import HouseholdMemberRow, HouseholdRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.kin import KinGroupMemberRow, KinGroupRow, KinRoleDutyRow
from aerona.db.tables.mind import PersonalityValueRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.titles import TitleHolderRow, TitleProfileRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.cycles import DescentGroup, KinshipDescent
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.genetics import HouseholdRole
from aerona.domain.enums.kin import KinDuty, KinGroupForm, KinRole
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.mortal import LifeStage
from aerona.domain.enums.titles import TitleTenure, TitleTier
from aerona.domain.models.entity_stats import TitleStats
from aerona.engine.context import TickContext
from aerona.engine.kin.duties import KinTally, keep_duties
from aerona.engine.kin.groups import GroupTally, keep_groups, kin_group_bars, split_group
from aerona.engine.kin.roles import kin_by_role
from aerona.engine.kin.seed import seed_kin
from aerona.engine.polity.held_titles import title_prestige
from aerona.engine.primitives.records import heir_of
from tests.engine.core.factories import CoreWorld, bond, entity, mortal, settlement, tuned_rules


async def home_town(session: AsyncSession, world: CoreWorld) -> int:
    if "town" not in world.extra:
        world.extra["town"] = await settlement(session, "Ardun", world, world.regions[0])
        await bond(session, world.extra["town"].id, world.people.id, BondKind.DESCENDS_FROM)
    return world.extra["town"].id


async def kinsman(session: AsyncSession, world: CoreWorld, name: str, **profile: object) -> int:
    being = await mortal(session, name, world, await home_town(session, world))
    session.add(MortalProfileRow(entity_id=being.id, locked=[], **profile))
    await session.flush()
    return being.id


async def duty(session: AsyncSession, world: CoreWorld, role: KinRole, kind: KinDuty, strength: int = 90) -> None:
    session.add(KinRoleDutyRow(people_entity_id=world.people.id, role=role, duty=kind, strength=strength, locked=[]))
    await session.flush()


async def kinds_of(session: AsyncSession) -> list[str]:
    return list(await session.scalars(select(IncidentRow.kind).where(IncidentRow.kind.startswith("kin.")).order_by(IncidentRow.id)))


async def test_kin_bound_by_support_help_their_kin_in_need(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    parent = await kinsman(session, world, "Ama", wealth=80)
    child = await kinsman(session, world, "Kel", wealth=2)
    await bond(session, parent, child, BondKind.PARENT_OF)
    await duty(session, world, KinRole.PARENT, KinDuty.SUPPORT)
    await keep_duties(ctx, KinTally())
    needy = await session.get(MortalProfileRow, child)
    assert needy is not None and needy.wealth > 2
    assert "kin.duty_kept" in await kinds_of(session)


async def test_a_kinsman_who_will_not_help_is_shamed(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    parent = await kinsman(session, world, "Dun", wealth=80, honour=50)
    child = await kinsman(session, world, "Iro", wealth=2)
    await bond(session, parent, child, BondKind.PARENT_OF)
    session.add_all(
        [PersonalityValueRow(node_id=parent, axis=ValueAxis.FAMILY, value=-100), PersonalityValueRow(node_id=parent, axis=ValueAxis.MERCY, value=-100)]
    )
    await duty(session, world, KinRole.PARENT, KinDuty.SUPPORT, strength=40)
    await keep_duties(ctx, KinTally())
    refuser = await session.get(MortalProfileRow, parent)
    assert refuser is not None and refuser.honour < 50
    assert "kin.duty_breached" in await kinds_of(session)


async def test_an_orphan_goes_to_the_grandparent_whose_duty_is_to_raise(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    grandparent = await kinsman(session, world, "Bel")
    parent = await kinsman(session, world, "Sora")
    child = await kinsman(session, world, "Pell", life_stage=LifeStage.CHILD)
    await bond(session, grandparent, parent, BondKind.PARENT_OF)
    await bond(session, parent, child, BondKind.PARENT_OF)
    dead = await session.get(type(world.people), parent)
    assert dead is not None
    dead.status, dead.end_epoch = EntityStatus.DEAD, ctx.epoch
    home = HouseholdRow(name="House of Bel", head_node_id=grandparent, locked=[])
    session.add(home)
    await session.flush()
    session.add(HouseholdMemberRow(member_node_id=grandparent, household_id=home.id, role=HouseholdRole.HEAD))
    await duty(session, world, KinRole.GRANDPARENT, KinDuty.RAISE)
    await duty(session, world, KinRole.CHILD, KinDuty.MOURN)
    assert await kin_by_role(session, child, KinRole.GRANDPARENT) == [grandparent]
    await keep_duties(ctx, KinTally())
    placed = await session.get(HouseholdMemberRow, child)
    assert placed is not None and placed.household_id == home.id and placed.role is HouseholdRole.WARD


async def test_members_of_an_exogamous_group_may_not_wed_and_groups_choose_heads_and_split(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    first = await kinsman(session, world, "Vael", renown=30)
    second = await kinsman(session, world, "Orin", renown=10)
    group = KinGroupRow(people_entity_id=world.people.id, name="Kin of the Ford", form=KinGroupForm.CLAN, exogamy=90, locked=[])
    session.add(group)
    await session.flush()
    session.add_all([KinGroupMemberRow(group_id=group.id, member_node_id=member, locked=[]) for member in (first, second)])
    await session.flush()
    one, two = await session.get(type(world.people), first), await session.get(type(world.people), second)
    assert one is not None and two is not None and await kin_group_bars(session, ctx.rules, one, two)
    tally = GroupTally()
    await keep_groups(ctx, tally)
    assert group.head_node_id == first and tally.heads == 1
    for name in ("Third", "Fourth"):
        session.add(KinGroupMemberRow(group_id=group.id, member_node_id=await kinsman(session, world, name), locked=[]))
    await session.flush()
    await keep_groups(replace(ctx, environment=replace(ctx.environment, rules=tuned_rules(kin={"split_size": 1}))), tally)
    assert await session.scalar(select(func.count()).select_from(KinGroupRow)) == 2 and "kin.group_split" in await kinds_of(session)


async def test_duties_and_descent_groups_are_seeded_from_the_kinship_system(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    session.add(KinshipSystemRow(people_entity_id=world.people.id, descent=KinshipDescent.THROUGH_FIRST_LINE, descent_group=DescentGroup.CLAN, locked=[]))
    member = await kinsman(session, world, "Lir")
    await session.flush()
    await seed_kin(ctx)
    raise_line = await session.get(KinRoleDutyRow, (world.people.id, KinRole.PARENT_SIBLING_FIRST_LINE, KinDuty.RAISE))
    assert raise_line is not None and raise_line.strength > 0
    clan = await session.scalar(select(KinGroupRow).where(KinGroupRow.people_entity_id == world.people.id, KinGroupRow.form == KinGroupForm.CLAN))
    assert clan is not None and clan.exogamy == ctx.rules.kin.group_exogamy_strength
    assert await session.get(KinGroupMemberRow, (clan.id, member)) is not None
    assert "kin.group_founded" in await kinds_of(session)


async def test_one_who_leaves_no_descendants_leaves_the_estate_to_a_member_of_the_kin_group(session: AsyncSession, world: CoreWorld) -> None:
    dead_id, cousin_id = await kinsman(session, world, "Aster"), await kinsman(session, world, "Brannoc")
    group = KinGroupRow(people_entity_id=world.people.id, name="Kin of the Hill", form=KinGroupForm.CLAN, locked=[])
    session.add(group)
    await session.flush()
    session.add_all([KinGroupMemberRow(group_id=group.id, member_node_id=member, locked=[]) for member in (dead_id, cousin_id)])
    await session.flush()
    dead = await session.get(EntityRow, dead_id)
    assert dead is not None
    heir = await heir_of(session, dead)
    assert heir is not None and heir.id == cousin_id


async def test_a_kin_group_whose_head_holds_titles_holds_together_longer(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    head = await kinsman(session, world, "Corran")
    second = await kinsman(session, world, "Dela")
    third = await kinsman(session, world, "Evrin")
    title = await entity(session, "Seat of the Hill", EntityType.TITLE, TitleStats(), world_id=world.world.id)
    session.add(TitleProfileRow(title_entity_id=title.id, rank=TitleTier.REGIONAL, prestige=60, regalia=[], drift={}, locked=[]))
    session.add(TitleHolderRow(title_entity_id=title.id, holder_node_id=head, tenure=TitleTenure.FOUNDED, since_epoch=0))
    group = KinGroupRow(people_entity_id=world.people.id, name="Kin of the Seat", form=KinGroupForm.LINEAGE, head_node_id=head, locked=[])
    session.add(group)
    await session.flush()
    session.add_all(KinGroupMemberRow(group_id=group.id, member_node_id=member, locked=[]) for member in (head, second, third))
    await session.flush()
    prestige = await title_prestige(session, [head])
    assert prestige == {head: 60}
    small = replace(ctx, environment=replace(ctx.environment, rules=tuned_rules(kin={"split_size": 2})))
    members = list(await session.scalars(select(KinGroupMemberRow).where(KinGroupMemberRow.group_id == group.id).order_by(KinGroupMemberRow.member_node_id)))
    tally = GroupTally()
    await split_group(small, group, members, prestige[head], tally)
    assert tally.splits == 0
    await split_group(small, group, members, 0, tally)
    assert tally.splits == 1
