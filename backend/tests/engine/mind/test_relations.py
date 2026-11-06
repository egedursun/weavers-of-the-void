from dataclasses import replace

from sqlalchemy import select

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionMembershipRow
from aerona.db.tables.mind import GriefRow, MemoryRow, SkillRow, ThoughtRow
from aerona.db.tables.relations import ContestRow, GroupRankRow, PassionRow, PersuasionRow, RelationshipRow, SocialCircleRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.mind import MemoryKind, PreferenceKind, SkillKind, SkillSource, ThoughtKind, ValueAxis, ValueHolder
from aerona.domain.enums.mortal import LifeStage
from aerona.domain.enums.relations import AppealKind, ContestKind, ContestStake, GroupKind, PassionKind, PassionSource, PersuasionAim, RelationType
from aerona.engine.mind.book import ensure_mind_row, stored_values, write_values
from aerona.engine.mind.opinion import opinion
from aerona.engine.mind.preferences import write_pref
from aerona.engine.mortal.kinship import marry
from aerona.engine.mortal.profile import ensure_profile
from aerona.engine.relations.affairs import AffairTally, flag_lovers, tend_affairs
from aerona.engine.relations.book import ensure_relation, refresh_kinds, relation
from aerona.engine.relations.circles import CircleTally, tend_circles
from aerona.engine.relations.contests import Bout, ContestTally, hold_contest, judge_taste
from aerona.engine.relations.interactions import SocialTally, socialise
from aerona.engine.relations.passions import PassionTally, bereaved, invoke, kindle, tend_passions
from aerona.engine.relations.pecking import PeckingTally, challenge, tend_pecking
from aerona.engine.relations.persuasion import persuade
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, active_bonds, context, mortal, settlement

RULES = Rules()


def tuned(**namespaces: dict[str, int]) -> Rules:
    rules = RULES
    for name, changes in namespaces.items():
        rules = replace(rules, **{name: replace(getattr(rules, name), **changes)})
    return rules


async def grown(realm: Realm, name: str, place: EntityRow) -> EntityRow:
    found = await mortal(realm, name, location_id=place.id)
    profile, _ = await ensure_profile(realm.session, found.id, 3)
    profile.life_stage = LifeStage.ADULT
    await ensure_mind_row(realm.session, found, 3)
    return found


async def kinds_of(realm: Realm, holder: int, subject: int) -> set[str]:
    row = await relation(realm.session, holder, subject)
    return set(row.kinds) if row is not None else set()


async def test_mortals_who_share_a_place_meet_and_come_to_know_each_other(realm: Realm) -> None:
    ctx = context(realm.session, tuned(social={"interactions_per_epoch": 12}))
    town = await settlement(realm, "Fairhold")
    first, second = await grown(realm, "Aled", town), await grown(realm, "Beca", town)
    tally = SocialTally()
    scene = await socialise(ctx, town.id, [first, second], tally)
    assert scene is not None and tally.interactions == 12 and tally.pairs == 1
    row = await relation(realm.session, first.id, second.id)
    assert row is not None and row.familiarity > 0
    await refresh_kinds(realm.session, ctx.rules, first.id, ctx.epoch)
    assert await kinds_of(realm, first.id, second.id)


async def test_bonds_take_types_with_hysteresis_and_lovers_are_bound(realm: Realm) -> None:
    ctx = context(realm.session)
    town = await settlement(realm, "Marrow")
    first, second = await grown(realm, "Cai", town), await grown(realm, "Dilys", town)
    there = await ensure_relation(realm.session, first.id, second.id, ctx.epoch)
    back = await ensure_relation(realm.session, second.id, first.id, ctx.epoch)
    assert there is not None and back is not None
    there.friendship, there.familiarity, there.romance = 85, 90, 70
    back.romance = 70
    await refresh_kinds(realm.session, ctx.rules, first.id, ctx.epoch)
    kinds = await kinds_of(realm, first.id, second.id)
    assert {"friend", "close_friend", "best_friend", "confidant", "lover"} <= kinds
    assert await active_bonds(realm.session, first.id, BondKind.LOVES)
    there.friendship = RULES.social.friend_at - RULES.social.hysteresis + 1
    await refresh_kinds(realm.session, ctx.rules, first.id, ctx.epoch)
    assert "friend" in await kinds_of(realm, first.id, second.id)
    there.friendship, there.romance = 0, 0
    await refresh_kinds(realm.session, ctx.rules, first.id, ctx.epoch)
    kinds = await kinds_of(realm, first.id, second.id)
    assert "friend" not in kinds and "ex_lover" in kinds
    back.friendship = 60
    view = await opinion(realm.session, RULES, ctx.epoch, second.id, first.id)
    assert any(term.key == "friendship" and term.value > 0 for term in view.terms)


async def test_an_affair_is_found_out_by_a_spouse_who_shares_the_place(realm: Realm) -> None:
    ctx = context(realm.session, tuned(social={"affair_discovery_pct": 100, "affair_divorce_pct": 0, "affair_feud_pct": 0}))
    town = await settlement(realm, "Cwm")
    cheat, lover, spouse = await grown(realm, "Elis", town), await grown(realm, "Ffion", town), await grown(realm, "Gwil", town)
    await marry(realm.session, cheat, spouse, ctx.epoch)
    row = await ensure_relation(realm.session, cheat.id, lover.id, ctx.epoch)
    assert row is not None
    row.kinds = [RelationType.LOVER.value]
    assert await flag_lovers(ctx, row)
    tally = AffairTally()
    await tend_affairs(ctx, tally)
    assert tally.discovered == 1 and row.affair_known
    jealous = await realm.session.scalar(select(ThoughtRow).where(ThoughtRow.holder_node_id == spouse.id, ThoughtRow.kind == ThoughtKind.JEALOUS))
    assert jealous is not None
    memory = await realm.session.scalar(select(MemoryRow).where(MemoryRow.holder_node_id == spouse.id, MemoryRow.kind == MemoryKind.BETRAYED_ME))
    assert memory is not None


async def test_shared_tastes_gather_a_circle_that_bonds_its_members_and_ranks_them(realm: Realm) -> None:
    rules = tuned(circles={"min_members": 3}, pecking={"min_members": 3})
    ctx = context(realm.session, rules)
    town = await settlement(realm, "Llan")
    folk = [await grown(realm, name, town) for name in ("Hywel", "Iolo", "Jac")]
    for person in folk:
        await write_pref(realm.session, person.id, PreferenceKind.DRINK, "mead", 90)
    tally = CircleTally()
    await tend_circles(ctx, town, folk, tally)
    circle = await realm.session.scalar(select(SocialCircleRow))
    assert tally.founded == 1 and circle is not None
    members = set(
        await realm.session.scalars(select(FactionMembershipRow.mortal_entity_id).where(FactionMembershipRow.faction_entity_id == circle.faction_entity_id))
    )
    assert members == {person.id for person in folk}
    await tend_circles(ctx, town, folk, tally)
    bond = await relation(realm.session, folk[0].id, folk[1].id)
    assert bond is not None and bond.friendship > 0
    await tend_pecking(ctx, PeckingTally())
    ranks = list(await realm.session.scalars(select(GroupRankRow).where(GroupRankRow.group_node_id == circle.faction_entity_id)))
    assert sorted(row.rank for row in ranks) == [1, 2, 3]


async def test_passions_grow_from_love_lift_when_called_on_and_bring_grief_at_a_death(realm: Realm) -> None:
    ctx = context(realm.session, tuned(passions={"relation_at": 60}))
    town = await settlement(realm, "Nant")
    holder, beloved = await grown(realm, "Kai", town), await grown(realm, "Lowri", town)
    row = await ensure_relation(realm.session, holder.id, beloved.id, ctx.epoch)
    assert row is not None
    row.kinds, row.romance = [RelationType.LOVER.value], 90
    await tend_passions(ctx, holder, PassionTally())
    love = await realm.session.scalar(select(PassionRow).where(PassionRow.holder_node_id == holder.id, PassionRow.kind == PassionKind.LOVE))
    assert love is not None and love.strength == 90
    love.strength = 100
    assert await invoke(ctx, holder, [beloved.id]) > 1
    assert await bereaved(ctx, beloved, None) == 1
    grief = await realm.session.scalar(select(GriefRow).where(GriefRow.mourner_node_id == holder.id))
    assert grief is not None and grief.strength == RULES.passions.grief_strength


async def test_a_skilled_speaker_sways_a_belief_and_the_argument_is_recorded(realm: Realm) -> None:
    ctx = context(realm.session, tuned(persuasion={"threshold": 0, "jitter": 0}))
    town = await settlement(realm, "Ogmore")
    speaker, listener = await grown(realm, "Mabli", town), await grown(realm, "Nia", town)
    await write_values(realm.session, ValueHolder.PERSONAL, listener.id, {ValueAxis.KNOWLEDGE: 10})
    argument = await persuade(ctx, speaker.id, listener.id, AppealKind.BELIEF, PersuasionAim.BELIEF, axis=ValueAxis.KNOWLEDGE, toward=100)
    assert argument.success and argument.record_id is not None
    assert (await stored_values(realm.session, ValueHolder.PERSONAL, listener.id))[ValueAxis.KNOWLEDGE] > 10
    assert await realm.session.get(PersuasionRow, argument.record_id) is not None


async def test_a_contest_for_a_hand_moves_the_heart_of_the_one_contested(realm: Realm) -> None:
    ctx = context(realm.session, tuned(contests={"jitter": 0}))
    town = await settlement(realm, "Pen")
    sage, fool, wooed = await grown(realm, "Owain", town), await grown(realm, "Pryd", town), await grown(realm, "Rhian", town)
    realm.session.add(SkillRow(holder_node_id=sage.id, skill=SkillKind.LORE, level=90, peak=90, last_used_epoch=1, source=SkillSource.PLAYER))
    await realm.session.flush()
    bout = Bout(ContestKind.RIDDLE_GAME, ContestStake.BRIDE, sage, fool, judge_id=wooed.id, stake_node_id=wooed.id, place_id=town.id)
    row = await hold_contest(ctx, bout, ContestTally())
    assert row is not None and row.outcome.value == "challenger" and len(row.rounds) == RULES.contests.rounds
    heart = await relation(realm.session, wooed.id, sage.id)
    assert heart is not None and heart.romance >= RULES.contests.bride_romance
    assert await realm.session.scalar(select(ContestRow.id)) is not None
    await kindle(realm.session, fool.id, PassionKind.HATRED, sage.id, strength=90, source=PassionSource.DIVINE, epoch=ctx.epoch)
    assert await realm.session.scalar(select(PassionRow).where(PassionRow.holder_node_id == fool.id)) is not None
    assert await realm.session.scalar(select(RelationshipRow).where(RelationshipRow.holder_node_id == fool.id, RelationshipRow.subject_node_id == sage.id))


async def test_a_judge_who_loves_the_art_form_weighs_merit_and_a_challenge_is_fought_out(realm: Realm) -> None:
    ctx = context(realm.session, tuned(contests={"jitter": 0}, pecking={"challenge_margin": 0, "challenge_pct": 100}))
    town = await settlement(realm, "Rhos")
    poet, rival, judge = await grown(realm, "Siân", town), await grown(realm, "Tudur", town), await grown(realm, "Urien", town)
    bout = Bout(ContestKind.FLYTING, ContestStake.HONOUR, poet, rival, judge_id=judge.id, place_id=town.id)
    assert await judge_taste(ctx, bout) == 0
    await write_pref(realm.session, judge.id, PreferenceKind.ART_FORM, "epic_poem", 80)
    assert await judge_taste(ctx, bout) == 80
    upper = GroupRankRow(group_node_id=town.id, member_node_id=rival.id, group_kind=GroupKind.CIRCLE, rank=1, dominance=10, since_epoch=1, locked=[])
    lower = GroupRankRow(group_node_id=town.id, member_node_id=poet.id, group_kind=GroupKind.CIRCLE, rank=2, dominance=90, since_epoch=1, locked=[])
    realm.session.add_all([upper, lower])
    await realm.session.flush()
    tally = PeckingTally()
    await challenge(ctx, upper, lower, tally)
    met = await relation(realm.session, rival.id, poet.id)
    assert tally.challenges == 1 and met is not None and met.familiarity > 0
