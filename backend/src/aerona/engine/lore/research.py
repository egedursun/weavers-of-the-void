from collections import defaultdict
from itertools import combinations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.structures import RESEARCH_HOUSES
from aerona.catalog.techniques import BRANCH_SKILLS, TECHNIQUES, Gate
from aerona.constants.units import PERCENT
from aerona.db.read_memo import memoized
from aerona.db.repositories.bonds import BondRepository
from aerona.db.tables.body import BodyRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import BookContentRow, CustomKindRow, HolderCustomTechniqueRow, HolderLevelRow, HolderTechniqueRow, ItemProfileRow
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.governance import OrgResearchRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.networks import NetworkNodeRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.warfare import WarSideRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.eras import EraChannel
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.society import KnowledgeBranch
from aerona.engine.agrarian.book import farming_boost
from aerona.engine.context import TickContext
from aerona.engine.crafts.reckoning import notation_boost
from aerona.engine.eras.effects import era_floors, tech_bonus
from aerona.engine.lore.eras import era_factor
from aerona.engine.lore.kinds import custom_bases
from aerona.engine.lore.learning import institution_factor, patron_factor
from aerona.engine.lore.printing import banned_for, read_in_secret
from aerona.engine.lore.truth import branch_factor
from aerona.engine.means.media import legible
from aerona.engine.museums.reading import collection_factor
from aerona.engine.networks.book import reach_pct
from aerona.engine.polity.laws import law_param
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.knowledge import raw_level
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import headcount, set_stats, stat
from aerona.engine.recording.record import record
from aerona.engine.regime.book import freedom_factor, school_factor, schooled
from aerona.engine.structures.readers import working
from aerona.rules.registry import Rules

THOUSAND = 1000
NATURAL_BRANCHES = frozenset(
    {KnowledgeBranch.ASTRONOMY, KnowledgeBranch.MEDICINE, KnowledgeBranch.AGRICULTURE, KnowledgeBranch.METALLURGY, KnowledgeBranch.SEAFARING}
)
SCHOLARLY = (SkillKind.LORE, SkillKind.THEOLOGY, SkillKind.WRITING, SkillKind.ASTRONOMY, SkillKind.MEDICINE, SkillKind.LAW, SkillKind.ALCHEMY)
Levels = dict[int, dict[KnowledgeBranch, int]]


async def holder_levels(session: AsyncSession) -> Levels:
    found: Levels = defaultdict(dict)
    for holder, branch, level in await session.execute(select(HolderLevelRow.holder_entity_id, HolderLevelRow.branch, HolderLevelRow.level)):
        found[holder][branch] = level
    return found


def gate_open(gate: Gate, levels: dict[KnowledgeBranch, int]) -> bool:
    if any(levels.get(branch, 0) < level for branch, level in gate.all_of):
        return False
    return not gate.any_of or any(levels.get(branch, 0) >= level for branch, level in gate.any_of)


@memoized(HolderTechniqueRow, CustomKindRow, HolderCustomTechniqueRow)
async def known_techniques(session: AsyncSession, holder_id: int) -> frozenset[Technique]:
    known = set(await session.scalars(select(HolderTechniqueRow.technique).where(HolderTechniqueRow.holder_entity_id == holder_id)))
    return frozenset(known | await custom_bases(session, holder_id))


async def techniques_of(session: AsyncSession, holder_id: int) -> set[Technique]:
    return set(await known_techniques(session, holder_id))


async def has_technique(session: AsyncSession, holder_id: int | None, technique: Technique) -> bool:
    if holder_id is None:
        return False
    if await session.get(HolderTechniqueRow, (holder_id, technique)) is not None:
        return True
    return technique in await custom_bases(session, holder_id)


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
    floors = await era_floors(ctx.session)
    for holder, _knowledge, branch, frontier, learned in await known_bonds(ctx.session):
        if held(holder):
            continue
        row = await ctx.session.get(HolderLevelRow, (holder, branch))
        if row is None:
            start = max(1 if learned >= ctx.epoch else frontier, floors.get(branch, 0))
            ctx.session.add(
                HolderLevelRow(
                    holder_entity_id=holder, branch=branch, level=start, practitioners=0, progress=0, secret=False, updated_epoch=ctx.epoch, locked=[]
                )
            )
            made += 1
        elif row.level > max(frontier, floors.get(branch, 0)) and "level" not in row.locked:
            row.level = max(frontier, floors.get(branch, 0))
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
        * (1 + max(await scholar_levels(ctx.session, ctx.rules, community.id, branch), default=0.0) / PERCENT * table.scholar_pct / PERCENT)
        * await institution_factor(ctx.session, ctx.rules, community.id)
        * await patron_factor(ctx.session, ctx.rules, community.id)
        * await thought_factor(ctx, community.id, branch)
        * await era_factor(ctx.session, ctx.rules, community.id)
        * await branch_factor(ctx.session, ctx.rules, community.id, branch)
        * await freedom_factor(ctx.session, ctx.rules, community.id)
        * await school_factor(ctx.session, ctx.rules, community.id)
        * (await farming_boost(ctx.session, community) if branch is KnowledgeBranch.AGRICULTURE else 1.0)
        * await notation_boost(ctx.session, ctx.rules, community.id, branch)
        * await collection_factor(ctx.session, ctx.rules, community.id, natural=branch in NATURAL_BRANCHES)
    )


async def thought_factor(ctx: TickContext, community_id: int, branch: KnowledgeBranch) -> float:
    table = ctx.rules.technique_effects
    known = await techniques_of(ctx.session, community_id)
    natural = table.philosophy_pct if branch in NATURAL_BRANCHES and Technique.NATURAL_PHILOSOPHY in known else 0
    tried = table.empiricism_pct if Technique.EMPIRICISM in known else 0
    machines = await tech_bonus(ctx.session, ctx.rules, community_id, EraChannel.RESEARCH)
    return (1 + (natural + tried + machines) / PERCENT) * ctx.rules.eras.research_speed_pct / PERCENT


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


async def scholar_levels(session: AsyncSession, rules: Rules, community_id: int, branch: KnowledgeBranch) -> list[float]:
    mortals = select(EntityRow.id).where(
        await present_among(session, [community_id]), EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON
    )
    field = set(BRANCH_SKILLS.get(branch, ()))
    skills = list({*SCHOLARLY, *field})
    expertise = 1 + rules.research_depth.expertise_pct / PERCENT
    rows = await session.execute(
        select(SkillRow.holder_node_id, SkillRow.skill, SkillRow.level).where(SkillRow.holder_node_id.in_(mortals), SkillRow.skill.in_(skills))
    )
    best: dict[int, float] = {}
    for holder, skill, level in rows:
        best[holder] = max(best.get(holder, 0.0), int(level) * (expertise if skill in field else 1.0))
    if not best:
        return []
    bodies = {row.node_id: row.scholarship for row in await session.scalars(select(BodyRow).where(BodyRow.node_id.in_(list(best))))}
    return [level * bodies.get(holder, PERCENT) / PERCENT for holder, level in best.items()]


async def masters(session: AsyncSession, rules: Rules, community_id: int, branch: KnowledgeBranch | None = None) -> bool:
    mortals = select(EntityRow.id).where(
        await present_among(session, [community_id]), EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON
    )
    skilled = select(SkillRow.holder_node_id).where(SkillRow.holder_node_id.in_(mortals), SkillRow.level >= rules.research.master_skill)
    if branch is not None:
        skilled = skilled.where(SkillRow.skill.in_(list(BRANCH_SKILLS.get(branch, ()))))
    holders = set(await session.scalars(skilled))
    if not holders:
        return False
    unable = select(BodyRow.node_id).where(BodyRow.node_id.in_(list(holders)), BodyRow.scholarship < rules.research.master_scholarship)
    return bool(holders - set(await session.scalars(unable)))


async def practise(ctx: TickContext) -> dict[str, int]:
    table = ctx.rules.research
    counts = {"levels_lost": 0, "forgotten": 0}
    rows = list(await ctx.session.scalars(select(HolderLevelRow).order_by(HolderLevelRow.holder_entity_id, HolderLevelRow.branch)))
    floors = await era_floors(ctx.session)
    knowledge_by: dict[tuple[int, KnowledgeBranch], int] = {(holder, branch): knowledge for holder, knowledge, branch, _, _ in await known_bonds(ctx.session)}
    for row in rows:
        holder = await ctx.session.get(EntityRow, row.holder_entity_id)
        if holder is None or holder.status is not EntityStatus.CANON:
            continue
        people = headcount(holder) if holder.entity_type in {EntityType.PEOPLE, EntityType.SETTLEMENT, EntityType.CULT} else 1
        before = row.practitioners
        row.practitioners = round_half_up(people * table.practitioners_per_level * max(1, row.level) / THOUSAND) if people else 1
        dying = before and row.practitioners < before // 2
        if not dying or "level" in row.locked or row.level <= floors.get(row.branch, 0):
            continue
        knowledge = knowledge_by.get((row.holder_entity_id, row.branch))
        if (knowledge is not None and knowledge in await books_of(ctx.session, holder.id)) or await masters(ctx.session, ctx.rules, holder.id, row.branch):
            continue
        if await schooled(ctx.session, holder.id):
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


async def network_pairs(ctx: TickContext) -> list[tuple[int, int]]:
    members: dict[int, list[int]] = {}
    for network_id, member in await ctx.session.execute(select(NetworkNodeRow.network_entity_id, NetworkNodeRow.member_node_id).order_by(NetworkNodeRow.id)):
        members.setdefault(network_id, []).append(member)
    pairs: list[tuple[int, int]] = []
    for network_id, joined in members.items():
        for first, second in combinations(joined, 2):
            reach = await reach_pct(ctx.session, ctx.rules, first, ctx.epoch, kind="carries_records")
            if reach and ctx.rng(f"diffusion.network.{network_id}.{first}.{second}.{ctx.epoch}").chance(reach):
                pairs.append((first, second))
    return pairs


async def diffuse_techniques(ctx: TickContext) -> int:
    moved = 0
    levels = await holder_levels(ctx.session)
    links = await ctx.session.execute(
        select(BondRow.source_node_id, BondRow.target_node_id).where(
            BondRow.kind.in_([BondKind.TRADES_WITH, BondKind.ALLY, BondKind.RULES]), BondRow.state == BondState.ACTIVE
        )
    )
    pairs = [*links.all(), *await network_pairs(ctx)]
    hidden: dict[int, set[KnowledgeBranch]] = defaultdict(set)
    for holder_id, branch in await ctx.session.execute(select(HolderLevelRow.holder_entity_id, HolderLevelRow.branch).where(HolderLevelRow.secret.is_(True))):
        hidden[holder_id].add(branch)
    shared: dict[int, set[Technique]] = defaultdict(set)
    for holder_id, known in await ctx.session.execute(
        select(HolderTechniqueRow.holder_entity_id, HolderTechniqueRow.technique).where(HolderTechniqueRow.secret.is_(False))
    ):
        shared[holder_id].add(known)
    learned: dict[int, set[Technique]] = {}
    for first, second in pairs:
        for giver, taker in ((first, second), (second, first)):
            if held(taker):
                continue
            veiled = hidden.get(giver, set())
            theirs = {technique for technique in shared.get(giver, set()) if TECHNIQUES[technique].branch not in veiled}
            mine = learned.get(taker)
            if mine is None:
                mine = learned[taker] = await techniques_of(ctx.session, taker)
            term = await law_param(ctx.session, giver, LawKind.INTELLECTUAL_PROPERTY, "term")
            guarded = min(PERCENT, (int(term) if isinstance(term, int) else 0) * ctx.rules.tech_graph.patent_block_pct)
            for technique in sorted(theirs - mine):
                spec = TECHNIQUES[technique]
                if guarded and ctx.rng(f"patent.{giver}.{taker}.{technique.value}.{ctx.epoch}").chance(guarded):
                    continue
                if levels.get(taker, {}).get(spec.branch, 0) >= spec.level:
                    ctx.session.add(HolderTechniqueRow(holder_entity_id=taker, technique=technique, since_epoch=ctx.epoch, secret=False))
                    mine.add(technique)
                    shared[taker].add(technique)
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
            await research_stolen(ctx, victim_id, thief_id, technique)
            return technique
    await steal_level(ctx, thief_id, victim_id)
    return None


async def research_stolen(ctx: TickContext, victim_id: int, thief_id: int, technique: Technique) -> None:
    researched = await ctx.session.scalar(
        select(OrgResearchRow.id).where(OrgResearchRow.org_node_id == victim_id, OrgResearchRow.technique == technique, OrgResearchRow.done_epoch.is_not(None))
    )
    if researched is not None:
        await record(ctx, "org.research_stolen", roles={IncidentRole.VICTIM: victim_id, IncidentRole.ACTOR: thief_id}, facts={"technique": technique})


async def steal_level(ctx: TickContext, thief_id: int, victim_id: int) -> KnowledgeBranch | None:
    hidden = await ctx.session.scalars(
        select(HolderLevelRow).where(HolderLevelRow.holder_entity_id == victim_id, HolderLevelRow.secret.is_(True)).order_by(HolderLevelRow.branch)
    )
    for victim in hidden:
        mine = await ctx.session.get(HolderLevelRow, (thief_id, victim.branch))
        if mine is None or mine.level >= victim.level or "level" in mine.locked:
            continue
        if ctx.rng(f"steal_level.{thief_id}.{victim.branch.value}.{ctx.epoch}").chance(ctx.rules.tech_graph.steal_chance):
            mine.level += 1
            return victim.branch
    return None


async def read_books(ctx: TickContext) -> int:
    table = ctx.rules.research
    taught = 0
    for book, knowledge, fidelity in (
        await ctx.session.execute(select(BookContentRow.book_entity_id, BookContentRow.knowledge_entity_id, BookContentRow.fidelity))
    ).all():
        owner = await ctx.session.scalar(
            select(BondRow.source_node_id).where(BondRow.target_node_id == book, BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE).limit(1)
        )
        known_record = await ctx.session.get(EntityRow, knowledge)
        reader = await ctx.session.get(EntityRow, owner) if owner is not None else None
        if reader is None or known_record is None or known_record.knowledge_branch is None:
            continue
        holder = reader.location_id if reader.entity_type is EntityType.MORTAL else reader.id
        if await banned_for(ctx.session, holder, book) and not await read_in_secret(ctx, reader.id, book):
            continue
        row = await ctx.session.get(HolderLevelRow, (holder, known_record.knowledge_branch)) if holder is not None else None
        if row is None or "progress" in row.locked or row.level >= raw_level(known_record.stats):
            continue
        paper = ctx.rules.technique_effects.paper_pct if await has_technique(ctx.session, holder, Technique.PAPER) else 0
        monks = ctx.rules.technique_effects.monastic_pct if await has_technique(ctx.session, holder, Technique.MONASTICISM) else 0
        read = table.book_progress * fidelity / PERCENT * (1 + (paper + monks) / PERCENT) * await legible(ctx, book)
        row.progress = clamp_int(row.progress + round_half_up(read), 0, PERCENT)
        taught += 1
    return taught


async def spread_of(ctx: TickContext) -> int:
    measured = 0
    peoples: dict[int | None, int | None] = {}
    learners: dict[tuple[int | None, KnowledgeBranch | None], int | None] = {}
    for knowledge in list(
        await ctx.session.scalars(select(EntityRow).where(EntityRow.entity_type == EntityType.KNOWLEDGE, EntityRow.status == EntityStatus.CANON))
    ):
        if knowledge.world_id not in peoples:
            peoples[knowledge.world_id] = await ctx.session.scalar(
                select(func.count(EntityRow.id)).where(
                    EntityRow.world_id == knowledge.world_id,
                    EntityRow.status == EntityStatus.CANON,
                    EntityRow.entity_type.in_([EntityType.PEOPLE, EntityType.SETTLEMENT]),
                )
            )
        communities = peoples[knowledge.world_id]
        place = (knowledge.world_id, knowledge.knowledge_branch)
        if place not in learners:
            learners[place] = await ctx.session.scalar(
                select(func.count(func.distinct(HolderLevelRow.holder_entity_id))).where(
                    HolderLevelRow.branch == knowledge.knowledge_branch,
                    HolderLevelRow.level >= 1,
                    HolderLevelRow.holder_entity_id.in_(select(EntityRow.id).where(EntityRow.world_id == knowledge.world_id)),
                )
            )
        holders = learners[place]
        if communities:
            set_stats(knowledge, spread=clamp_int(round_half_up(int(holders or 0) * PERCENT / int(communities)), 0, PERCENT))
            measured += 1
    return measured


async def mean_spread(session: AsyncSession) -> float:
    values = [
        raw for raw in await session.scalars(select(EntityRow).where(EntityRow.entity_type == EntityType.KNOWLEDGE, EntityRow.status == EntityStatus.CANON))
    ]
    spreads = [stat(item, "spread") or 0 for item in values]
    return sum(spreads) / len(spreads) if spreads else 0.0


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
            select(BondRow.target_node_id)
            .where(BondRow.source_node_id == owner, BondRow.kind == BondKind.KNOWS, BondRow.state == BondState.ACTIVE)
            .distinct()
            .order_by(BondRow.target_node_id)
        )
        subjects = 1 + max(0, book.quality) // ctx.rules.scale.book_quality_per_subject
        for knowledge in ctx.rng(f"book.subjects.{book.item_entity_id}").sample(list(known), subjects):
            ctx.session.add(BookContentRow(book_entity_id=book.item_entity_id, knowledge_entity_id=knowledge, fidelity=clamp_int(book.quality, 0, PERCENT)))
            filled += 1
    return filled


async def lacks(session: AsyncSession, holder_id: int | None, technique: Technique) -> bool:
    if holder_id is None:
        return False
    known = await techniques_of(session, holder_id)
    return bool(known) and technique not in known
