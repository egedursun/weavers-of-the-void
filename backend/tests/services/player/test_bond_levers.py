import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import ValidationFailedError
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionMembershipRow
from aerona.db.tables.relations import ContestRow, GroupRankRow, PassionRow, PersuasionRow, RelationshipRow, SocialCircleRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.relations import AppealKind, CircleKind, ContestEnd, ContestKind, GroupKind, PassionKind, RelationType
from aerona.services.player import bonds
from aerona.services.player.scope import PlayerScope
from tests.services.player.factories import PlayerWorld, make_entity


async def hero(session: AsyncSession, world: PlayerWorld, name: str) -> int:
    found = await make_entity(session, name, EntityType.MORTAL, world_id=world.world.id, location_id=world.region.id)
    return found.id


async def test_the_god_shapes_holds_and_forgets_a_bond(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    first, second = await hero(session, world, "Seren"), await hero(session, world, "Tegid")
    made = await bonds.set_relation(
        scope, bonds.SetTie(holder_id=first, subject_id=second, friendship=70, romance=40, kinds=[RelationType.FRIEND], mutual=True, hold=True)
    )
    row = await session.get(RelationshipRow, made.values["relation_id"])
    assert row is not None and row.friendship == 70 and row.kinds == ["friend"] and {"friendship", "romance", "kinds"} <= set(row.locked)
    back = await session.scalar(select(RelationshipRow).where(RelationshipRow.holder_node_id == second, RelationshipRow.subject_node_id == first))
    assert back is not None and back.friendship == 70
    await bonds.remove_relation(scope, bonds.TieTarget(relation_id=row.id))
    assert await session.get(RelationshipRow, row.id) is None
    with pytest.raises(ValidationFailedError):
        await bonds.set_relation(scope, bonds.SetTie(holder_id=first, subject_id=first, friendship=10))


async def test_the_god_gathers_reshapes_fills_and_breaks_up_a_circle(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    members = [await hero(session, world, name) for name in ("Ulla", "Vaun")]
    made = await bonds.found_circle(
        scope, bonds.FoundCircle(place_id=world.region.id, kind=CircleKind.STUDY_CIRCLE, axis=ValueAxis.KNOWLEDGE, member_ids=members)
    )
    circle_id = made.values["circle_id"]
    row = await session.get(SocialCircleRow, circle_id)
    assert row is not None and row.kind is CircleKind.STUDY_CIRCLE
    await bonds.edit_circle(scope, bonds.EditCircle(circle_id=circle_id, kind=CircleKind.POETS_CIRCLE))
    assert row.kind is CircleKind.POETS_CIRCLE and "kind" in row.locked
    newcomer = await hero(session, world, "Wyn")
    await bonds.circle_member(scope, bonds.CircleMember(circle_id=circle_id, mortal_id=newcomer))
    assert await session.get(FactionMembershipRow, (circle_id, newcomer)) is not None
    await bonds.circle_member(scope, bonds.CircleMember(circle_id=circle_id, mortal_id=newcomer, remove=True))
    assert await session.get(FactionMembershipRow, (circle_id, newcomer)) is None
    await bonds.disband_circle(scope, bonds.CircleTarget(circle_id=circle_id))
    faction = await session.get(EntityRow, circle_id)
    assert await session.get(SocialCircleRow, circle_id) is None and faction is not None and faction.status is not EntityStatus.CANON


async def test_the_god_kindles_calls_on_and_quenches_a_passion_and_sets_a_rank(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    holder, beloved = await hero(session, world, "Ynyr"), await hero(session, world, "Zara")
    made = await bonds.set_passion(scope, bonds.SetPassion(holder_id=holder, kind=PassionKind.LOVE, object_id=beloved, strength=100))
    passion = await session.get(PassionRow, made.values["passion_id"])
    assert passion is not None and passion.strength == 100 and "strength" in passion.locked
    called = await bonds.invoke_passion(scope, bonds.PassionTarget(passion_id=passion.id))
    assert called.values["lift"] > 100
    await bonds.remove_passion(scope, bonds.PassionTarget(passion_id=passion.id))
    assert await session.get(PassionRow, passion.id) is None
    await bonds.set_rank(scope, bonds.SetRank(group_id=world.region.id, member_id=holder, group_kind=GroupKind.HOUSEHOLD, rank=1, dominance=80))
    await bonds.set_rank(scope, bonds.SetRank(group_id=world.region.id, member_id=beloved, group_kind=GroupKind.HOUSEHOLD, rank=1))
    first = await session.get(GroupRankRow, (world.region.id, holder))
    assert first is not None and first.rank == 2 and first.dominance == 80
    await bonds.remove_rank(scope, bonds.RankTarget(group_id=world.region.id, member_id=holder))
    assert await session.get(GroupRankRow, (world.region.id, holder)) is None


async def test_the_god_stages_retells_and_strikes_contests_and_arguments(scope: PlayerScope, session: AsyncSession, world: PlayerWorld) -> None:
    first, second = await hero(session, world, "Afan"), await hero(session, world, "Bryn")
    made = await bonds.stage_contest(scope, bonds.HoldContest(challenger_id=first, defender_id=second, kind=ContestKind.INSULT_CONTEST))
    contest = await session.get(ContestRow, made.values["contest_id"])
    assert contest is not None and len(contest.rounds) > 0
    await bonds.edit_contest(scope, bonds.EditContest(contest_id=contest.id, outcome=ContestEnd.DRAWN, famous=True, note="sung in the halls"))
    assert contest.outcome is ContestEnd.DRAWN and contest.famous and contest.note == "sung in the halls"
    await bonds.remove_contest(scope, bonds.ContestTarget(contest_id=contest.id))
    assert await session.get(ContestRow, contest.id) is None
    argued = await bonds.attempt_persuasion(scope, bonds.Persuade(speaker_id=first, target_id=second, appeal=AppealKind.FEAR, axis=ValueAxis.TRUTH))
    record = await session.get(PersuasionRow, argued.values["persuasion_id"])
    assert record is not None and record.appeal is AppealKind.FEAR
    await bonds.remove_persuasion(scope, bonds.PersuasionTarget(persuasion_id=record.id))
    assert await session.get(PersuasionRow, record.id) is None
    with pytest.raises(ValidationFailedError):
        await bonds.attempt_persuasion(scope, bonds.Persuade(speaker_id=first, target_id=second, appeal=AppealKind.BELIEF))
