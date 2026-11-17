from collections import Counter
from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.cycles import LongPlanRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.genetics import GenomeRow
from aerona.db.tables.military import FeudRow
from aerona.db.tables.mortal import MarriageRow
from aerona.db.tables.polity import ClaimRow, HouseMemberRow, HouseProfileRow, PolityProfileRow
from aerona.db.tables.regime import BreedingPlanRow, LineageSegmentRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.cycles import LongPlanStatus
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.intrigue import IntrigueSecret
from aerona.domain.enums.military import FeudParty, FeudStatus
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import GovernmentKind
from aerona.domain.enums.regime import SegmentLevel
from aerona.domain.enums.unions import UnionPurpose
from aerona.engine.body.customs import people_of
from aerona.engine.collective.book import shift
from aerona.engine.context import TickContext
from aerona.engine.cycles.plans import PlanTally, complete
from aerona.engine.demography.kinship import may_wed
from aerona.engine.intrigue.secrets import keep_secret
from aerona.engine.mortal.kin import children_of, spouses_of
from aerona.engine.mortal.kinship import marry
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import stat_or
from aerona.engine.recording.record import record
from aerona.engine.services.community_relations import change_relation

TRIBAL = frozenset({GovernmentKind.CHIEFDOM, GovernmentKind.TRIBAL_CONFEDERATION})
DEPTH = 12
MATCHES_PER_EPOCH = 2
WEDDING_AGE = 16


@dataclass
class LineageTally:
    segments: int = 0
    backing: int = 0
    matches: int = 0
    love_matches: int = 0
    concealed: int = 0
    bred: int = 0


async def stateless(ctx: TickContext, house: HouseProfileRow) -> bool:
    if house.polity_entity_id is None:
        return True
    profile = await ctx.session.get(PolityProfileRow, house.polity_entity_id)
    return profile is None or profile.government in TRIBAL


async def tribe_for(ctx: TickContext, house: HouseProfileRow) -> int | None:
    founder_id = house.founder_entity_id or house.head_entity_id
    founder = await ctx.session.get(EntityRow, founder_id) if founder_id is not None else None
    people = await people_of(ctx.session, founder) if founder is not None else None
    return people.id if people is not None else None


def segment_level(ctx: TickContext, branches: int, *, founding: bool) -> SegmentLevel:
    if not founding or branches == 0:
        return SegmentLevel.LINEAGE
    return SegmentLevel.TRIBE if branches >= ctx.rules.segmentary_lineages.tribe_houses else SegmentLevel.CLAN


async def seed_segments(ctx: TickContext, tally: LineageTally) -> list[LineageSegmentRow]:
    houses = await ctx.session.execute(
        select(HouseProfileRow, EntityRow)
        .join(EntityRow, EntityRow.id == HouseProfileRow.house_entity_id)
        .where(EntityRow.status == EntityStatus.CANON, HouseProfileRow.extinct_epoch.is_(None))
        .order_by(HouseProfileRow.house_entity_id)
    )
    parents = Counter(await ctx.session.scalars(select(HouseProfileRow.parent_house_id).where(HouseProfileRow.parent_house_id.is_not(None))))
    rows: list[LineageSegmentRow] = []
    for house, _ in houses.all():
        if held(house.house_entity_id) or not await stateless(ctx, house):
            continue
        row = await ctx.session.get(LineageSegmentRow, house.house_entity_id)
        if row is None:
            row = LineageSegmentRow(house_entity_id=house.house_entity_id, since_epoch=ctx.epoch, locked=[])
            ctx.session.add(row)
            tally.segments += 1
        if "level" not in row.locked:
            row.level = segment_level(ctx, parents[house.house_entity_id], founding=house.parent_house_id is None)
        if "tribe_entity_id" not in row.locked:
            row.tribe_entity_id = await tribe_for(ctx, house)
        rows.append(row)
    await ctx.session.flush()
    return rows


async def ancestry(ctx: TickContext, house_id: int) -> list[int]:
    chain = [house_id]
    for _ in range(DEPTH):
        profile = await ctx.session.get(HouseProfileRow, chain[-1])
        if profile is None or profile.parent_house_id is None or profile.parent_house_id in chain:
            break
        chain.append(profile.parent_house_id)
    return chain


async def distance(ctx: TickContext, first: int, second: int) -> int | None:
    left, right = await ancestry(ctx, first), await ancestry(ctx, second)
    shared = next((house for house in left if house in right), None)
    if shared is not None:
        return left.index(shared) + right.index(shared)
    first_row, second_row = await ctx.session.get(LineageSegmentRow, first), await ctx.session.get(LineageSegmentRow, second)
    if first_row is not None and second_row is not None and first_row.tribe_entity_id is not None and first_row.tribe_entity_id == second_row.tribe_entity_id:
        return DEPTH * 2
    return None


async def side_for(ctx: TickContext, row: LineageSegmentRow, feud: FeudRow) -> int | None:
    first, second = feud.first_entity_id, feud.second_entity_id
    if row.house_entity_id in {first, second}:
        return None
    first_row, second_row = await ctx.session.get(LineageSegmentRow, first), await ctx.session.get(LineageSegmentRow, second)
    first_tribe = first_row.tribe_entity_id if first_row is not None else None
    second_tribe = second_row.tribe_entity_id if second_row is not None else None
    if first_tribe != second_tribe:
        if row.tribe_entity_id is not None and row.tribe_entity_id == first_tribe:
            return first
        if row.tribe_entity_id is not None and row.tribe_entity_id == second_tribe:
            return second
        return None
    near, far = await distance(ctx, row.house_entity_id, first), await distance(ctx, row.house_entity_id, second)
    if near is None or far is None or near == far:
        return None
    return first if near < far else second


async def align(ctx: TickContext, rows: list[LineageSegmentRow], tally: LineageTally) -> None:
    feuds = list(await ctx.session.scalars(select(FeudRow).where(FeudRow.status == FeudStatus.ACTIVE, FeudRow.party == FeudParty.HOUSE).order_by(FeudRow.id)))
    for row in rows:
        if "backs_entity_id" in row.locked:
            continue
        backing = None
        for feud in feuds:
            backing = await side_for(ctx, row, feud)
            if backing is not None:
                break
        row.backs_entity_id = backing
        if backing is not None:
            tally.backing += 1
            await change_relation(ctx, row.house_entity_id, backing, ctx.rules.segmentary_lineages.backing_regard, MemoryKind.GOODWILL, note="kin in a feud")


async def carries(ctx: TickContext, mortal_id: int, plan: BreedingPlanRow) -> bool:
    if plan.locus is not None and plan.allele is not None:
        genome = await ctx.session.get(GenomeRow, mortal_id)
        return genome is not None and plan.allele in (genome.genes.get(plan.locus) or [])
    if plan.claim_polity_id is not None:
        claim = await ctx.session.scalar(
            select(ClaimRow.id)
            .where(ClaimRow.claimant_entity_id == mortal_id, ClaimRow.polity_entity_id == plan.claim_polity_id, ClaimRow.ended_epoch.is_(None))
            .limit(1)
        )
        return claim is not None
    return False


async def house_members(ctx: TickContext, house_id: int) -> list[EntityRow]:
    rows = await ctx.session.scalars(
        select(HouseMemberRow.mortal_entity_id).where(HouseMemberRow.house_entity_id == house_id).order_by(HouseMemberRow.mortal_entity_id)
    )
    found = []
    for mortal_id in rows:
        mortal = await living_entity(ctx.session, mortal_id)
        if mortal is not None and mortal.entity_type is EntityType.MORTAL:
            found.append(mortal)
    return found


async def in_love(ctx: TickContext, mortal_id: int) -> bool:
    found = await ctx.session.scalar(
        select(BondRow.id).where(BondRow.source_node_id == mortal_id, BondRow.kind == BondKind.LOVES, BondRow.state == BondState.ACTIVE).limit(1)
    )
    return found is not None


async def match_for(ctx: TickContext, plan: BreedingPlanRow, member: EntityRow, house_ids: set[int]) -> EntityRow | None:
    pool = await ctx.session.scalars(
        select(EntityRow)
        .where(
            EntityRow.entity_type == EntityType.MORTAL,
            EntityRow.status == EntityStatus.CANON,
            EntityRow.world_id == member.world_id,
            EntityRow.id.not_in(house_ids),
        )
        .order_by(EntityRow.id)
    )
    for other in pool:
        if held(other.id) or stat_or(other, "age", 0) < WEDDING_AGE or await spouses_of(ctx.session, other.id):
            continue
        if await carries(ctx, other.id, plan) and await may_wed(ctx.session, ctx.rules, member, other):
            return other
    return None


async def steer(ctx: TickContext, plan: BreedingPlanRow, design: LongPlanRow, tally: LineageTally) -> None:
    table = ctx.rules.breeding_plans
    members = await house_members(ctx, plan.house_entity_id)
    ids = {member.id for member in members}
    made = 0
    for member in members:
        if made >= MATCHES_PER_EPOCH or held(member.id) or stat_or(member, "age", 0) < WEDDING_AGE or await spouses_of(ctx.session, member.id):
            continue
        if await in_love(ctx, member.id) or ctx.rng(f"breeding.love.{plan.plan_id}.{member.id}.{ctx.epoch}").chance(table.love_pct):
            shift(plan, "love_matches", 1, high=10**6)
            shift(design, "progress", -1, high=10**6)
            tally.love_matches += 1
            await record(
                ctx,
                "breeding.love",
                roles={IncidentRole.SUBJECT: member.id, IncidentRole.OPPONENT: plan.house_entity_id},
                facts={"love_matches": plan.love_matches},
            )
            made += 1
            continue
        spouse = await match_for(ctx, plan, member, ids)
        if spouse is None:
            continue
        await marry(ctx.session, member, spouse, ctx.epoch, purpose=UnionPurpose.ALLIANCE, description="a match arranged by a long design")
        shift(plan, "matches", 1, high=10**6)
        tally.matches += 1
        made += 1
        if ctx.rng(f"breeding.conceal.{plan.plan_id}.{member.id}.{ctx.epoch}").chance(table.conceal_pct):
            shift(plan, "concealed", 1, high=10**6)
            shift(design, "secrecy", table.conceal_secrecy)
            await keep_secret(ctx, member.id, IntrigueSecret.TRUE_PARENTAGE, about_id=plan.house_entity_id, severity=table.secret_severity, source=design.name)
            tally.concealed += 1


async def count_barren(ctx: TickContext, plan: BreedingPlanRow, members: list[EntityRow]) -> None:
    if "barren" in plan.locked:
        return
    since = ctx.epoch - ctx.rules.breeding_plans.barren_epochs
    barren = 0
    for member in members:
        wed = await ctx.session.scalar(
            select(MarriageRow.id).where(
                (MarriageRow.first_id == member.id) | (MarriageRow.second_id == member.id), MarriageRow.end_epoch.is_(None), MarriageRow.start_epoch <= since
            )
        )
        if wed is not None and not await children_of(ctx.session, member.id):
            barren += 1
    plan.barren = barren


async def advance_breeding(ctx: TickContext, tally: LineageTally) -> None:
    rows = await ctx.session.execute(
        select(BreedingPlanRow, LongPlanRow)
        .join(LongPlanRow, LongPlanRow.id == BreedingPlanRow.plan_id)
        .where(LongPlanRow.status == LongPlanStatus.ACTIVE)
        .order_by(BreedingPlanRow.plan_id)
    )
    for plan, design in rows.all():
        if held(plan.house_entity_id, design.holder_node_id) or "status" in design.locked:
            continue
        await steer(ctx, plan, design, tally)
        members = await house_members(ctx, plan.house_entity_id)
        await count_barren(ctx, plan, members)
        carrying = sum([1 for member in members if await carries(ctx, member.id, plan)])
        share = carrying * PERCENT / len(members) if members else 0
        if "progress" not in design.locked:
            design.progress = clamp_int(round_half_up(design.steps * min(1.0, share / max(1, plan.target_share))), 0, design.steps)
        if design.progress >= design.steps:
            holder = await living_entity(ctx.session, design.holder_node_id)
            await complete(ctx, design, holder, PlanTally())
            tally.bred += 1
    await ctx.session.flush()


async def keep_lineages(ctx: TickContext, tally: LineageTally) -> None:
    rows = await seed_segments(ctx, tally)
    await align(ctx, rows, tally)
    await advance_breeding(ctx, tally)
    await ctx.session.flush()
