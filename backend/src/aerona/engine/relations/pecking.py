from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from itertools import pairwise

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.read_memo import memoized
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionMembershipRow, FactionProfileRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.polity import HouseMemberRow, OfficeRow
from aerona.db.tables.relations import GroupRankRow, SocialCircleRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.mind import Facet, ThoughtKind
from aerona.domain.enums.relations import GroupKind, InteractionKind
from aerona.engine.body.book import effective
from aerona.engine.context import TickContext
from aerona.engine.mind.aspirations import rules_over
from aerona.engine.mind.split import facets_of
from aerona.engine.mind.thoughts import think
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import active_bonds
from aerona.engine.relations.book import WARLIKE, ensure_relation, shift
from aerona.engine.relations.interactions import SocialTally, interact, load_scene

FACET_SPAN = 50
LEADING = frozenset({GroupKind.CIRCLE, GroupKind.WARBAND, GroupKind.BAND, GroupKind.CELL})
FACTION_GROUPS: Mapping[GroupKind, frozenset[FactionKind]] = {
    GroupKind.CELL: frozenset({FactionKind.SECRET_SOCIETY, FactionKind.ASSASSINS, FactionKind.REBELS}),
    GroupKind.BAND: frozenset(
        {FactionKind.BANDITS, FactionKind.ROUTE_RAIDERS, FactionKind.CRIME_FAMILY, FactionKind.THIEVES_GUILD, FactionKind.SMUGGLING_RING}
    ),
    GroupKind.TEAM: frozenset({FactionKind.CHARTERED_COMPANY, FactionKind.ENGINEERS_SOCIETY, FactionKind.SCHOLARS_ACADEMY, FactionKind.CLUB}),
}


@dataclass
class PeckingTally:
    groups: int = 0
    challenges: int = 0
    upsets: int = 0
    shares: int = 0


async def living_ids(session: AsyncSession, ids: set[int]) -> set[int]:
    return set(await living_among(session, frozenset(ids)))


@memoized(EntityRow, NodeRow)
async def living_among(session: AsyncSession, ids: frozenset[int]) -> frozenset[int]:
    query = select(EntityRow.id).where(EntityRow.id.in_(ids), EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON)
    return frozenset(await session.scalars(query))


async def groups(session: AsyncSession) -> dict[tuple[int, GroupKind], set[int]]:
    found: dict[tuple[int, GroupKind], set[int]] = defaultdict(set)
    for house, mortal in await session.execute(select(HouseMemberRow.house_entity_id, HouseMemberRow.mortal_entity_id)):
        found[(house, GroupKind.HOUSEHOLD)].add(mortal)
    for polity, holder in await session.execute(select(OfficeRow.polity_entity_id, OfficeRow.holder_entity_id).where(OfficeRow.holder_entity_id.is_not(None))):
        if holder is not None:
            found[(polity, GroupKind.COURT)].add(holder)
    circles = select(SocialCircleRow.faction_entity_id)
    bands = select(FactionProfileRow.faction_entity_id).where(FactionProfileRow.kind.in_(list(WARLIKE)))
    for faction, mortal in await session.execute(
        select(FactionMembershipRow.faction_entity_id, FactionMembershipRow.mortal_entity_id).where(FactionMembershipRow.faction_entity_id.in_(circles))
    ):
        found[(faction, GroupKind.CIRCLE)].add(mortal)
    for faction, mortal in await session.execute(
        select(FactionMembershipRow.faction_entity_id, FactionMembershipRow.mortal_entity_id).where(FactionMembershipRow.faction_entity_id.in_(bands))
    ):
        found[(faction, GroupKind.WARBAND)].add(mortal)
    for bond in await active_bonds(session, [BondKind.CAPTAIN_OF, BondKind.PASSENGER_OF]):
        found[(bond.target_node_id, GroupKind.CREW)].add(bond.source_node_id)
    for kind, factions in FACTION_GROUPS.items():
        chosen = select(FactionProfileRow.faction_entity_id).where(FactionProfileRow.kind.in_(list(factions)))
        for faction, mortal in await session.execute(
            select(FactionMembershipRow.faction_entity_id, FactionMembershipRow.mortal_entity_id).where(FactionMembershipRow.faction_entity_id.in_(chosen))
        ):
            found[(faction, kind)].add(mortal)
    return found


async def dominance(ctx: TickContext, mortal_id: int) -> int:
    table = ctx.rules.pecking
    mortal = await ctx.session.get(EntityRow, mortal_id)
    if mortal is None:
        return 0
    profile = await ctx.session.get(MortalProfileRow, mortal_id)
    facets = await facets_of(ctx.session, mortal_id)
    parts = (
        (await effective(ctx.session, mortal, "strength", rules=ctx.rules), table.strength_pct),
        (await rules_over(ctx.session, mortal_id), table.office_pct),
        (profile.renown if profile is not None else 0, table.renown_pct),
        ((facets.get(Facet.ASSERTIVENESS, 0) + FACET_SPAN) * PERCENT / (2 * FACET_SPAN), table.assertive_pct),
    )
    weight = sum(share for _, share in parts) or 1
    return clamp_int(sum(value * share for value, share in parts) / weight, 0, PERCENT)


async def confront(ctx: TickContext, challenger_id: int, holder_id: int) -> None:
    challenger, holder = await ctx.session.get(EntityRow, challenger_id), await ctx.session.get(EntityRow, holder_id)
    if challenger is None or holder is None or challenger.location_id is None or challenger.location_id != holder.location_id:
        return
    scene = await load_scene(ctx, challenger.location_id, [challenger, holder])
    temper = (await facets_of(ctx.session, challenger_id)).get(Facet.ANGER, 0)
    kind = InteractionKind.BRAWL if temper > 0 else InteractionKind.BOAST
    rng = ctx.rng(seed_of("pecking_confront", challenger_id, holder_id, ctx.epoch))
    await interact(scene, challenger_id, holder_id, kind, rng=rng, tally=SocialTally())


async def challenge(ctx: TickContext, upper: GroupRankRow, lower: GroupRankRow, tally: PeckingTally) -> None:
    tally.challenges += 1
    await confront(ctx, lower.member_node_id, upper.member_node_id)
    rng = ctx.rng(seed_of("pecking", upper.group_node_id, lower.member_node_id, ctx.epoch))
    odds = PERCENT // 2 + (lower.dominance - upper.dominance)
    for holder, other in ((upper.member_node_id, lower.member_node_id), (lower.member_node_id, upper.member_node_id)):
        row = await ensure_relation(ctx.session, holder, other, ctx.epoch)
        if row is not None:
            shift(ctx.rules, row, ctx.epoch, rivalry=ctx.rules.contests.renown, familiarity=2)
    if not rng.chance(max(0, min(PERCENT, odds))):
        return
    upper.rank, lower.rank = lower.rank, upper.rank
    upper.since_epoch = lower.since_epoch = ctx.epoch
    tally.upsets += 1
    await think(ctx.session, ctx.rules, lower.member_node_id, ThoughtKind.ROSE_IN_STANDING, ctx.epoch, subject_id=upper.group_node_id)
    await think(ctx.session, ctx.rules, upper.member_node_id, ThoughtKind.LOST_STANDING, ctx.epoch, subject_id=upper.group_node_id)


async def share(ctx: TickContext, ordered: list[GroupRankRow], tally: PeckingTally) -> None:
    amount = ctx.rules.pecking.wealth_share
    top = await ctx.session.get(MortalProfileRow, ordered[0].member_node_id)
    low = await ctx.session.get(MortalProfileRow, ordered[-1].member_node_id)
    if not amount or top is None or low is None or top is low or "wealth" in top.locked or "wealth" in low.locked or low.wealth < amount:
        return
    low.wealth -= amount
    top.wealth = min(PERCENT, top.wealth + amount)
    tally.shares += 1


async def lead(ctx: TickContext, group_id: int, top: int) -> None:
    profile = await ctx.session.get(FactionProfileRow, group_id)
    if profile is not None and "leader_entity_id" not in profile.locked and not held(group_id):
        profile.leader_entity_id = top


async def contested(ctx: TickContext, group_id: int, upper: GroupRankRow, lower: GroupRankRow) -> bool:
    if "rank" in upper.locked or "rank" in lower.locked or held(upper.member_node_id) or held(lower.member_node_id):
        return False
    if lower.dominance < upper.dominance + ctx.rules.pecking.challenge_margin:
        return False
    return ctx.rng(seed_of("challenge", group_id, lower.member_node_id, ctx.epoch)).chance(ctx.rules.pecking.challenge_pct)


async def order(ctx: TickContext, group_id: int, kind: GroupKind, members: set[int], tally: PeckingTally) -> None:
    rows = {row.member_node_id: row for row in await ctx.session.scalars(select(GroupRankRow).where(GroupRankRow.group_node_id == group_id))}
    for member, row in list(rows.items()):
        if member not in members and "rank" not in row.locked:
            await ctx.session.delete(row)
            del rows[member]
    for member in sorted(members - set(rows)):
        if held(member):
            continue
        rows[member] = GroupRankRow(
            group_node_id=group_id, member_node_id=member, group_kind=kind, rank=len(rows) + 1, dominance=0, since_epoch=ctx.epoch, locked=[]
        )
        ctx.session.add(rows[member])
    for member, row in rows.items():
        if "dominance" not in row.locked and not held(member):
            row.dominance = await dominance(ctx, member)
    ordered = sorted(rows.values(), key=lambda row: (row.rank, row.member_node_id))
    for place, row in enumerate(ordered, start=1):
        row.rank = place
    for upper, lower in pairwise(ordered):
        if await contested(ctx, group_id, upper, lower):
            await challenge(ctx, upper, lower, tally)
    ordered = sorted(rows.values(), key=lambda row: (row.rank, row.member_node_id))
    if kind in LEADING and ordered:
        await lead(ctx, group_id, ordered[0].member_node_id)
    if kind is GroupKind.HOUSEHOLD and len(ordered) >= 2:
        await share(ctx, ordered, tally)
    await ctx.session.flush()


async def tend_pecking(ctx: TickContext, tally: PeckingTally) -> None:
    table = ctx.rules.pecking
    for (group_id, kind), members in sorted((await groups(ctx.session)).items(), key=lambda item: (item[0][0], item[0][1].value)):
        living = await living_ids(ctx.session, members)
        if held(group_id) or len(living) < table.min_members:
            continue
        tally.groups += 1
        await order(ctx, group_id, kind, living, tally)
