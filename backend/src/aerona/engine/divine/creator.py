from sqlalchemy import func, select

from aerona.catalog.backfill_words import ACT_WORDS
from aerona.constants.units import PERCENT
from aerona.db.tables.agency import ActionRecordRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.cosmos import AppliedFixupRow, CreatorRow
from aerona.db.tables.creator_bonds import CreatorStandingRow
from aerona.db.tables.divine import CreatorTabooRow, WorldAttentionRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.creator import CreatorPassion
from aerona.domain.enums.entity import COMMUNITY_TYPES, EngineKind, EntityStatus, EntityType, MortalRole
from aerona.domain.enums.node import ActorKind
from aerona.domain.enums.world import Discovery
from aerona.engine.context import TickContext
from aerona.engine.gods.queries import creator_row
from aerona.engine.gods.signs import grace_sign, lonely_dream, silence, wrath_sign
from aerona.engine.primitives.numbers import clamp_percent
from aerona.engine.primitives.words import names_word

P = CreatorPassion
TABOO_FIXUP = "creator_taboos_typed"
SCHOLARS = frozenset({MortalRole.SAGE, MortalRole.SCRIBE, MortalRole.SEER, MortalRole.SCIENTIST})


async def place_of(ctx: TickContext, node_id: int) -> EntityRow | None:
    row = await ctx.session.get(EntityRow, node_id)
    if row is None:
        return None
    if row.entity_type in COMMUNITY_TYPES:
        return row
    return await ctx.session.get(EntityRow, row.location_id) if row.location_id is not None else row


async def taboo_wrath(ctx: TickContext, creator: CreatorRow) -> int:
    table = ctx.rules.creator
    struck = 0
    broken = await ctx.session.scalars(select(CreatorTabooRow).where(CreatorTabooRow.last_broken_epoch >= ctx.epoch - 1).order_by(CreatorTabooRow.act))
    for row in broken:
        if row.answered_epoch is not None and row.last_broken_epoch is not None and row.answered_epoch >= row.last_broken_epoch:
            continue
        target = await place_of(ctx, row.last_breaker_node_id) if row.last_breaker_node_id is not None else None
        if target is None or not ctx.rng(f"taboo.{row.act.value}").chance(row.severity * table.taboo_wrath_pct / PERCENT):
            continue
        if await wrath_sign(ctx, creator, target) is not None:
            row.answered_epoch = ctx.epoch
            struck += 1
    return struck


async def type_taboos(ctx: TickContext) -> int:
    if await ctx.session.get(AppliedFixupRow, TABOO_FIXUP) is not None:
        return 0
    creator = await creator_row(ctx.session)
    if creator is None:
        return 0
    added = 0
    prose = list(creator.depth.taboos) if creator.depth is not None else []
    for text in prose:
        for act, words in ACT_WORDS.items():
            if names_word(text, words) and await ctx.session.get(CreatorTabooRow, act) is None:
                ctx.session.add(
                    CreatorTabooRow(act=act, creator_node_id=creator.id, severity=ctx.rules.creator.taboo_default_severity, since_epoch=ctx.epoch, broken=0)
                )
                added += 1
    ctx.session.add(AppliedFixupRow(key=TABOO_FIXUP, result={"taboos": added}))
    await ctx.session.flush()
    return added


async def attention_row(ctx: TickContext, world_id: int) -> WorldAttentionRow:
    row = await ctx.session.get(WorldAttentionRow, world_id)
    if row is None:
        row = WorldAttentionRow(world_id=world_id, attention=ctx.rules.creator.attention_start, watched=False, epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    return row


async def acted_on(ctx: TickContext) -> dict[int, int]:
    counts: dict[int, int] = {}
    rows = await ctx.session.execute(
        select(EntityRow.world_id)
        .join(ActionRecordRow, ActionRecordRow.target_node_id == EntityRow.id)
        .where(ActionRecordRow.epoch == ctx.epoch, ActionRecordRow.actor_kind == ActorKind.CREATOR)
    )
    for (world_id,) in rows:
        counts[world_id] = counts.get(world_id, 0) + 1
    return counts


async def awe_by_world(ctx: TickContext) -> dict[int, float]:
    rows = await ctx.session.execute(
        select(EntityRow.world_id, func.avg(CreatorStandingRow.awe))
        .join(EntityRow, EntityRow.id == CreatorStandingRow.people_entity_id)
        .group_by(EntityRow.world_id)
    )
    return {world_id: float(awe) for world_id, awe in rows.all() if world_id is not None and awe is not None}


async def tend_attention(ctx: TickContext) -> int:
    table = ctx.rules.creator
    creator = await creator_row(ctx.session)
    if creator is None:
        return 0
    worlds = list(await ctx.session.scalars(select(WorldRow).where(WorldRow.discovery != Discovery.FORGOTTEN).order_by(WorldRow.id)))
    rows = [await attention_row(ctx, world.id) for world in worlds]
    watched = [row for row in rows if row.watched]
    budget = creator.mood_interest * table.attention_budget_pct / PERCENT
    share = budget / len(watched) if watched else 0.0
    acts = await acted_on(ctx)
    awe = await awe_by_world(ctx)
    for row in rows:
        if "attention" in row.locked:
            continue
        drawn = awe.get(row.world_id, 0.0) * ctx.rules.creator_bonds.awe_pull / PERCENT
        pull = (share if row.watched else 0.0) + acts.get(row.world_id, 0) * table.world_attention_per_action + drawn
        row.attention = clamp_percent(row.attention * (PERCENT - table.attention_decay_pct) / PERCENT + pull)
        row.epoch = ctx.epoch
    await ctx.session.flush()
    return len(rows)


async def far_from_eye(ctx: TickContext, world_id: int | None) -> bool:
    if world_id is None:
        return False
    row = await ctx.session.get(WorldAttentionRow, world_id)
    return row is not None and row.attention < ctx.rules.creator.far_eye_below


async def target_for(ctx: TickContext, passion: CreatorPassion) -> EntityRow | None:
    born = select(EntityRow).where(EntityRow.birth_epoch == ctx.epoch, EntityRow.status == EntityStatus.CANON)
    if passion is P.KNOWLEDGE:
        return await ctx.session.scalar(
            select(EntityRow).where(EntityRow.status == EntityStatus.CANON, EntityRow.mortal_role.in_(list(SCHOLARS))).order_by(EntityRow.id).limit(1)
        )
    if passion is P.BEAUTY:
        work = await ctx.session.scalar(born.where(EntityRow.entity_type.in_([EntityType.ARTWORK, EntityType.STRUCTURE])).order_by(EntityRow.id).limit(1))
        return await place_of(ctx, work.id) if work is not None else None
    if passion in {P.WAR, P.CHAOS}:
        battle = await ctx.session.scalar(born.where(EntityRow.engine_kind.in_([EngineKind.BATTLE, EngineKind.SIEGE])).order_by(EntityRow.id).limit(1))
        return await place_of(ctx, battle.id) if battle is not None else None
    if passion is P.MERCY:
        plague = await ctx.session.scalar(born.where(EntityRow.engine_kind == EngineKind.PLAGUE).order_by(EntityRow.id).limit(1))
        return await place_of(ctx, plague.id) if plague is not None else None
    if passion in {P.CREATION, P.ORDER}:
        return await ctx.session.scalar(born.where(EntityRow.entity_type.in_(list(COMMUNITY_TYPES))).order_by(EntityRow.id).limit(1))
    return None


async def passion_sign(ctx: TickContext, creator: CreatorRow) -> CreatorPassion | None:
    table = ctx.rules.creator
    rng = ctx.rng("passion_sign")
    if not creator.passions or not rng.chance(table.passion_sign_chance):
        return None
    passion = rng.pick(list(creator.passions))
    if passion is P.SILENCE:
        await silence(ctx, creator, True)
        return passion
    target = await target_for(ctx, passion)
    if target is None:
        return None
    if passion is P.KNOWLEDGE:
        await lonely_dream(ctx, creator, target)
    elif passion is P.CHAOS:
        await wrath_sign(ctx, creator, target)
    else:
        await grace_sign(ctx, creator, target)
    return passion


async def autonomy(ctx: TickContext, son: SonRow) -> int:
    return ctx.rules.creator.far_eye_rebel_pct if await far_from_eye(ctx, son.current_world_id) else 0
