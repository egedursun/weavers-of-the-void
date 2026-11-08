from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.civics import CAPABILITIES, CAPABILITY_INSTITUTIONS, SOCIAL_CHANGE, TRIGGERS
from aerona.catalog.techniques import BRANCH_GRAPH, BRANCH_SKILLS, INSTITUTIONS, TECHNIQUES
from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import SkyEventRow
from aerona.db.tables.culture import HolderTechniqueRow, InstitutionRow, ResearchBoostRow, ResearchFocusRow, ResearchProgressRow
from aerona.db.tables.discovery import WorldEraRow
from aerona.db.tables.disease import OutbreakRow
from aerona.db.tables.economy import LoanRow, ProductionRunRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.justice import CrimeCaseRow
from aerona.db.tables.military import CaptiveCohortRow, OccupationRow
from aerona.db.tables.mind import CultureValueRow, SkillRow
from aerona.db.tables.polity import OfficeRow, PolityProfileRow, TreatyClauseRow, TreatyProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.warfare import SiegeRow, WarSideRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.culture import BoostTrigger, Capability, ResearchChooser, Technique
from aerona.domain.enums.disease import OutbreakStatus
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus, EntityType
from aerona.domain.enums.environment import TerrainKind
from aerona.domain.enums.polity import ClauseKind, OfficeKind, TreatyKind, TreatyStatus
from aerona.domain.enums.renown import Currency
from aerona.domain.enums.society import KnowledgeBranch, SocialClass
from aerona.domain.enums.structure import StructureKind
from aerona.domain.enums.war import SiegeStatus
from aerona.domain.enums.world import SkyEventKind
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import wealth_points
from aerona.engine.economy.stocks import holding
from aerona.engine.faith.book import patron_node
from aerona.engine.gods.queries import community_of
from aerona.engine.lore.learning import court_scholar, realm_of
from aerona.engine.lore.research import gate_open, has_technique, holder_levels, need_for, techniques_of
from aerona.engine.notes import note
from aerona.engine.polity.accords import parties_of
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import shift_stat, stat
from aerona.engine.renown.currencies import bump, purse_of, ruler_of_realm
from aerona.engine.structures.readers import working
from aerona.rules.registry import Rules

TRADE_KINDS = (BondKind.TRADES_WITH, BondKind.ALLY)
FIELD_SKILL_FLOOR = 0
SECRETIVE = frozenset({EntityType.CULT, EntityType.FACTION})
LIBRARIES = (StructureKind.LIBRARY, StructureKind.ACADEMY, StructureKind.SCHOOL)
RESEARCHERS = frozenset({EntityType.PEOPLE, EntityType.SETTLEMENT, EntityType.CULT, EntityType.FACTION})


@dataclass
class DepthTally:
    counts: dict[str, int] = field(default_factory=dict)

    def add(self, key: str, value: int = 1) -> None:
        self.counts[key] = self.counts.get(key, 0) + value


async def trade_partners(session: AsyncSession, community_id: int) -> set[int]:
    rows = await session.scalars(
        select(BondRow.target_node_id).where(BondRow.source_node_id == community_id, BondRow.kind.in_(TRADE_KINDS), BondRow.state == BondState.ACTIVE)
    )
    return set(rows)


def bordering(atlas: RegionAtlas, community_id: int) -> set[int]:
    region = atlas.top_region(community_id)
    if region is None:
        return set()
    near = {region, *atlas.neighbour_regions(region)}
    return {other for place in near for other in atlas.communities_in(place) if other != community_id}


async def neighbours(session: AsyncSession, atlas: RegionAtlas, community_id: int) -> set[int]:
    return bordering(atlas, community_id) | await trade_partners(session, community_id)


async def catch_up(ctx: TickContext, atlas: RegionAtlas, holder_id: int, technique: Technique) -> float:
    table = ctx.rules.research_depth
    known = 0
    for other in sorted(await neighbours(ctx.session, atlas, holder_id)):
        known += int(await has_technique(ctx.session, other, technique))
    return 1 + min(table.catch_up_cap, known * table.catch_up_pct) / PERCENT


async def era_known(ctx: TickContext, holder_id: int, technique: Technique) -> float:
    holder = await ctx.session.get(EntityRow, holder_id)
    era = await ctx.session.get(WorldEraRow, holder.world_id) if holder is not None and holder.world_id is not None else None
    if era is None or TECHNIQUES[technique].level > era.era:
        return 1.0
    return 1 + ctx.rules.research_depth.era_known_pct / PERCENT


async def capable(session: AsyncSession, holder_id: int, capability: Capability, levels: dict[KnowledgeBranch, int] | None = None) -> bool:
    spec = CAPABILITIES[capability]
    levels = (await holder_levels(session)).get(holder_id, {}) if levels is None else levels
    if any(levels.get(branch, 0) < level for branch, level in spec.branches):
        return False
    known = await techniques_of(session, holder_id)
    return all(item in known for item in spec.all_of) and (not spec.any_of or any(item in known for item in spec.any_of))


async def capable_among(session: AsyncSession, holder_ids: list[int], capability: Capability) -> set[int]:
    levels = await holder_levels(session)
    return {holder for holder in holder_ids if holder in levels and await capable(session, holder, capability, levels[holder])}


async def research_home(session: AsyncSession, actor: EntityRow) -> EntityRow | None:
    if actor.entity_type in RESEARCHERS:
        return actor
    if actor.entity_type is not EntityType.MORTAL:
        return None
    home = await community_of(session, actor)
    return home if home is not None and home.entity_type in RESEARCHERS else None


async def research_choices(session: AsyncSession, holder_id: int) -> list[Technique]:
    levels = (await holder_levels(session)).get(holder_id, {})
    within = await open_techniques(session, holder_id, levels)
    row = await session.get(ResearchFocusRow, holder_id)
    offered = [Technique(item) for item in row.options if item in Technique._value2member_map_] if row is not None else []
    return [item for item in offered if item in within] or within


async def capabilities_of(session: AsyncSession, holder_id: int) -> list[Capability]:
    return [capability for capability in Capability if await capable(session, holder_id, capability)]


async def add_progress(ctx: TickContext, holder_id: int, technique: Technique, amount: int) -> int:
    row = await ctx.session.get(ResearchProgressRow, (holder_id, technique))
    if row is None:
        row = ResearchProgressRow(holder_entity_id=holder_id, technique=technique, progress=0, updated_epoch=ctx.epoch)
        ctx.session.add(row)
    row.progress = clamp_int(row.progress + amount, 0, PERCENT - 1)
    row.updated_epoch = ctx.epoch
    return row.progress


async def boost(ctx: TickContext, holder_id: int, trigger: BoostTrigger) -> int:
    known = await techniques_of(ctx.session, holder_id)
    pushed = 0
    for technique in TRIGGERS[trigger].techniques:
        if technique in known:
            continue
        already = await ctx.session.scalar(
            select(ResearchBoostRow.id).where(
                ResearchBoostRow.holder_entity_id == holder_id, ResearchBoostRow.technique == technique, ResearchBoostRow.trigger == trigger
            )
        )
        if already is not None:
            continue
        amount = ctx.rules.research_depth.boost_progress
        await add_progress(ctx, holder_id, technique, amount)
        ctx.session.add(ResearchBoostRow(holder_entity_id=holder_id, technique=technique, trigger=trigger, progress=amount, epoch=ctx.epoch))
        pushed += 1
    return pushed


@dataclass
class Deeds:
    by_trigger: dict[BoostTrigger, set[int]] = field(default_factory=dict)

    def of(self, community_id: int) -> list[BoostTrigger]:
        return [trigger for trigger in BoostTrigger if community_id in self.by_trigger.get(trigger, set())]


async def gather_deeds(ctx: TickContext, atlas: RegionAtlas, communities: list[EntityRow]) -> Deeds:
    table = ctx.rules.research_depth
    recent = ctx.epoch - 1
    ids = [item.id for item in communities]
    deeds = Deeds()
    fishing = await ctx.session.execute(
        select(ProductionRunRow.community_entity_id)
        .where(ProductionRunRow.community_entity_id.in_(ids), ProductionRunRow.output == CommodityKind.FISH, ProductionRunRow.epoch >= recent)
        .group_by(ProductionRunRow.community_entity_id)
        .having(func.sum(ProductionRunRow.quantity) >= table.fishing_scale)
    )
    deeds.by_trigger[BoostTrigger.COASTAL_FISHING] = set(fishing.scalars())
    deeds.by_trigger[BoostTrigger.SURVIVED_SIEGE] = set(
        await ctx.session.scalars(select(SiegeRow.besieged_entity_id).where(SiegeRow.status == SiegeStatus.REPULSED, SiegeRow.ended_epoch >= recent))
    )
    plagued = set(
        await ctx.session.scalars(select(OutbreakRow.region_entity_id).where(OutbreakRow.status == OutbreakStatus.ENDED, OutbreakRow.ended_epoch >= recent))
    )
    deeds.by_trigger[BoostTrigger.SURVIVED_EPIDEMIC] = {item for item in ids if atlas.top_region(item) in plagued}
    dark = set(await ctx.session.scalars(select(SkyEventRow.world_id).where(SkyEventRow.kind == SkyEventKind.ECLIPSE, SkyEventRow.epoch >= recent)))
    watched = {item.profile.host_entity_id for item in await working(ctx.session, (StructureKind.OBSERVATORY,))} if dark else set()
    deeds.by_trigger[BoostTrigger.ECLIPSE_OBSERVED] = {item.id for item in communities if item.world_id in dark and item.id in watched}
    deeds.by_trigger[BoostTrigger.GREAT_TRIAL] = set(
        await ctx.session.scalars(
            select(CrimeCaseRow.settlement_entity_id).where(CrimeCaseRow.closed_epoch >= recent, CrimeCaseRow.evidence >= table.great_trial_evidence)
        )
    )
    loans = await ctx.session.execute(
        select(LoanRow.lender_entity_id, LoanRow.borrower_entity_id).where(LoanRow.principal >= table.great_debt, LoanRow.issued_epoch >= recent)
    )
    deeds.by_trigger[BoostTrigger.GREAT_DEBT] = {party for pair in loans.all() for party in pair if party is not None}
    fighting = set(await ctx.session.scalars(select(WarSideRow.entity_id).where(WarSideRow.left_epoch.is_(None))))
    riders: set[int] = set()
    for community in communities:
        region = atlas.top_region(community.id)
        if community.id not in fighting or region is None:
            continue
        land = await ctx.session.get(RegionEnvironmentRow, region)
        if land is not None and land.dominant_terrain is TerrainKind.STEPPE and await holding(ctx.session, community.id, CommodityKind.MOUNTS) > 0:
            riders.add(community.id)
    deeds.by_trigger[BoostTrigger.STEPPE_HORSES_AT_WAR] = riders
    return deeds


async def deeds_push_research(ctx: TickContext, tally: DepthTally) -> None:
    atlas = await RegionAtlas.load(ctx.session)
    communities = [item for item in await living_researchers(ctx.session) if not held(item.id)]
    deeds = await gather_deeds(ctx, atlas, communities)
    for community in communities:
        for trigger in deeds.of(community.id):
            pushed = await boost(ctx, community.id, trigger)
            if pushed:
                tally.add("boosts", pushed)
                await note(
                    ctx,
                    f"{community.name} learned from what it lived through: {TRIGGERS[trigger].label.lower()} pushed its research forward.",
                    key="research.boosted",
                    ids=[community.id],
                    kind=ChronicleKind.KNOWLEDGE,
                )


async def living_researchers(session: AsyncSession) -> list[EntityRow]:
    rows = await session.scalars(
        select(EntityRow).where(EntityRow.entity_type.in_(list(RESEARCHERS)), EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    return list(rows)


async def open_techniques(session: AsyncSession, holder_id: int, levels: dict[KnowledgeBranch, int]) -> list[Technique]:
    known = await techniques_of(session, holder_id)
    found: list[Technique] = []
    for technique, spec in TECHNIQUES.items():
        if technique in known or levels.get(spec.branch, 0) < spec.level or not gate_open(spec.gate, levels):
            continue
        if spec.level > 1 and not gate_open(BRANCH_GRAPH[spec.branch], levels):
            continue
        found.append(technique)
    return found


async def draw_options(ctx: TickContext, holder_id: int, levels: dict[KnowledgeBranch, int]) -> list[Technique]:
    table = ctx.rules.research_depth
    pool = await open_techniques(ctx.session, holder_id, levels)
    boosted = set(await ctx.session.scalars(select(ResearchProgressRow.technique).where(ResearchProgressRow.holder_entity_id == holder_id)))
    weights: dict[Technique, int] = {}
    for technique in pool:
        need = await need_for(ctx.session, holder_id, TECHNIQUES[technique].branch)
        weights[technique] = 1 + round(need * table.need_weight) + (table.boost_weight if technique in boosted else 0)
    rng = ctx.rng(f"research.options.{holder_id}.{ctx.epoch}")
    chosen: list[Technique] = []
    while pool and len(chosen) < table.options:
        pick = rng.weighted_by(pool, lambda item: weights[item])
        chosen.append(pick)
        pool = [item for item in pool if item is not pick]
    return chosen


async def field_skill(session: AsyncSession, community_id: int, branch: KnowledgeBranch) -> int:
    mortals = select(EntityRow.id).where(
        await present_among(session, [community_id]), EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON
    )
    skills = list(BRANCH_SKILLS.get(branch, ()))
    if not skills:
        return FIELD_SKILL_FLOOR
    best = await session.scalar(select(func.max(SkillRow.level)).where(SkillRow.holder_node_id.in_(mortals), SkillRow.skill.in_(skills)))
    return int(best or FIELD_SKILL_FLOOR)


async def scholars_choose(ctx: TickContext, holder_id: int, options: list[Technique]) -> Technique:
    scored = [(await field_skill(ctx.session, holder_id, TECHNIQUES[item].branch), -index, item) for index, item in enumerate(options)]
    return max(scored)[2]


async def set_focus(ctx: TickContext, tally: DepthTally) -> None:
    levels = await holder_levels(ctx.session)
    for holder_id in sorted(levels):
        if held(holder_id):
            continue
        row = await ctx.session.get(ResearchFocusRow, holder_id)
        known = await techniques_of(ctx.session, holder_id)
        if row is not None and "technique" in row.locked and row.technique not in known:
            continue
        if row is not None and row.chooser is ResearchChooser.AGENT and row.technique not in known and row.epoch >= ctx.epoch - 1:
            continue
        options = await draw_options(ctx, holder_id, levels[holder_id])
        if not options:
            continue
        choice = await scholars_choose(ctx, holder_id, options)
        if row is None:
            row = ResearchFocusRow(holder_entity_id=holder_id, technique=choice, chooser=ResearchChooser.SCHOLARS, locked=[])
            ctx.session.add(row)
        row.technique, row.chooser, row.epoch = choice, ResearchChooser.SCHOLARS, ctx.epoch
        row.options = [item.value for item in options]
        tally.add("focus_chosen")
    await ctx.session.flush()


async def focus_factor(session: AsyncSession, rules: Rules, holder_id: int, technique: Technique) -> float:
    row = await session.get(ResearchFocusRow, holder_id)
    table = rules.research_depth
    if row is None:
        return table.focus_pct / PERCENT
    return table.focus_pct / PERCENT if row.technique is technique else table.unfocused_pct / PERCENT


async def captive_leaks(ctx: TickContext, tally: DepthTally) -> None:
    for cohort in await ctx.session.scalars(select(CaptiveCohortRow).where(CaptiveCohortRow.count > 0).order_by(CaptiveCohortRow.id)):
        if held(cohort.captor_entity_id) or cohort.origin_entity_id is None:
            continue
        mine = await techniques_of(ctx.session, cohort.captor_entity_id)
        for technique in sorted(await techniques_of(ctx.session, cohort.origin_entity_id) - mine):
            await add_progress(ctx, cohort.captor_entity_id, technique, ctx.rules.research_depth.captive_leak)
            tally.add("captive_leaks")


async def migrant_leaks(ctx: TickContext, tally: DepthTally) -> None:
    fled = await ctx.session.execute(
        select(BondRow.source_node_id, BondRow.target_node_id).where(BondRow.kind == BondKind.MIGRATED_TO, BondRow.epoch >= ctx.epoch - 1).order_by(BondRow.id)
    )
    for origin, host in fled.all():
        if held(host):
            continue
        mine = await techniques_of(ctx.session, host)
        for technique in sorted(await techniques_of(ctx.session, origin) - mine):
            await add_progress(ctx, host, technique, ctx.rules.research_depth.refugee_leak)
            tally.add("refugee_leaks")


async def library_leaks(ctx: TickContext, tally: DepthTally) -> None:
    atlas = await RegionAtlas.load(ctx.session)
    keepers = {item.profile.host_entity_id for item in await working(ctx.session, LIBRARIES) if item.profile.host_entity_id is not None}
    for occupation in list(await ctx.session.scalars(select(OccupationRow).order_by(OccupationRow.region_entity_id))):
        if held(occupation.occupier_entity_id):
            continue
        mine = await techniques_of(ctx.session, occupation.occupier_entity_id)
        for community in sorted(set(atlas.communities_in(occupation.region_entity_id)) & keepers):
            for technique in sorted(await techniques_of(ctx.session, community) - mine):
                await add_progress(ctx, occupation.occupier_entity_id, technique, ctx.rules.research_depth.library_leak)
                tally.add("library_leaks")


async def origin_ready(ctx: TickContext, community: EntityRow, technique: Technique) -> bool:
    table = ctx.rules.research_depth
    if not await has_technique(ctx.session, community.id, technique):
        return False
    capability = CAPABILITY_INSTITUTIONS.get(technique)
    if capability is not None and not await capable(ctx.session, community.id, capability):
        return False
    wealthy = (stat(community, "prosperity") or 0) >= table.origin_wealth
    traders = len(await trade_partners(ctx.session, community.id)) >= table.origin_trade
    scholars = await field_skill(ctx.session, community.id, TECHNIQUES[technique].branch) > 0
    return wealthy and traders and scholars


async def kin(session: AsyncSession, first: EntityRow, second: EntityRow) -> bool:
    folk_a, folk_b = await people_of(session, first), await people_of(session, second)
    if folk_a is not None and folk_b is not None and folk_a.id == folk_b.id:
        return True
    god = await patron_node(session, first.id)
    return god is not None and god == await patron_node(session, second.id)


async def institutions_round(ctx: TickContext, tally: DepthTally) -> None:
    table = ctx.rules.research_depth
    atlas = await RegionAtlas.load(ctx.session)
    communities = [item for item in await living_researchers(ctx.session) if item.entity_type in COMMUNITY_TYPES]
    present = {(row.technique, row.community_entity_id): row for row in await ctx.session.scalars(select(InstitutionRow))}
    for technique in sorted(INSTITUTIONS):
        if any(key[0] is technique for key in present):
            continue
        for community in communities:
            if not held(community.id) and await origin_ready(ctx, community, technique):
                row = InstitutionRow(technique=technique, community_entity_id=community.id, origin=True, embraced=True, since_epoch=ctx.epoch, locked=[])
                ctx.session.add(row)
                present[(technique, community.id)] = row
                tally.add("institutions_born")
                await note(
                    ctx,
                    f"{TECHNIQUES[technique].label} rose as an institution in {community.name}, where wealth, trade and scholars met.",
                    key="research.institution_born",
                    ids=[community.id],
                    kind=ChronicleKind.KNOWLEDGE,
                )
                break
    for (technique, holder_id), row in sorted(present.items(), key=lambda item: (item[0][0].value, item[0][1])):
        source = await ctx.session.get(EntityRow, holder_id)
        if source is None or source.status is not EntityStatus.CANON:
            continue
        for other in sorted(await neighbours(ctx.session, atlas, holder_id)):
            target = await ctx.session.get(EntityRow, other)
            if target is None or target.entity_type not in COMMUNITY_TYPES or (technique, other) in present or held(other):
                continue
            chance = table.spread_pct * (1 + (table.kin_spread_pct / PERCENT if await kin(ctx.session, source, target) else 0))
            if ctx.rng(f"institution.{technique.value}.{holder_id}.{other}.{ctx.epoch}").chance(round_half_up(chance)):
                present[(technique, other)] = InstitutionRow(technique=technique, community_entity_id=other, since_epoch=ctx.epoch, locked=[])
                ctx.session.add(present[(technique, other)])
                tally.add("institutions_spread")
        if not row.embraced and "embraced" not in row.locked and not held(holder_id):
            if await embrace(ctx, row):
                tally.add("institutions_embraced")
                await note(
                    ctx,
                    f"{source.name} paid to embrace {TECHNIQUES[technique].label.lower()} as an institution of its own.",
                    key="research.institution_embraced",
                    ids=[holder_id],
                    kind=ChronicleKind.KNOWLEDGE,
                )
            elif "refused_epochs" not in row.locked:
                row.refused_epochs += 1
    await ctx.session.flush()


async def embrace(ctx: TickContext, row: InstitutionRow) -> bool:
    cost = ctx.rules.research_depth.embrace_cost
    realm = await realm_of(ctx.session, row.community_entity_id)
    profile = await ctx.session.get(PolityProfileRow, realm) if realm is not None else None
    if profile is not None and profile.treasury >= cost and "treasury" not in profile.locked:
        profile.treasury -= cost
        row.embraced = True
        return True
    community = await ctx.session.get(EntityRow, row.community_entity_id)
    if profile is None and community is not None and (stat(community, "wealth") or 0) >= wealth_points(ctx.rules, cost):
        shift_stat(community, "wealth", -wealth_points(ctx.rules, cost))
        row.embraced = True
        return True
    return False


async def patronage(ctx: TickContext, tally: DepthTally) -> None:
    table = ctx.rules.research_depth
    for office in list(await ctx.session.scalars(select(OfficeRow).where(OfficeRow.kind == OfficeKind.COURT_SCHOLAR, OfficeRow.holder_entity_id.is_not(None)))):
        if held(office.polity_entity_id):
            continue
        profile = await ctx.session.get(PolityProfileRow, office.polity_entity_id)
        if profile is None:
            continue
        if "treasury" not in profile.locked:
            profile.treasury -= table.patron_stipend
        ruler = await ruler_of_realm(ctx.session, office.polity_entity_id)
        purse = await purse_of(ctx.session, ruler, ctx.epoch) if ruler is not None else None
        if purse is not None:
            bump(purse, Currency.PRESTIGE, table.patron_prestige)
        tally.add("scholars_funded")


def agreement_branch(clause: TreatyClauseRow) -> KnowledgeBranch | None:
    key = clause.params.get("branch")
    return KnowledgeBranch(key) if isinstance(key, str) and key in KnowledgeBranch._value2member_map_ else None


async def scholars_at_court(session: AsyncSession, party_id: int) -> bool:
    realm = party_id if await session.get(PolityProfileRow, party_id) is not None else await realm_of(session, party_id)
    return realm is not None and await court_scholar(session, realm) is not None


async def seal_agreements(ctx: TickContext, tally: DepthTally) -> None:
    pacts = await ctx.session.scalars(
        select(TreatyProfileRow).where(TreatyProfileRow.status == TreatyStatus.IN_FORCE, TreatyProfileRow.kind == TreatyKind.TRADE_PACT)
    )
    for profile in list(pacts):
        if held(profile.treaty_entity_id):
            continue
        kinds = set(await ctx.session.scalars(select(TreatyClauseRow.kind).where(TreatyClauseRow.treaty_entity_id == profile.treaty_entity_id)))
        if ClauseKind.RESEARCH_AGREEMENT in kinds:
            continue
        parties = [row.party_node_id for row in await parties_of(ctx.session, profile.treaty_entity_id)]
        if len(parties) >= 2 and all([await scholars_at_court(ctx.session, party) for party in parties]):
            ctx.session.add(TreatyClauseRow(treaty_entity_id=profile.treaty_entity_id, kind=ClauseKind.RESEARCH_AGREEMENT, params={}, locked=[]))
            tally.add("agreements_sealed")
    await ctx.session.flush()


async def share_agreements(ctx: TickContext, tally: DepthTally) -> None:
    table = ctx.rules.research_depth
    levels = await holder_levels(ctx.session)
    share = round_half_up(ctx.rules.tech_graph.adopt_chance * table.agreement_share_pct / PERCENT)
    clauses = await ctx.session.execute(
        select(TreatyClauseRow)
        .join(TreatyProfileRow, TreatyProfileRow.treaty_entity_id == TreatyClauseRow.treaty_entity_id)
        .where(TreatyClauseRow.kind == ClauseKind.RESEARCH_AGREEMENT, TreatyProfileRow.status == TreatyStatus.IN_FORCE)
        .order_by(TreatyClauseRow.id)
    )
    for clause in list(clauses.scalars()):
        only = agreement_branch(clause)
        parties = [row.party_node_id for row in await parties_of(ctx.session, clause.treaty_entity_id)]
        for party in parties:
            if held(party) or party not in levels:
                continue
            partners = [levels.get(other, {}) for other in parties if other != party]
            for technique in await open_techniques(ctx.session, party, levels[party]):
                branch = TECHNIQUES[technique].branch
                if only is not None and branch is not only:
                    continue
                if any(theirs.get(branch, 0) > levels[party].get(branch, 0) for theirs in partners):
                    await add_progress(ctx, party, technique, share)
                    tally.add("agreement_shares")
        clause.last_kept_epoch = ctx.epoch


async def social_change(ctx: TickContext, holder_id: int, technique: Technique) -> bool:
    shift = SOCIAL_CHANGE.get(technique)
    if shift is None or held(holder_id):
        return False
    scale = ctx.rules.research_depth.social_shift_pct / PERCENT
    for axis, delta in shift.values.items():
        row = await ctx.session.get(CultureValueRow, (holder_id, axis))
        if row is None:
            row = CultureValueRow(entity_id=holder_id, axis=axis, value=0)
            ctx.session.add(row)
        row.value = clamp_int(row.value + round_half_up(delta * scale), -PERCENT, PERCENT)
    society = await ctx.session.get(CommunitySocietyRow, holder_id)
    if society is not None and shift.classes:
        for social_class, weight in shift.classes.items():
            column = f"share_{social_class.value}"
            setattr(society, column, max(0.0, getattr(society, column) + weight * scale))
        settle_shares(society)
    return True


def settle_shares(society: CommunitySocietyRow) -> None:
    columns = [f"share_{item.value}" for item in SocialClass]
    total = sum(getattr(society, column) for column in columns)
    if total <= 0:
        return
    for column in columns:
        setattr(society, column, getattr(society, column) * PERCENT / total)


async def adopted_this_epoch(session: AsyncSession, epoch: int) -> list[tuple[int, Technique]]:
    rows = await session.execute(select(HolderTechniqueRow.holder_entity_id, HolderTechniqueRow.technique).where(HolderTechniqueRow.since_epoch == epoch))
    return [(holder, technique) for holder, technique in rows.all()]


async def research_depth(ctx: TickContext) -> dict[str, int]:
    tally = DepthTally()
    await deeds_push_research(ctx, tally)
    await captive_leaks(ctx, tally)
    await migrant_leaks(ctx, tally)
    await library_leaks(ctx, tally)
    await seal_agreements(ctx, tally)
    await share_agreements(ctx, tally)
    await institutions_round(ctx, tally)
    await patronage(ctx, tally)
    await set_focus(ctx, tally)
    return tally.counts


async def changes_of_adoption(ctx: TickContext) -> int:
    changed = 0
    for holder, technique in await adopted_this_epoch(ctx.session, ctx.epoch):
        changed += int(await social_change(ctx, holder, technique))
    return changed


async def advanced(ctx: TickContext, atlas: RegionAtlas, holder_id: int, technique: Technique) -> bool:
    row = await ctx.session.get(ResearchProgressRow, (holder_id, technique))
    if row is None:
        row = ResearchProgressRow(holder_entity_id=holder_id, technique=technique, progress=0, updated_epoch=ctx.epoch)
        ctx.session.add(row)
    gain = (
        ctx.rules.tech_graph.adopt_chance
        * await focus_factor(ctx.session, ctx.rules, holder_id, technique)
        * await catch_up(ctx, atlas, holder_id, technique)
        * await era_known(ctx, holder_id, technique)
    )
    row.progress = clamp_int(row.progress + round_half_up(gain), 0, PERCENT)
    row.updated_epoch = ctx.epoch
    if row.progress < PERCENT:
        return False
    await ctx.session.delete(row)
    return True


async def adopt_techniques(ctx: TickContext) -> int:
    table = ctx.rules.tech_graph
    levels = await holder_levels(ctx.session)
    atlas = await RegionAtlas.load(ctx.session)
    adopted = 0
    for holder_id in sorted(levels):
        if adopted >= table.cap:
            break
        known = await techniques_of(ctx.session, holder_id)
        holder = await ctx.session.get(EntityRow, holder_id)
        if holder is None or holder.status is not EntityStatus.CANON or held(holder_id):
            continue
        for technique, spec in TECHNIQUES.items():
            if technique in known or levels[holder_id].get(spec.branch, 0) < spec.level or not gate_open(spec.gate, levels[holder_id]):
                continue
            if not gate_open(BRANCH_GRAPH[spec.branch], levels[holder_id]) and spec.level > 1:
                continue
            rng = ctx.rng(f"technique.{holder_id}.{technique.value}.{ctx.epoch}")
            if not await advanced(ctx, atlas, holder_id, technique):
                continue
            secret = holder.entity_type in SECRETIVE and rng.chance(table.secret_pct)
            ctx.session.add(HolderTechniqueRow(holder_entity_id=holder_id, technique=technique, since_epoch=ctx.epoch, secret=secret))
            known.add(technique)
            adopted += 1
    return adopted
