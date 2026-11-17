from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.techniques import TECHNIQUES
from aerona.constants.units import PERCENT
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.culture import HolderTechniqueRow, InstitutionRow
from aerona.db.tables.discovery import EraDeedRow, GreatPersonRow, PolityEraRow, WorldEraRow
from aerona.db.tables.entities import EntityFlagRow, EntityRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.warfare import WarRow
from aerona.db.write_guard import held
from aerona.domain.enums.discovery import AgeKind, EraDeed
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.war import WarStatus
from aerona.engine.context import TickContext
from aerona.engine.lore.learning import realm_of
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.recording.record import record as record_incident
from aerona.rules.registry import Rules

SCORE_FLOOR, SCORE_CEILING = -1000, 1000


async def polity_for(session: AsyncSession, node_id: int | None) -> int | None:
    if node_id is None:
        return None
    entity = await session.get(EntityRow, node_id)
    if entity is not None and entity.entity_type is EntityType.POLITY:
        return entity.id
    return await realm_of(session, node_id)


async def record_deed(ctx: TickContext, polity_id: int | None, deed: EraDeed, points: int, subject_id: int | None = None) -> bool:
    if polity_id is None or held(polity_id):
        return False
    if subject_id is not None:
        seen = await ctx.session.scalar(
            select(EraDeedRow.id).where(EraDeedRow.polity_entity_id == polity_id, EraDeedRow.deed == deed, EraDeedRow.subject_node_id == subject_id).limit(1)
        )
        if seen is not None:
            return False
    ctx.session.add(EraDeedRow(polity_entity_id=polity_id, deed=deed, points=points, epoch=ctx.epoch, subject_node_id=subject_id))
    row = await era_of(ctx, polity_id)
    if "score" not in row.locked:
        row.score = clamp_int(row.score + points, SCORE_FLOOR, SCORE_CEILING)
    return True


async def era_of(ctx: TickContext, polity_id: int) -> PolityEraRow:
    row = await ctx.session.get(PolityEraRow, polity_id)
    if row is None:
        row = PolityEraRow(polity_entity_id=polity_id, score=0, age=AgeKind.NORMAL, since_epoch=ctx.epoch, lowest=0, locked=[])
        ctx.session.add(row)
        await ctx.session.flush()
    return row


async def firsts(ctx: TickContext) -> int:
    fresh = list(await ctx.session.scalars(select(HolderTechniqueRow).where(HolderTechniqueRow.since_epoch == ctx.epoch)))
    found = 0
    for row in fresh:
        holder = await ctx.session.get(EntityRow, row.holder_entity_id)
        if holder is None:
            continue
        earlier = await ctx.session.scalar(
            select(HolderTechniqueRow.holder_entity_id)
            .join(EntityRow, EntityRow.id == HolderTechniqueRow.holder_entity_id)
            .where(
                HolderTechniqueRow.technique == row.technique,
                HolderTechniqueRow.holder_entity_id != holder.id,
                EntityRow.world_id == holder.world_id,
                HolderTechniqueRow.since_epoch < ctx.epoch,
            )
            .limit(1)
        )
        if earlier is None:
            polity = await polity_for(ctx.session, holder.id)
            found += int(await record_deed(ctx, polity, EraDeed.FIRST_TECHNIQUE, ctx.rules.discovery.first_points, holder.id))
    return found


async def institutions_born(ctx: TickContext) -> int:
    born = await ctx.session.scalars(select(InstitutionRow).where(InstitutionRow.origin.is_(True), InstitutionRow.since_epoch >= ctx.epoch - 1))
    found = 0
    for row in list(born):
        polity = await polity_for(ctx.session, row.community_entity_id)
        found += int(await record_deed(ctx, polity, EraDeed.FIRST_INSTITUTION, ctx.rules.discovery.institution_points, row.community_entity_id))
    return found


async def wars_ended(ctx: TickContext) -> int:
    table = ctx.rules.discovery
    ended = await ctx.session.scalars(select(WarRow).where(WarRow.status == WarStatus.ENDED, WarRow.ended_epoch >= ctx.epoch - 1))
    found = 0
    for war in list(ended):
        found += int(
            await record_deed(ctx, await polity_for(ctx.session, war.victor_entity_id), EraDeed.GREAT_VICTORY, table.victory_points, war.event_entity_id)
        )
        found += int(await record_deed(ctx, await polity_for(ctx.session, war.loser_entity_id), EraDeed.DEFEAT, -table.defeat_points, war.event_entity_id))
    return found


async def wonders_raised(ctx: TickContext) -> int:
    flags = await ctx.session.scalars(select(EntityFlagRow).where(EntityFlagRow.flag == EntityFlag.WONDER, EntityFlagRow.epoch >= ctx.epoch - 1))
    found = 0
    for flag in list(flags):
        work = await ctx.session.get(EntityRow, flag.entity_id)
        if work is not None:
            found += int(await record_deed(ctx, await polity_for(ctx.session, work.location_id), EraDeed.WONDER, ctx.rules.discovery.wonder_points, work.id))
    return found


async def great_risen(ctx: TickContext) -> int:
    found = 0
    for great in list(await ctx.session.scalars(select(GreatPersonRow).where(GreatPersonRow.promoted_epoch >= ctx.epoch - 1))):
        polity = await polity_for(ctx.session, great.holder_entity_id)
        found += int(await record_deed(ctx, polity, EraDeed.GREAT_PERSON, ctx.rules.discovery.great_person_points, great.mortal_entity_id))
    return found


async def famines(ctx: TickContext) -> int:
    starving = await ctx.session.scalars(select(CommunitySocietyRow.entity_id).where(CommunitySocietyRow.stock_food <= 0))
    by_polity: dict[int, int] = defaultdict(int)
    for community in list(starving):
        polity = await realm_of(ctx.session, community)
        if polity is not None:
            by_polity[polity] += 1
    for polity, count in sorted(by_polity.items()):
        await record_deed(ctx, polity, EraDeed.FAMINE, -ctx.rules.discovery.famine_points * count)
    return len(by_polity)


def next_age(row: PolityEraRow, rules: Rules) -> AgeKind:
    table = rules.discovery
    if row.age is AgeKind.DARK and row.score - row.lowest >= table.heroic_rise:
        return AgeKind.HEROIC
    if row.score <= table.dark_at:
        return AgeKind.DARK
    if row.age is AgeKind.HEROIC and row.score < table.golden_at:
        return AgeKind.HEROIC
    return AgeKind.GOLDEN if row.score >= table.golden_at else AgeKind.NORMAL


async def settle_ages(ctx: TickContext) -> int:
    table = ctx.rules.discovery
    changed = 0
    for row in list(await ctx.session.scalars(select(PolityEraRow).order_by(PolityEraRow.polity_entity_id))):
        polity = await ctx.session.get(EntityRow, row.polity_entity_id)
        if polity is None or polity.status is not EntityStatus.CANON or held(polity.id):
            continue
        if "score" not in row.locked and row.score:
            fade = min(abs(row.score), table.era_decay)
            row.score -= fade if row.score > 0 else -fade
        if row.age is AgeKind.DARK and "lowest" not in row.locked:
            row.lowest = min(row.lowest, row.score)
        if "age" not in row.locked:
            age = next_age(row, ctx.rules)
            if age is not row.age:
                if age is AgeKind.DARK and "lowest" not in row.locked:
                    row.lowest = row.score
                row.age, row.since_epoch = age, ctx.epoch
                changed += 1
                await record_incident(ctx, f"discovery.age_{age.value}", roles={IncidentRole.SUBJECT: polity.id}, facts={"age": age, "score": row.score})
        profile = await ctx.session.get(PolityProfileRow, polity.id)
        if profile is not None and "stability" not in profile.locked:
            if row.age in {AgeKind.GOLDEN, AgeKind.HEROIC}:
                profile.stability = clamp_int(profile.stability + table.golden_stability, 0, PERCENT)
            elif row.age is AgeKind.DARK:
                profile.stability = clamp_int(profile.stability - table.dark_stability, 0, PERCENT)
    return changed


async def era_factor(session: AsyncSession, rules: Rules, community_id: int) -> float:
    realm = await realm_of(session, community_id)
    row = await session.get(PolityEraRow, realm) if realm is not None else None
    if row is None:
        return 1.0
    table = rules.discovery
    shifts = {AgeKind.GOLDEN: table.golden_research_pct, AgeKind.HEROIC: table.heroic_research_pct, AgeKind.DARK: -table.dark_research_pct}
    return 1 + shifts.get(row.age, 0) / PERCENT


async def leaders_share(session: AsyncSession, world_id: int, era: int, leaders: int) -> float:
    holders = select(EntityRow.id).where(EntityRow.world_id == world_id, EntityRow.status == EntityStatus.CANON)
    known: dict[int, set[str]] = defaultdict(set)
    rows = await session.execute(
        select(HolderTechniqueRow.holder_entity_id, HolderTechniqueRow.technique).where(HolderTechniqueRow.holder_entity_id.in_(holders))
    )
    for holder, technique in rows.all():
        known[holder].add(technique.value)
    ranked = sorted(known.items(), key=lambda item: (-len(item[1]), item[0]))[:leaders]
    targets = {spec.technique.value for spec in TECHNIQUES.values() if spec.level == era}
    if not targets or not ranked:
        return 0.0
    return max(len(targets & techniques) / len(targets) for _, techniques in ranked)


async def advance_worlds(ctx: TickContext) -> int:
    table = ctx.rules.discovery
    top = max(spec.level for spec in TECHNIQUES.values())
    advanced = 0
    for world in list(await ctx.session.scalars(select(WorldRow).order_by(WorldRow.id))):
        if held(world.id):
            continue
        row = await ctx.session.get(WorldEraRow, world.id)
        if row is None:
            row = WorldEraRow(world_id=world.id, era=1, since_epoch=ctx.epoch, locked=[])
            ctx.session.add(row)
        if "era" in row.locked or row.era >= top:
            continue
        if await leaders_share(ctx.session, world.id, row.era + 1, table.era_leaders) * PERCENT >= table.era_advance_pct:
            row.era, row.since_epoch = row.era + 1, ctx.epoch
            advanced += 1
            await record_incident(ctx, "discovery.world_era", roles={IncidentRole.SUBJECT: world.id}, facts={"era": row.era}, world_id=world.id)
    await ctx.session.flush()
    return advanced


async def eras(ctx: TickContext) -> dict[str, int]:
    deeds = await firsts(ctx) + await institutions_born(ctx) + await wars_ended(ctx) + await wonders_raised(ctx) + await great_risen(ctx) + await famines(ctx)
    await ctx.session.flush()
    return {"era_deeds": deeds, "ages_changed": await settle_ages(ctx), "worlds_advanced": await advance_worlds(ctx)}
