from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.structures import RESEARCH_HOUSES
from aerona.catalog.techniques import BRANCH_GRAPH, TECHNIQUES, Gate
from aerona.constants.units import PERCENT
from aerona.db.repositories.bonds import BondRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import BookContentRow, HolderLevelRow, HolderTechniqueRow, ItemProfileRow
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.warfare import WarSideRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.society import KnowledgeBranch
from aerona.engine.context import TickContext
from aerona.engine.primitives.knowledge import raw_level
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import headcount
from aerona.engine.structures.readers import working

THOUSAND = 1000
ORDERS = frozenset({EntityType.CULT, EntityType.FACTION})
MASTER_SKILL = 50
Levels = dict[int, dict[KnowledgeBranch, int]]


async def holder_levels(session: AsyncSession) -> Levels:
    found: Levels = defaultdict(dict)
    for row in await session.scalars(select(HolderLevelRow)):
        found[row.holder_entity_id][row.branch] = row.level
    return found


def gate_open(gate: Gate, levels: dict[KnowledgeBranch, int]) -> bool:
    if any(levels.get(branch, 0) < level for branch, level in gate.all_of):
        return False
    return not gate.any_of or any(levels.get(branch, 0) >= level for branch, level in gate.any_of)


async def techniques_of(session: AsyncSession, holder_id: int) -> set[Technique]:
    return set(await session.scalars(select(HolderTechniqueRow.technique).where(HolderTechniqueRow.holder_entity_id == holder_id)))


async def has_technique(session: AsyncSession, holder_id: int | None, technique: Technique) -> bool:
    if holder_id is None:
        return False
    return await session.get(HolderTechniqueRow, (holder_id, technique)) is not None


async def known_bonds(session: AsyncSession) -> list[tuple[int, int, KnowledgeBranch, int, int]]:
    statement = (
        select(BondRow.source_node_id, BondRow.target_node_id, EntityRow.knowledge_branch, EntityRow.stats, BondRow.epoch)
        .join(EntityRow, EntityRow.id == BondRow.target_node_id)
        .where(
            BondRow.kind == BondKind.KNOWS,
            BondRow.state == BondState.ACTIVE,
            EntityRow.entity_type == EntityType.KNOWLEDGE,
            EntityRow.status == EntityStatus.CANON,
        )
    )
    found = []
    for holder, knowledge, branch, stats, epoch in await session.execute(statement):
        if branch is not None:
            found.append((holder, knowledge, branch, raw_level(stats), epoch))
    return found


async def ensure_holders(ctx: TickContext) -> int:
    made = 0
    for holder, _knowledge, branch, frontier, learned in await known_bonds(ctx.session):
        row = await ctx.session.get(HolderLevelRow, (holder, branch))
        if row is None:
            start = 1 if learned >= ctx.epoch else frontier
            ctx.session.add(
                HolderLevelRow(
                    holder_entity_id=holder, branch=branch, level=start, practitioners=0, progress=0, secret=False, updated_epoch=ctx.epoch, locked=[]
                )
            )
            made += 1
        elif row.level > frontier and "level" not in row.locked:
            row.level = frontier
    await ctx.session.flush()
    return made


async def institutions(session: AsyncSession, community_id: int) -> int:
    return len(await working(session, RESEARCH_HOUSES, host_id=community_id))


async def need_for(session: AsyncSession, community_id: int, branch: KnowledgeBranch) -> float:
    if branch is KnowledgeBranch.WARFARE:
        fighting = await session.scalar(select(WarSideRow.war_id).where(WarSideRow.entity_id == community_id, WarSideRow.left_epoch.is_(None)).limit(1))
        return 1.0 if fighting is not None else 0.0
    if branch is KnowledgeBranch.AGRICULTURE:
        society = await session.get(CommunitySocietyRow, community_id)
        return 1.0 if society is not None and society.stock_food <= 0 else 0.0
    return 0.0


async def contact(session: AsyncSession, community_id: int, branch: KnowledgeBranch, level: int, levels: Levels) -> float:
    partners = await session.scalars(
        select(BondRow.target_node_id).where(
            BondRow.source_node_id == community_id, BondRow.kind.in_([BondKind.TRADES_WITH, BondKind.ALLY]), BondRow.state == BondState.ACTIVE
        )
    )
    return 1.0 if any(levels.get(partner, {}).get(branch, 0) > level for partner in partners) else 0.0


async def research_factor(ctx: TickContext, community: EntityRow, branch: KnowledgeBranch, level: int, levels: Levels) -> float:
    table = ctx.rules.research
    culture = await ctx.session.get(PeopleCultureRow, community.id)
    literacy = (culture.literacy if culture is not None else 0) / PERCENT
    return (
        (1 + await need_for(ctx.session, community.id, branch) * table.need_pct / PERCENT)
        * (1 + await institutions(ctx.session, community.id) * table.institution_pct / PERCENT)
        * (1 + literacy * table.literacy_pct / PERCENT)
        * (1 + await contact(ctx.session, community.id, branch, level, levels) * table.contact_pct / PERCENT)
    )


async def raise_holder(ctx: TickContext, holder_id: int, branch: KnowledgeBranch, cap: int) -> int | None:
    row = await ctx.session.get(HolderLevelRow, (holder_id, branch))
    if row is None or "level" in row.locked or row.level >= cap:
        return None
    row.level += 1
    row.updated_epoch = ctx.epoch
    return row.level


async def books_of(session: AsyncSession, holder_id: int) -> set[int]:
    owned = select(BondRow.target_node_id).where(BondRow.source_node_id == holder_id, BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE)
    return set(await session.scalars(select(BookContentRow.knowledge_entity_id).where(BookContentRow.book_entity_id.in_(owned))))


async def masters(session: AsyncSession, community_id: int) -> bool:
    mortals = select(EntityRow.id).where(
        EntityRow.location_id == community_id, EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON
    )
    found = await session.scalar(select(SkillRow.holder_node_id).where(SkillRow.holder_node_id.in_(mortals), SkillRow.level >= MASTER_SKILL).limit(1))
    return found is not None


async def practise(ctx: TickContext) -> dict[str, int]:
    table = ctx.rules.research
    counts = {"levels_lost": 0, "forgotten": 0}
    rows = list(await ctx.session.scalars(select(HolderLevelRow).order_by(HolderLevelRow.holder_entity_id, HolderLevelRow.branch)))
    knowledge_by: dict[tuple[int, KnowledgeBranch], int] = {(holder, branch): knowledge for holder, knowledge, branch, _, _ in await known_bonds(ctx.session)}
    for row in rows:
        holder = await ctx.session.get(EntityRow, row.holder_entity_id)
        if holder is None or holder.status is not EntityStatus.CANON:
            continue
        people = headcount(holder) if holder.entity_type in {EntityType.PEOPLE, EntityType.SETTLEMENT, EntityType.CULT} else 1
        before = row.practitioners
        row.practitioners = round_half_up(people * table.practitioners_per_level * max(1, row.level) / THOUSAND) if people else 1
        dying = before and row.practitioners < before // 2
        if not dying or "level" in row.locked:
            continue
        knowledge = knowledge_by.get((row.holder_entity_id, row.branch))
        if (knowledge is not None and knowledge in await books_of(ctx.session, holder.id)) or await masters(ctx.session, holder.id):
            continue
        if not ctx.rng(f"loss.{holder.id}.{row.branch.value}.{ctx.epoch}").chance(table.loss_chance):
            continue
        row.level -= 1
        counts["levels_lost"] += 1
        if row.level <= 0 and knowledge is not None:
            await forget(ctx, holder.id, knowledge)
            await ctx.session.delete(row)
            counts["forgotten"] += 1
    return counts


async def forget(ctx: TickContext, holder_id: int, knowledge_id: int) -> None:
    repository = BondRepository(ctx.session)
    bonds = await ctx.session.scalars(
        select(BondRow).where(
            BondRow.source_node_id == holder_id, BondRow.target_node_id == knowledge_id, BondRow.kind == BondKind.KNOWS, BondRow.state == BondState.ACTIVE
        )
    )
    for bond in list(bonds):
        await repository.deactivate(bond, ctx.epoch, "the last masters died")


async def adopt_techniques(ctx: TickContext) -> int:
    table = ctx.rules.tech_graph
    levels = await holder_levels(ctx.session)
    adopted = 0
    for holder_id in sorted(levels):
        if adopted >= table.cap:
            break
        held = await techniques_of(ctx.session, holder_id)
        holder = await ctx.session.get(EntityRow, holder_id)
        if holder is None or holder.status is not EntityStatus.CANON:
            continue
        for technique, spec in TECHNIQUES.items():
            if technique in held or levels[holder_id].get(spec.branch, 0) < spec.level or not gate_open(spec.gate, levels[holder_id]):
                continue
            if not gate_open(BRANCH_GRAPH[spec.branch], levels[holder_id]) and spec.level > 1:
                continue
            rng = ctx.rng(f"technique.{holder_id}.{technique.value}.{ctx.epoch}")
            if not rng.chance(table.adopt_chance):
                continue
            secret = holder.entity_type in ORDERS and rng.chance(table.secret_pct)
            ctx.session.add(HolderTechniqueRow(holder_entity_id=holder_id, technique=technique, since_epoch=ctx.epoch, secret=secret))
            held.add(technique)
            adopted += 1
    return adopted


async def diffuse_techniques(ctx: TickContext) -> int:
    moved = 0
    levels = await holder_levels(ctx.session)
    links = await ctx.session.execute(
        select(BondRow.source_node_id, BondRow.target_node_id).where(
            BondRow.kind.in_([BondKind.TRADES_WITH, BondKind.ALLY, BondKind.RULES]), BondRow.state == BondState.ACTIVE
        )
    )
    for first, second in links.all():
        for giver, taker in ((first, second), (second, first)):
            theirs = {
                row.technique
                for row in await ctx.session.scalars(
                    select(HolderTechniqueRow).where(HolderTechniqueRow.holder_entity_id == giver, HolderTechniqueRow.secret.is_(False))
                )
            }
            mine = await techniques_of(ctx.session, taker)
            for technique in sorted(theirs - mine):
                spec = TECHNIQUES[technique]
                if levels.get(taker, {}).get(spec.branch, 0) >= spec.level:
                    ctx.session.add(HolderTechniqueRow(holder_entity_id=taker, technique=technique, since_epoch=ctx.epoch, secret=False))
                    mine.add(technique)
                    moved += 1
    return moved


async def steal_technique(ctx: TickContext, thief_id: int, victim_id: int) -> Technique | None:
    secret = await ctx.session.scalars(
        select(HolderTechniqueRow.technique).where(HolderTechniqueRow.holder_entity_id == victim_id, HolderTechniqueRow.secret.is_(True))
    )
    mine = await techniques_of(ctx.session, thief_id)
    for technique in sorted(set(secret) - mine):
        if ctx.rng(f"steal_technique.{thief_id}.{technique.value}.{ctx.epoch}").chance(ctx.rules.tech_graph.steal_chance):
            ctx.session.add(HolderTechniqueRow(holder_entity_id=thief_id, technique=technique, since_epoch=ctx.epoch, secret=True))
            return technique
    return None


async def fill_books(ctx: TickContext) -> int:
    filled = 0
    books = await ctx.session.scalars(select(ItemProfileRow).where(ItemProfileRow.item_class.in_(["book", "scroll", "prayer_book"])))
    for book in list(books):
        if (
            await ctx.session.scalar(select(BookContentRow.knowledge_entity_id).where(BookContentRow.book_entity_id == book.item_entity_id).limit(1))
            is not None
        ):
            continue
        owner = await ctx.session.scalar(
            select(BondRow.source_node_id)
            .where(BondRow.target_node_id == book.item_entity_id, BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE)
            .limit(1)
        )
        if owner is None:
            continue
        known = await ctx.session.scalars(
            select(BondRow.target_node_id).where(BondRow.source_node_id == owner, BondRow.kind == BondKind.KNOWS, BondRow.state == BondState.ACTIVE)
        )
        for knowledge in list(known)[:3]:
            ctx.session.add(BookContentRow(book_entity_id=book.item_entity_id, knowledge_entity_id=knowledge, fidelity=clamp_int(book.quality, 0, PERCENT)))
            filled += 1
    return filled


async def lacks(session: AsyncSession, holder_id: int | None, technique: Technique) -> bool:
    if holder_id is None:
        return False
    held = await techniques_of(session, holder_id)
    return bool(held) and technique not in held
