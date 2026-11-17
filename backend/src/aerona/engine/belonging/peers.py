from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations

from sqlalchemy import func, select

from aerona.db.tables.belonging import PeerGroupRow, PeerMemberRow
from aerona.db.tables.demography import CohortRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import NotableYearRow
from aerona.db.tables.kinds import KindHoldingRow
from aerona.db.tables.military import ArmyProfileRow
from aerona.db.tables.mind import FACET_MAX, FACET_MIN, FacetRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.belonging import PlayKind
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.demography import AgeBand
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.environment import NotableYearKind
from aerona.domain.enums.kinds import KindConcept
from aerona.domain.enums.mind import Facet, SkillKind
from aerona.domain.enums.mortal import LifeStage
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.society import SocialClass
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.mind.skills import practise
from aerona.engine.polity.laws import law_param
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import active_bonds, connect
from aerona.engine.relations.book import ensure_relation

YOUNG = frozenset({LifeStage.CHILD, LifeStage.YOUTH})
PLAY_SKILLS = {
    PlayKind.GAMES: SkillKind.TACTICS,
    PlayKind.MOCK_FIGHTS: SkillKind.UNARMED,
    PlayKind.IMITATION: SkillKind.ETIQUETTE,
    PlayKind.RIDING: SkillKind.RIDING,
    PlayKind.ARCHERY: SkillKind.BOW,
    PlayKind.SONGS: SkillKind.LORE,
}
PLAY_FACETS = {
    PlayKind.GAMES: Facet.COOPERATION,
    PlayKind.MOCK_FIGHTS: Facet.ASSERTIVENESS,
    PlayKind.IMITATION: Facet.COOPERATION,
    PlayKind.RIDING: Facet.ASSERTIVENESS,
    PlayKind.ARCHERY: Facet.ASSERTIVENESS,
    PlayKind.SONGS: Facet.COOPERATION,
}
CLASS_PLAY = {
    SocialClass.NOBLE: PlayKind.RIDING,
    SocialClass.WARRIOR: PlayKind.ARCHERY,
    SocialClass.PRIEST: PlayKind.SONGS,
    SocialClass.SCRIBE: PlayKind.SONGS,
    SocialClass.MONASTIC: PlayKind.SONGS,
}


LABOURING = frozenset({SocialClass.FARMER, SocialClass.SERF_OR_SLAVE, SocialClass.WORKER, SocialClass.UNEMPLOYED, SocialClass.OUTCAST, SocialClass.ARTISAN})


@dataclass
class PeerTally:
    groups: int = 0
    members: int = 0
    friendships: int = 0
    rivalries: int = 0
    deprived: int = 0
    grown: int = 0


async def play_of(ctx: TickContext, town: EntityRow, social_class: SocialClass) -> PlayKind:
    folk = await people_of(ctx.session, town)
    if folk is not None and await ctx.session.scalar(
        select(KindHoldingRow.id).where(KindHoldingRow.concept == KindConcept.GAME, KindHoldingRow.holder_node_id == folk.id).limit(1)
    ):
        return PlayKind.GAMES
    if social_class in CLASS_PLAY:
        return CLASS_PLAY[social_class]
    return PlayKind.MOCK_FIGHTS if ctx.rng(seed_of("play", town.id, social_class.value)).chance(50) else PlayKind.IMITATION


async def shift_facet(ctx: TickContext, node_id: int, facet: Facet, amount: int) -> None:
    row = await ctx.session.get(FacetRow, (node_id, facet))
    if row is None:
        ctx.session.add(FacetRow(node_id=node_id, facet=facet, value=clamp_int(amount, FACET_MIN, FACET_MAX)))
    else:
        row.value = clamp_int(row.value + amount, FACET_MIN, FACET_MAX)


async def put_to_work(ctx: TickContext, town_id: int, social_class: SocialClass) -> bool:
    return social_class in LABOURING and await law_param(ctx.session, town_id, LawKind.LABOUR_LAW, "child_labour") is True


async def troubled_lands(ctx: TickContext) -> set[int]:
    hungry = set(
        await ctx.session.scalars(
            select(NotableYearRow.region_entity_id).where(NotableYearRow.kind == NotableYearKind.HUNGER, NotableYearRow.epoch >= ctx.epoch - 1)
        )
    )
    armies = set(await ctx.session.scalars(select(ArmyProfileRow.region_entity_id).where(ArmyProfileRow.target_entity_id.is_not(None))))
    return {item for item in hungry | armies if item is not None}


async def befriend(ctx: TickContext, group: PeerGroupRow, members: list[int], tally: PeerTally) -> None:
    table = ctx.rules.peer_groups
    for first, second in combinations(sorted(members), 2):
        roll = ctx.rng(seed_of("peers", group.id, first, second, ctx.epoch))
        friend, rival = roll.chance(table.friend_chance), roll.chance(table.rival_chance)
        if not friend and not rival:
            continue
        for holder, subject in ((first, second), (second, first)):
            row = await ensure_relation(ctx.session, holder, subject, ctx.epoch)
            if row is None:
                continue
            if friend and "friendship" not in row.locked:
                row.friendship = max(row.friendship, table.friendship)
            if rival and not friend and "rivalry" not in row.locked:
                row.rivalry = max(row.rivalry, table.rivalry)
            row.last_epoch = ctx.epoch
        tally.friendships += int(friend)
        tally.rivalries += int(rival and not friend)


async def grow_up(ctx: TickContext, group: PeerGroupRow, member: PeerMemberRow, grown: list[int], tally: PeerTally) -> None:
    profile = await ctx.session.get(MortalProfileRow, member.mortal_entity_id)
    if profile is not None and member.deprived_epochs and "stress" not in profile.locked:
        profile.stress = clamp_int(profile.stress + member.deprived_epochs * ctx.rules.peer_groups.deprived_stress, 0, 100)
    for other in grown:
        await connect(ctx.session, member.mortal_entity_id, other, BondKind.COMPANION, ctx.epoch, description="companions since childhood")
    await ctx.session.delete(member)
    tally.grown += 1


async def enrol(ctx: TickContext, group: PeerGroupRow, children: list[int]) -> list[PeerMemberRow]:
    members = list(await ctx.session.scalars(select(PeerMemberRow).where(PeerMemberRow.group_id == group.id).order_by(PeerMemberRow.mortal_entity_id)))
    known = {row.mortal_entity_id for row in members}
    for child in children:
        if child not in known and not held(child):
            row = PeerMemberRow(group_id=group.id, mortal_entity_id=child, joined_epoch=ctx.epoch, locked=[])
            ctx.session.add(row)
            members.append(row)
    return members


async def keep_group(ctx: TickContext, group: PeerGroupRow, children: list[int], troubled: bool, tally: PeerTally) -> None:
    table = ctx.rules.peer_groups
    if "deprived" not in group.locked:
        group.deprived = troubled
    if "children" not in group.locked:
        counted = await ctx.session.scalar(
            select(func.coalesce(func.sum(CohortRow.count), 0)).where(
                CohortRow.community_entity_id == group.settlement_entity_id, CohortRow.age_band == AgeBand.CHILD, CohortRow.social_class == group.social_class
            )
        )
        group.children = int(counted or 0) + len(children)
    members = await enrol(ctx, group, children)
    young = set(children)
    staying = [row for row in members if row.mortal_entity_id in young]
    grown_ids: list[int] = []
    for row in members:
        if row.mortal_entity_id not in young and not held(row.mortal_entity_id):
            await grow_up(ctx, group, row, grown_ids, tally)
            grown_ids.append(row.mortal_entity_id)
    for row in staying:
        if held(row.mortal_entity_id):
            continue
        if group.deprived:
            if "deprived_epochs" not in row.locked:
                row.deprived_epochs += 1
            await shift_facet(ctx, row.mortal_entity_id, Facet.CHEERFULNESS, -table.deprived_cheer)
            tally.deprived += 1
            continue
        await shift_facet(ctx, row.mortal_entity_id, PLAY_FACETS[group.play], table.play_facet)
        await practise(ctx.session, ctx.rules, row.mortal_entity_id, PLAY_SKILLS[group.play], table.play_skill, epoch=ctx.epoch)
    if not group.deprived:
        await befriend(ctx, group, [row.mortal_entity_id for row in staying if not held(row.mortal_entity_id)], tally)
    if "cohesion" not in group.locked:
        group.cohesion = clamp_int(group.cohesion + (-table.deprived_cheer if group.deprived else table.play_facet), 0, 100)
    if not staying and group.dissolved_epoch is None and "dissolved_epoch" not in group.locked:
        group.dissolved_epoch = ctx.epoch
    tally.members += len(staying)


async def keep_peers(ctx: TickContext, tally: PeerTally) -> None:
    table = ctx.rules.peer_groups
    atlas = await RegionAtlas.load(ctx.session)
    troubled = await troubled_lands(ctx)
    rows = await ctx.session.execute(
        select(EntityRow, MortalProfileRow.life_stage)
        .join(MortalProfileRow, MortalProfileRow.entity_id == EntityRow.id)
        .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, MortalProfileRow.life_stage.in_(list(YOUNG)))
        .order_by(EntityRow.id)
    )
    found: dict[tuple[int, SocialClass], list[int]] = defaultdict(list)
    for mortal, _stage in rows:
        town = await ctx.session.get(EntityRow, mortal.location_id) if mortal.location_id is not None else None
        if town is not None and town.entity_type is EntityType.SETTLEMENT:
            found[(town.id, mortal.social_class or SocialClass.FARMER)].append(mortal.id)
    groups = {
        (row.settlement_entity_id, row.social_class): row
        for row in await ctx.session.scalars(select(PeerGroupRow).where(PeerGroupRow.dissolved_epoch.is_(None)).order_by(PeerGroupRow.id))
    }
    for key in sorted(set(found) | set(groups), key=lambda item: (item[0], item[1].value)):
        town_id, social_class = key
        children = found.get(key, [])
        group = groups.get(key)
        if held(town_id) or (group is None and len(children) < table.min_children):
            continue
        town = await ctx.session.get(EntityRow, town_id)
        if town is None:
            continue
        if group is None:
            group = PeerGroupRow(
                settlement_entity_id=town_id, social_class=social_class, play=await play_of(ctx, town, social_class), formed_epoch=ctx.epoch, locked=[]
            )
            ctx.session.add(group)
            await ctx.session.flush()
        kept_from_play = atlas.top_region(town_id) in troubled or await put_to_work(ctx, town_id, social_class)
        await keep_group(ctx, group, children, kept_from_play, tally)
        tally.groups += 1
    await ctx.session.flush()


async def companions_of(ctx: TickContext, mortal_id: int | None) -> set[int]:
    if mortal_id is None:
        return set()
    groups = select(PeerMemberRow.group_id).where(PeerMemberRow.mortal_entity_id == mortal_id)
    found = set(await ctx.session.scalars(select(PeerMemberRow.mortal_entity_id).where(PeerMemberRow.group_id.in_(groups))))
    for bond in await active_bonds(ctx.session, [BondKind.COMPANION], sources=[mortal_id]):
        found.add(bond.target_node_id)
    for bond in await active_bonds(ctx.session, [BondKind.COMPANION], targets=[mortal_id]):
        found.add(bond.source_node_id)
    return found - {mortal_id}
