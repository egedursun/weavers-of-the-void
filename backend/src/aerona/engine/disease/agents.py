from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.disease_agents import AGENT_OF_VECTOR, AGENTS
from aerona.constants.units import PERCENT
from aerona.db.tables.culture import HolderLevelRow
from aerona.db.tables.disease import DiseaseProfileRow, EndemicDiseaseRow, OutbreakRow
from aerona.db.tables.disease_agents import DiseaseAgentRow
from aerona.db.tables.ecology import SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.write_guard import held
from aerona.domain.enums.disease import OutbreakStatus
from aerona.domain.enums.disease_agents import CureClass, DiseaseAgent
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.environment import RiverClass
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.society import KnowledgeBranch
from aerona.engine.context import TickContext
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.stats import shift_stat, stat_or
from aerona.engine.recording.record import record
from aerona.engine.recording.terms import explaining_alone, term
from aerona.rules.registry import Rules

COMMUNITIES = frozenset({EntityType.PEOPLE, EntityType.SETTLEMENT})
HERB_LEVEL = 2
MEDICINE_ORDER = (CureClass.ANTIMICROBIAL, CureClass.ANTIPARASITIC, CureClass.ANTITOXIN, CureClass.NUTRITIONAL, CureClass.HERBAL, CureClass.REST_AND_CARE)
OVERUSED = frozenset({CureClass.ANTIMICROBIAL, CureClass.ANTIPARASITIC, CureClass.ANTITOXIN})


@dataclass
class AgentTally:
    typed: int = 0
    right: int = 0
    wrong: int = 0
    resistant: int = 0
    identified: int = 0
    reservoirs: int = 0


def mutation_of(rules: Rules, agent: DiseaseAgent) -> int | None:
    table = rules.disease
    rates = {
        DiseaseAgent.VIRUS: table.mutation_virus_pct,
        DiseaseAgent.BACTERIUM: table.mutation_bacterium_pct,
        DiseaseAgent.FUNGUS: table.mutation_fungus_pct,
        DiseaseAgent.PARASITE: table.mutation_parasite_pct,
        DiseaseAgent.PRION: table.mutation_prion_pct,
    }
    return rates.get(agent)


async def agent_of(ctx: TickContext, profile: DiseaseProfileRow, tally: AgentTally) -> DiseaseAgentRow:
    row = await ctx.session.get(DiseaseAgentRow, profile.disease_entity_id)
    if row is not None:
        return row
    agent = DiseaseAgent.MADE if profile.designed_line_id is not None else AGENT_OF_VECTOR[profile.vector]
    spec = AGENTS[agent]
    row = DiseaseAgentRow(
        disease_entity_id=profile.disease_entity_id,
        agent=agent,
        survival_water=spec.water,
        survival_soil=spec.soil,
        survival_objects=spec.objects,
        survival_cold=spec.cold,
        reservoir_species_id=profile.host_species_id,
        locked=[],
    )
    ctx.session.add(row)
    rate = mutation_of(ctx.rules, agent)
    if rate is not None and "mutation_rate" not in profile.locked:
        with explaining_alone():
            term("disease.agent_mutation", rate - profile.mutation_rate, source_node_id=profile.disease_entity_id)
            profile.mutation_rate = rate
    tally.typed += 1
    return row


async def medicine_of(ctx: TickContext, community_id: int) -> int:
    level = await ctx.session.get(HolderLevelRow, (community_id, KnowledgeBranch.MEDICINE))
    return level.level if level is not None else 0


def cure_tried(rules: Rules, community: EntityRow, medicine: int, row: DiseaseAgentRow) -> CureClass:
    if stat_or(community, "piety", 0) >= rules.disease.rite_piety:
        return CureClass.RITE
    if row.identified and medicine >= rules.disease.identify_level:
        known = AGENTS[row.agent].cures
        return next((cure for cure in MEDICINE_ORDER if cure in known), CureClass.REST_AND_CARE)
    if medicine >= rules.disease.identify_level:
        return CureClass.ANTIMICROBIAL
    return CureClass.HERBAL if medicine >= HERB_LEVEL else CureClass.REST_AND_CARE


async def largest_in(ctx: TickContext, atlas: RegionAtlas, region_id: int) -> EntityRow | None:
    found: list[EntityRow] = []
    for community_id in atlas.communities_in(region_id):
        community = await ctx.session.get(EntityRow, community_id)
        if community is not None and community.entity_type in COMMUNITIES and community.status is EntityStatus.CANON and not held(community.id):
            found.append(community)
    return max(found, key=lambda each: (stat_or(each, "population", 0), -each.id), default=None)


async def overuse(ctx: TickContext, profile: DiseaseProfileRow, row: DiseaseAgentRow, cure: CureClass, tally: AgentTally) -> None:
    table = ctx.rules.disease
    if cure not in OVERUSED or "overuse" in row.locked:
        return
    row.overused_cure = cure
    row.overuse = clamp_int(row.overuse + table.overuse_per_use, 0, PERCENT)
    if row.overuse < PERCENT or "resistance" in profile.locked:
        return
    row.overuse = 0
    with explaining_alone():
        term("disease.overuse", table.resistance_per_overuse, source_node_id=profile.disease_entity_id)
        profile.resistance = clamp_int(profile.resistance + table.resistance_per_overuse, 0, PERCENT)
    tally.resistant += 1
    await record(
        ctx, "disease.resistance_rose", roles={IncidentRole.SUBJECT: profile.disease_entity_id}, facts={"cure": cure, "resistance": profile.resistance}
    )


async def treat(ctx: TickContext, outbreak: OutbreakRow, pair: tuple[DiseaseProfileRow, DiseaseAgentRow], atlas: RegionAtlas, tally: AgentTally) -> None:
    table = ctx.rules.disease
    profile, row = pair
    community = await largest_in(ctx, atlas, outbreak.region_entity_id)
    if community is None:
        return
    medicine = await medicine_of(ctx, community.id)
    if not row.identified and medicine >= table.identify_level and "identified" not in row.locked:
        row.identified = True
        tally.identified += 1
        await record(
            ctx,
            "disease.agent_identified",
            roles={IncidentRole.SUBJECT: profile.disease_entity_id, IncidentRole.ACTOR: community.id},
            facts={"agent": row.agent},
        )
    cure = cure_tried(ctx.rules, community, medicine, row)
    roles = {IncidentRole.SUBJECT: profile.disease_entity_id, IncidentRole.ACTOR: community.id}
    if cure in AGENTS[row.agent].cures:
        tally.right += 1
        if "severity" not in outbreak.locked:
            with explaining_alone():
                term("disease.right_cure", -table.right_cure_cut, source_node_id=community.id)
                outbreak.severity = clamp_int(outbreak.severity - table.right_cure_cut, 0, PERCENT)
        await record(ctx, "disease.right_cure", roles=roles, facts={"cure": cure, "severity": outbreak.severity}, place=outbreak.region_entity_id)
    else:
        tally.wrong += 1
        with explaining_alone():
            term("disease.wrong_cure", -table.wrong_cure_trust_loss, source_node_id=community.id)
            shift_stat(community, "piety", -table.wrong_cure_trust_loss, low=0, high=PERCENT)
        await record(ctx, "disease.wrong_cure", roles=roles, facts={"cure": cure, "agent": row.agent}, place=outbreak.region_entity_id)
    await overuse(ctx, profile, row, cure, tally)


async def linger(ctx: TickContext, outbreak: OutbreakRow, row: DiseaseAgentRow, atlas: RegionAtlas, tally: AgentTally) -> None:
    table = ctx.rules.disease
    region = outbreak.region_entity_id
    if held(region) or await ctx.session.get(EndemicDiseaseRow, (region, row.disease_entity_id)) is not None:
        return
    reservoir = row.reservoir_species_id is not None and await ctx.session.get(SpeciesRangeRow, (row.reservoir_species_id, region)) is not None
    land = await ctx.session.get(RegionEnvironmentRow, region)
    by_water = land is not None and land.river_class is not RiverClass.NONE and row.survival_water >= table.survival_water_pct
    by_objects = bool(atlas.communities_in(region)) and row.survival_objects >= table.survival_object_pct
    if not reservoir and row.survival_soil < table.survival_soil_pct and not by_water and not by_objects:
        return
    ctx.session.add(EndemicDiseaseRow(region_entity_id=region, disease_entity_id=row.disease_entity_id, load=table.linger_load, since_epoch=ctx.epoch))
    if reservoir:
        tally.reservoirs += 1
        await record(
            ctx,
            "disease.reservoir_found",
            roles={IncidentRole.SUBJECT: row.disease_entity_id, IncidentRole.PLACE: region},
            facts={"load": table.linger_load},
            place=region,
        )


async def keep_agents(ctx: TickContext, tally: AgentTally) -> None:
    atlas = await RegionAtlas.load(ctx.session)
    active = {
        outbreak.disease_entity_id: outbreak
        for outbreak in await ctx.session.scalars(select(OutbreakRow).where(OutbreakRow.status == OutbreakStatus.ACTIVE).order_by(OutbreakRow.id.desc()))
    }
    for profile in list(await ctx.session.scalars(select(DiseaseProfileRow).order_by(DiseaseProfileRow.disease_entity_id))):
        if held(profile.disease_entity_id):
            continue
        row = await agent_of(ctx, profile, tally)
        outbreak = active.get(profile.disease_entity_id)
        if outbreak is None:
            if "overuse" not in row.locked:
                row.overuse = clamp_int(row.overuse - ctx.rules.disease.overuse_fade, 0, PERCENT)
            if row.overuse == 0 and profile.resistance > 0 and "resistance" not in profile.locked:
                with explaining_alone():
                    term("disease.unused", -ctx.rules.disease.resistance_fade, source_node_id=profile.disease_entity_id)
                    profile.resistance = clamp_int(profile.resistance - ctx.rules.disease.resistance_fade, 0, PERCENT)
            continue
        if held(outbreak.region_entity_id):
            continue
        await treat(ctx, outbreak, (profile, row), atlas, tally)
        await linger(ctx, outbreak, row, atlas, tally)
    await ctx.session.flush()


async def works_on(ctx: TickContext, disease_id: int, cure: CureClass) -> bool | None:
    row = await ctx.session.get(DiseaseAgentRow, disease_id)
    return cure in AGENTS[row.agent].cures if row is not None else None


async def apply_cure(ctx: TickContext, community: EntityRow, disease_id: int, cure: CureClass) -> bool | None:
    table = ctx.rules.disease
    works = await works_on(ctx, disease_id, cure)
    if works is None:
        return None
    atlas = await RegionAtlas.load(ctx.session)
    region = atlas.top_region(community.id)
    outbreak = (
        await ctx.session.scalar(
            select(OutbreakRow)
            .where(OutbreakRow.disease_entity_id == disease_id, OutbreakRow.region_entity_id == region, OutbreakRow.status == OutbreakStatus.ACTIVE)
            .order_by(OutbreakRow.id)
            .limit(1)
        )
        if region is not None
        else None
    )
    roles = {IncidentRole.SUBJECT: disease_id, IncidentRole.ACTOR: community.id}
    if works:
        if outbreak is not None and "severity" not in outbreak.locked and not held(outbreak.region_entity_id):
            with explaining_alone():
                term("disease.right_cure", -table.right_cure_cut, source_node_id=community.id)
                outbreak.severity = clamp_int(outbreak.severity - table.right_cure_cut, 0, PERCENT)
        await record(ctx, "disease.right_cure", roles=roles, facts={"cure": cure, "severity": outbreak.severity if outbreak is not None else 0})
        return True
    if not held(community.id):
        with explaining_alone():
            term("disease.wrong_cure", -table.wrong_cure_trust_loss, source_node_id=community.id)
            shift_stat(community, "piety", -table.wrong_cure_trust_loss, low=0, high=PERCENT)
    row = await ctx.session.get(DiseaseAgentRow, disease_id)
    await record(ctx, "disease.wrong_cure", roles=roles, facts={"cure": cure, "agent": row.agent if row is not None else DiseaseAgent.UNKNOWN})
    return False
