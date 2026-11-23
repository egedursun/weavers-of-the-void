from sqlalchemy import select

from aerona.catalog.discovery import ACCIDENT_BRANCHES, DANGEROUS_BRANCHES, DANGEROUS_TECHNIQUES
from aerona.catalog.life.lore import (
    ACCIDENTS_RESEARCH_INCIDENTS,
    HARMS,
    SCHOLARLY,
    STRIKE_RESEARCH_INCIDENTS,
    STRIKE_RESEARCH_INCIDENTS_2,
    STRIKE_RESEARCH_INCIDENTS_3,
)
from aerona.catalog.techniques import TECHNIQUES
from aerona.constants.units import PERCENT
from aerona.db.record_context import Term
from aerona.db.tables.culture import HolderLevelRow, HolderTechniqueRow, ResearchProgressRow
from aerona.db.tables.discovery import ResearchIncidentRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.military import SpyNetworkRow
from aerona.db.tables.mind import SkillRow
from aerona.db.write_guard import held
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.discovery import ResearchIncident
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus, EntityType
from aerona.domain.enums.mind import ActKind, MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.society import KnowledgeBranch
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.disease.control import loose
from aerona.engine.ecology.control import commonest_species, spawn_beast
from aerona.engine.interconnect.flows import FlowCategory, flowing
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.lore.learning import realm_of
from aerona.engine.lore.research import has_technique
from aerona.engine.lore.research_depth import add_progress, neighbours
from aerona.engine.lore.rites import phenomenon
from aerona.engine.mind.ethics import BAD, culture_of, ethics_of
from aerona.engine.polity.repute import shift_infamy
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import shift_stat, stat
from aerona.engine.recording.record import record as record_incident
from aerona.engine.renown.currencies import ruler_of_realm
from aerona.engine.services.community_relations import change_relation

DANGEROUS = frozenset(DANGEROUS_TECHNIQUES)


async def scholars_of(ctx: TickContext, holder_id: int) -> list[EntityRow]:
    rows = await ctx.session.scalars(
        select(EntityRow)
        .join(SkillRow, SkillRow.holder_node_id == EntityRow.id)
        .where(
            await present_among(ctx.session, [holder_id]),
            EntityRow.entity_type == EntityType.MORTAL,
            EntityRow.status == EntityStatus.CANON,
            SkillRow.skill.in_(SCHOLARLY),
        )
        .order_by(SkillRow.level.desc(), EntityRow.id)
    )
    found: list[EntityRow] = []
    for mortal in rows:
        if mortal not in found and not held(mortal.id):
            found.append(mortal)
    return found[: ctx.rules.discovery.incident_victims]


async def plague_site(ctx: TickContext, holder: EntityRow) -> EntityRow | None:
    if holder.entity_type in COMMUNITY_TYPES:
        return holder
    place = await ctx.session.get(EntityRow, holder.location_id) if holder.location_id is not None else None
    if place is None or place.status is not EntityStatus.CANON or held(place.id):
        return None
    return place if place.entity_type in {EntityType.REGION, *COMMUNITY_TYPES} else None


async def strike(
    ctx: TickContext, holder: EntityRow, kind: ResearchIncident, *, technique: Technique | None = None, branch: KnowledgeBranch | None = None
) -> ResearchIncidentRow:
    table = ctx.rules.discovery
    rng = ctx.rng(f"research.incident.{holder.id}.{kind.value}.{ctx.epoch}")
    severity = clamp_int(round_half_up(table.incident_severity * (0.5 + rng.random())), 1, PERCENT)
    row = ResearchIncidentRow(holder_entity_id=holder.id, kind=kind, technique=technique, branch=branch, severity=severity, dead=0, epoch=ctx.epoch)
    ctx.session.add(row)
    atlas = await RegionAtlas.load(ctx.session)
    region_id = atlas.top_region(holder.id)
    region = await ctx.session.get(EntityRow, region_id) if region_id is not None else None
    if kind in STRIKE_RESEARCH_INCIDENTS:
        shift_stat(holder, "prosperity", -round_half_up(table.incident_prosperity * severity / PERCENT))
    if kind in STRIKE_RESEARCH_INCIDENTS_2:
        people = stat(holder, "population") or 0
        row.dead = round_half_up(people * table.incident_dead_pct / PERCENT * severity / PERCENT)
        if row.dead:
            with flowing(FlowCategory.DISASTER):
                shift_stat(holder, "population", -row.dead)
    if kind in HARMS:
        cause, damage = HARMS[kind]
        for scholar in await scholars_of(ctx, holder.id):
            harm = Harm(table.incident_hp * severity / PERCENT, cause, "died of what the work let loose", damage_type=damage)
            await apply_hits(ctx, scholar, harm, lethal=False)
    await fortune_follows(ctx, holder, kind, technique)
    if kind is ResearchIncident.LEAK and technique is not None:
        for other in sorted(await neighbours(ctx.session, atlas, holder.id))[:1]:
            if not held(other) and not await has_technique(ctx.session, other, technique):
                await add_progress(ctx, other, technique, table.leak_progress)
    if kind in STRIKE_RESEARCH_INCIDENTS_3 and region is not None:
        species = await commonest_species(ctx, region.id)
        if species is not None and kind is ResearchIncident.RELEASED_BEAST:
            await spawn_beast(ctx, species)
        shift_stat(region, "danger", round_half_up(table.incident_danger * severity / PERCENT))
    site = await plague_site(ctx, holder) if kind is ResearchIncident.PLAGUE else None
    if site is not None:
        await loose(ctx, site.id, disease_id=None, severity=severity, son_id=None)
    if kind is ResearchIncident.BACKLASH and region is not None:
        await phenomenon(ctx, region)
    await record_incident(
        ctx,
        f"discovery.incident_{kind.value}",
        roles={IncidentRole.SUBJECT: holder.id},
        facts={
            "incident": kind,
            "severity": severity,
            "dead": row.dead,
            **({"technique": technique} if technique is not None else {}),
            **({"branch": branch} if branch is not None else {}),
        },
        place=holder.id,
        terms=[Term("rules.discovery.incident_severity", table.incident_severity)],
    )
    return row


async def condemn(ctx: TickContext, holder: EntityRow, act: ActKind) -> int:
    table = ctx.rules.discovery
    atlas = await RegionAtlas.load(ctx.session)
    angered = 0
    for other_id in sorted(await neighbours(ctx.session, atlas, holder.id)):
        other = await ctx.session.get(EntityRow, other_id)
        if other is None or other.entity_type not in COMMUNITY_TYPES or other.status is not EntityStatus.CANON:
            continue
        culture = await culture_of(ctx.session, other.id)
        stance = (await ethics_of(ctx.session, culture.id)).get(act) if culture is not None else None
        if stance is not None and stance.stance in BAD:
            await change_relation(ctx, other.id, holder.id, -table.ethics_relation, MemoryKind.ILL_WILL, note="dabbles in what it holds shameful")
            angered += 1
    realm = await realm_of(ctx.session, holder.id)
    ruler = await ruler_of_realm(ctx.session, realm) if realm is not None else None
    if angered and ruler is not None:
        await shift_infamy(ctx, ruler, table.ethics_infamy)
    return angered


async def learned_dangers(ctx: TickContext) -> int:
    table = ctx.rules.discovery
    struck = 0
    fresh = await ctx.session.scalars(
        select(HolderTechniqueRow).where(HolderTechniqueRow.since_epoch == ctx.epoch, HolderTechniqueRow.technique.in_(list(DANGEROUS)))
    )
    for row in list(fresh):
        holder = await ctx.session.get(EntityRow, row.holder_entity_id)
        if holder is None or holder.status is not EntityStatus.CANON or held(holder.id):
            continue
        spec = DANGEROUS_TECHNIQUES[row.technique]
        await condemn(ctx, holder, spec.act)
        rng = ctx.rng(f"research.discovery_incident.{holder.id}.{row.technique.value}.{ctx.epoch}")
        if rng.chance(table.discovery_incident_pct):
            await strike(ctx, holder, rng.pick(list(spec.incidents)), technique=row.technique)
            struck += 1
    return struck


async def dangerous_arts(ctx: TickContext) -> int:
    table = ctx.rules.discovery
    struck = 0
    holders = await ctx.session.execute(
        select(HolderTechniqueRow.holder_entity_id, HolderTechniqueRow.technique).where(HolderTechniqueRow.technique.in_(list(DANGEROUS)))
    )
    arts: list[tuple[int, Technique | None, KnowledgeBranch | None, tuple[ResearchIncident, ...]]] = [
        (holder, technique, None, DANGEROUS_TECHNIQUES[technique].incidents) for holder, technique in holders.all()
    ]
    for field, danger in DANGEROUS_BRANCHES.items():
        rows = await ctx.session.scalars(select(HolderLevelRow).where(HolderLevelRow.branch == field, HolderLevelRow.level >= danger.level))
        arts.extend((row.holder_entity_id, None, field, danger.incidents) for row in rows)
    for holder_id, technique, branch, incidents in sorted(arts, key=lambda item: (item[0], str(item[1] or ""), str(item[2] or ""))):
        holder = await ctx.session.get(EntityRow, holder_id)
        if holder is None or holder.status is not EntityStatus.CANON or held(holder.id):
            continue
        key = technique.value if technique is not None else (branch.value if branch is not None else "art")
        rng = ctx.rng(f"research.dangerous_art.{holder.id}.{key}.{ctx.epoch}")
        if rng.chance(table.use_incident_pct):
            await strike(ctx, holder, rng.pick(list(incidents)), technique=technique, branch=branch)
            struck += 1
    return struck


async def fortune_follows(ctx: TickContext, holder: EntityRow, kind: ResearchIncident, technique: Technique | None) -> None:
    table = ctx.rules.discovery
    if technique is None:
        return
    if kind is ResearchIncident.STOLEN:
        thief = await thief_of(ctx, holder.id)
        if thief is not None and not await has_technique(ctx.session, thief, technique):
            await add_progress(ctx, thief, technique, table.stolen_progress)
    if kind is ResearchIncident.CHANCE_FIND:
        await add_progress(ctx, holder.id, technique, table.chance_find_progress)


async def thief_of(ctx: TickContext, holder_id: int) -> int | None:
    owners = await ctx.session.scalars(
        select(SpyNetworkRow.owner_entity_id).where(SpyNetworkRow.target_entity_id == holder_id).order_by(SpyNetworkRow.owner_entity_id)
    )
    return next((owner for owner in owners if owner != holder_id and not held(owner)), None)


async def turns_of_fortune(ctx: TickContext, holder: EntityRow, technique: Technique, branch: KnowledgeBranch) -> int:
    table = ctx.rules.discovery
    rng = ctx.rng(f"research.fortune.{holder.id}.{technique.value}.{ctx.epoch}")
    if rng.chance(table.chance_find_pct):
        await strike(ctx, holder, ResearchIncident.CHANCE_FIND, technique=technique, branch=branch)
        return 1
    if rng.chance(table.stolen_pct) and await thief_of(ctx, holder.id) is not None:
        await strike(ctx, holder, ResearchIncident.STOLEN, technique=technique, branch=branch)
        return 1
    return 0


async def accidents(ctx: TickContext) -> int:
    table = ctx.rules.discovery
    struck = 0
    active = await ctx.session.scalars(
        select(ResearchProgressRow).where(ResearchProgressRow.updated_epoch == ctx.epoch).order_by(ResearchProgressRow.holder_entity_id)
    )
    for row in list(active):
        branch = TECHNIQUES[row.technique].branch
        incidents = ACCIDENT_BRANCHES.get(branch) or (ACCIDENTS_RESEARCH_INCIDENTS if row.technique is Technique.ALCHEMY else ())
        holder = await ctx.session.get(EntityRow, row.holder_entity_id)
        if holder is None or holder.status is not EntityStatus.CANON or held(holder.id):
            continue
        struck += await turns_of_fortune(ctx, holder, row.technique, branch)
        if not incidents:
            continue
        rng = ctx.rng(f"research.accident.{holder.id}.{row.technique.value}.{ctx.epoch}")
        if rng.chance(table.accident_pct):
            await strike(ctx, holder, rng.pick(list(incidents)), technique=row.technique, branch=branch)
            struck += 1
    return struck


async def dangers(ctx: TickContext) -> dict[str, int]:
    return {"dangers_on_learning": await learned_dangers(ctx), "dangerous_arts": await dangerous_arts(ctx), "accidents": await accidents(ctx)}
