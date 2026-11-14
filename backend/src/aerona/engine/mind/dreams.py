from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.thoughts import EMOTIONS, NEED_READINGS, NEEDS, READINGS
from aerona.constants.units import PERCENT
from aerona.db.repositories.entities import EntityRepository
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lore import MessageRow
from aerona.db.tables.mind import DreamRow, MemoryRow, SkillRow, ThoughtRow
from aerona.db.tables.routes import RouteRow
from aerona.db.write_guard import write_blocked
from aerona.domain.enums.agent import MessageIntent
from aerona.domain.enums.body import ConditionKind, HarmCause
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.divine import DomainHook
from aerona.domain.enums.entity import EntityStatus, EntityType, MortalRole
from aerona.domain.enums.mind import DreamKind, DreamReading, MemoryKind, NeedKind, SkillKind, ThoughtKind, ValueHolder
from aerona.domain.enums.society import NaturalLaw
from aerona.domain.enums.world import WorldType
from aerona.engine.body.conditions import gain_condition
from aerona.engine.context import TickContext
from aerona.engine.lifecycle.aging import is_notable
from aerona.engine.mind.book import locked_for, needs_of, stored_values
from aerona.engine.mind.split import facets_of
from aerona.engine.mind.thoughts import need_importance, shift_mind, strength_of, think, thinker, thoughts_of
from aerona.engine.mortal.kin import partners_of
from aerona.engine.mortal.standing import add_renown, add_stress
from aerona.engine.notes import note
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.queries import active_bonds
from aerona.engine.services.war import ongoing_wars
from aerona.rules.registry import Rules

DREAM_LOCK = "dreams"
DREAMS_KEY = "dreams"
SEERS = frozenset({MortalRole.SEER, MortalRole.CHOSEN, MortalRole.SAINT})
DREADFUL = frozenset({"fear", "anxiety", "despair", "grief"})
FAVOURED = (DreamReading.OMEN_OF_FAVOUR, DreamReading.OMEN_OF_PLENTY)


@dataclass(frozen=True)
class DreamDraft:
    kind: DreamKind
    intensity: int
    content: tuple[int, ...] = ()
    thought_id: int | None = None
    sender_id: int | None = None
    partner_id: int | None = None
    world_id: int | None = None
    message_id: int | None = None


async def record_dream(session: AsyncSession, dreamer_id: int, draft: DreamDraft, epoch: int, *, forced: bool = False) -> DreamRow | None:
    if await thinker(session, dreamer_id) is None or write_blocked(dreamer_id, DREAMS_KEY):
        return None
    if not forced and await locked_for(session, dreamer_id, DREAM_LOCK):
        return None
    row = DreamRow(
        dreamer_node_id=dreamer_id,
        kind=draft.kind,
        epoch=epoch,
        intensity=max(0, min(PERCENT, draft.intensity)),
        content=list(dict.fromkeys(draft.content)),
        thought_id=draft.thought_id,
        sender_node_id=draft.sender_id,
        partner_node_id=draft.partner_id,
        world_id=draft.world_id,
        message_id=draft.message_id,
        reading=DreamReading.UNREAD,
        recurring=False,
    )
    session.add(row)
    await session.flush()
    return row


async def near_dream_world(session: AsyncSession, mortal: EntityRow) -> int | None:
    if mortal.world_id is None:
        return None
    worlds = list(await session.scalars(select(WorldRow).where(WorldRow.world_type == WorldType.DREAM).order_by(WorldRow.id)))
    for world in worlds:
        if mortal.world_id in {world.parent_world_id, world.id}:
            return world.id
        linked = await session.scalar(
            select(RouteRow.id)
            .where(
                or_(
                    (RouteRow.world_a_id == world.id) & (RouteRow.world_b_id == mortal.world_id),
                    (RouteRow.world_b_id == world.id) & (RouteRow.world_a_id == mortal.world_id),
                )
            )
            .limit(1)
        )
        if linked is not None:
            return world.id
    return None


async def seer(session: AsyncSession, rules: Rules, mortal: EntityRow) -> bool:
    if mortal.mortal_role in SEERS:
        return True
    level = await session.scalar(select(SkillRow.level).where(SkillRow.holder_node_id == mortal.id, SkillRow.skill == SkillKind.PROPHECY).limit(1))
    return (level or 0) >= rules.dreams.prophecy_reader_level


@dataclass
class Mind:
    fears: list[ThoughtRow]
    wounds: list[MemoryRow]
    longings: list[tuple[int, NeedKind]]
    partner: int | None
    gifted: bool
    world: int | None
    strongest: ThoughtRow | None


async def mind_of_dreamer(ctx: TickContext, mortal: EntityRow) -> Mind:
    table = ctx.rules.thoughts
    rows = await thoughts_of(ctx.session, mortal.id)
    recent = [row for row in rows if ctx.epoch - row.epoch <= 1]
    fears = [row for row in recent if row.emotion.value in DREADFUL]
    wounds = list(
        await ctx.session.scalars(
            select(MemoryRow).where(MemoryRow.holder_node_id == mortal.id, MemoryRow.kind == MemoryKind.FORMATIVE, MemoryRow.magnitude < 0)
        )
    )
    facets = await facets_of(ctx.session, mortal.id)
    values = await stored_values(ctx.session, ValueHolder.PERSONAL, mortal.id)
    longings = [
        (value, need)
        for need, value in (await needs_of(ctx.session, mortal.id)).items()
        if value < table.need_unmet_below and need_importance(ctx.rules, need, facets, values) >= table.need_felt_above_pct
    ]
    partners = [
        *await partners_of(ctx.session, mortal.id),
        *(bond.target_node_id for bond in await active_bonds(ctx.session, [BondKind.LOVES], sources=[mortal.id])),
    ]
    living = [other for other in partners if (found := await ctx.session.get(EntityRow, other)) is not None and found.status is EntityStatus.CANON]
    strongest = max(rows, key=lambda row: (strength_of(row, ctx.epoch), row.id), default=None)
    return Mind(
        fears=fears,
        wounds=wounds,
        longings=longings,
        partner=living[0] if living else None,
        gifted=await seer(ctx.session, ctx.rules, mortal),
        world=await near_dream_world(ctx.session, mortal),
        strongest=strongest,
    )


async def prophecy_content(ctx: TickContext, mortal: EntityRow) -> tuple[int, ...]:
    wars = [item.war.event_entity_id for item in await ongoing_wars(ctx.session) if item.war.event_entity_id is not None]
    if wars:
        return (ctx.rng(seed_of("prophecy.war", mortal.id, ctx.epoch)).pick(wars),)
    prophecies = list(
        await ctx.session.scalars(
            select(EntityRow.id).where(
                EntityRow.entity_type == EntityType.PROPHECY, EntityRow.status == EntityStatus.CANON, EntityRow.world_id == mortal.world_id
            )
        )
    )
    return (ctx.rng(seed_of("prophecy", mortal.id, ctx.epoch)).pick(prophecies),) if prophecies else ()


async def recurring(ctx: TickContext, mortal: EntityRow, row: DreamRow) -> bool:
    table = ctx.rules.dreams
    count = len(
        list(
            await ctx.session.scalars(
                select(DreamRow.id).where(
                    DreamRow.dreamer_node_id == mortal.id, DreamRow.kind == DreamKind.NIGHTMARE, DreamRow.epoch > ctx.epoch - table.recurring_window
                )
            )
        )
    )
    if count < table.recurring_after:
        return False
    row.recurring = True
    await gain_condition(ctx, mortal, ConditionKind.NIGHTMARES, HarmCause.ACCIDENT, severity=min(5, 1 + count - table.recurring_after))
    return True


async def nightmare(ctx: TickContext, mortal: EntityRow, mind: Mind, base: int) -> DreamRow | None:
    table = ctx.rules.dreams
    subjects = tuple(memory.subject_node_id for memory in mind.wounds[:3]) or tuple(row.subject_node_id for row in mind.fears if row.subject_node_id)
    size = max(base, abs(mind.wounds[0].magnitude)) if mind.wounds else base
    row = await record_dream(ctx.session, mortal.id, DreamDraft(DreamKind.NIGHTMARE, size, subjects), ctx.epoch)
    if row is None:
        return None
    await add_stress(ctx.session, mortal.id, table.nightmare_stress, ctx.epoch)
    await think(ctx.session, ctx.rules, mortal.id, ThoughtKind.HAD_NIGHTMARE, ctx.epoch, intensity=row.intensity)
    if await recurring(ctx, mortal, row):
        await note(ctx, f"{mortal.name} is haunted by the same nightmare night after night.", key="dream.recurring", ids=[mortal.id])
    return row


async def dream(ctx: TickContext, mortal: EntityRow) -> DreamRow | None:
    table = ctx.rules.dreams
    rng = ctx.rng(seed_of("dream", mortal.id, ctx.epoch))
    real = ctx.rules.natural_laws.real_dream_pct / PERCENT if (await ctx.laws()).has(NaturalLaw.DREAMS_ARE_REAL, mortal.world_id) else 1.0
    if not rng.chance(table.dream_pct * real * await ctx.hook_factor(mortal.id, DomainHook.DREAM_SENDING)):
        return None
    mind = await mind_of_dreamer(ctx, mortal)
    weights = {
        DreamKind.ORDINARY: 1.0 + (1 if mind.strongest is not None else 0),
        DreamKind.NIGHTMARE: float(table.nightmare_weight * (len(mind.fears) + len(mind.wounds))),
        DreamKind.LONGING: float(table.longing_weight * len(mind.longings)),
        DreamKind.PROPHETIC: float(table.prophetic_weight if mind.gifted or mind.world is not None else 0),
        DreamKind.SHARED: float(table.shared_weight if mind.partner is not None else 0),
    }
    kind = rng.weighted(list(weights), list(weights.values()))
    strongest = mind.strongest
    base = round(strength_of(strongest, ctx.epoch)) if strongest is not None else table.nightmare_stress * 4
    if kind is DreamKind.NIGHTMARE:
        row = await nightmare(ctx, mortal, mind, base)
    elif kind is DreamKind.LONGING:
        row = await record_dream(ctx.session, mortal.id, DreamDraft(kind, base), ctx.epoch)
        if row is not None:
            await think(ctx.session, ctx.rules, mortal.id, ThoughtKind.DREAMED_OF_LONGING, ctx.epoch)
    elif kind is DreamKind.PROPHETIC:
        row = await record_dream(
            ctx.session, mortal.id, DreamDraft(kind, max(base, PERCENT // 2), await prophecy_content(ctx, mortal), world_id=mind.world), ctx.epoch
        )
    elif kind is DreamKind.SHARED and mind.partner is not None:
        draft = DreamDraft(kind, base, (mind.partner,), partner_id=mind.partner, world_id=mind.world)
        row = await record_dream(ctx.session, mortal.id, draft, ctx.epoch)
        if row is not None:
            await record_dream(ctx.session, mind.partner, DreamDraft(kind, base, (mortal.id,), partner_id=mortal.id, world_id=mind.world), ctx.epoch)
            for dreamer in (mortal.id, mind.partner):
                await think(
                    ctx.session, ctx.rules, dreamer, ThoughtKind.HAD_GOOD_DREAM, ctx.epoch, subject_id=mind.partner if dreamer == mortal.id else mortal.id
                )
    else:
        content = (strongest.subject_node_id,) if strongest is not None and strongest.subject_node_id is not None else ()
        row = await record_dream(
            ctx.session, mortal.id, DreamDraft(DreamKind.ORDINARY, base, content, thought_id=strongest.id if strongest else None), ctx.epoch
        )
        if row is not None and strongest is not None and EMOTIONS[strongest.emotion].valence > 0:
            await think(ctx.session, ctx.rules, mortal.id, ThoughtKind.HAD_GOOD_DREAM, ctx.epoch)
    if row is not None:
        await interpret(ctx, mortal, row, mind)
    return row


async def reader_for(ctx: TickContext, mortal: EntityRow) -> EntityRow | None:
    if mortal.location_id is None:
        return None
    neighbours = await ctx.session.scalars(
        select(EntityRow)
        .where(await present_among(ctx.session, [mortal.location_id]), EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    for neighbour in neighbours:
        if await seer(ctx.session, ctx.rules, neighbour):
            return neighbour
    return None


async def reading_of(ctx: TickContext, mortal: EntityRow, row: DreamRow, mind: Mind | None) -> DreamReading:
    if row.kind is DreamKind.LONGING and mind is not None and mind.longings:
        _, need = min(mind.longings, key=lambda item: item[0])
        return NEED_READINGS[NEEDS[need].group]
    at_war = mortal.location_id is not None and bool(await ongoing_wars(ctx.session, mortal.location_id))
    if row.kind is DreamKind.NIGHTMARE:
        return DreamReading.OMEN_OF_WAR if at_war else DreamReading.OMEN_OF_DEATH if row.intensity >= PERCENT * 3 // 4 else DreamReading.WARNING
    if row.kind is DreamKind.PROPHETIC:
        return DreamReading.OMEN_OF_WAR if at_war else DreamReading.OMEN_OF_FAVOUR
    if row.kind is DreamKind.SHARED:
        return DreamReading.CALL_TO_LOVE
    if row.kind is DreamKind.VISITATION:
        return DreamReading.OMEN_OF_FAVOUR
    return ctx.rng(seed_of("reading", row.id)).pick(list(FAVOURED)) if row.intensity >= PERCENT // 2 else DreamReading.CALL_TO_JOURNEY


async def interpret(ctx: TickContext, mortal: EntityRow, row: DreamRow, mind: Mind | None = None) -> DreamReading:
    table = ctx.rules.dreams
    reader = await reader_for(ctx, mortal)
    if reader is None or not ctx.rng(seed_of("read", row.id)).chance(table.reading_pct):
        return row.reading
    row.reader_node_id = reader.id
    row.reading = await reading_of(ctx, mortal, row, mind)
    level = await ctx.session.scalar(select(SkillRow.level).where(SkillRow.holder_node_id == reader.id, SkillRow.skill == SkillKind.PROPHECY).limit(1)) or 0
    truth = level * table.reading_skill_pct / PERCENT if row.kind is DreamKind.PROPHETIC else level * table.reading_skill_pct / PERCENT / 2
    row.reading_true = ctx.rng(seed_of("truth", row.id)).chance(min(PERCENT, truth))
    await read_into(ctx, mortal, row)
    return row.reading


async def read_into(ctx: TickContext, mortal: EntityRow, row: DreamRow) -> None:
    spec = READINGS.get(row.reading)
    if spec is None:
        return
    await think(ctx.session, ctx.rules, mortal.id, spec.thought, ctx.epoch, subject_id=row.reader_node_id)
    await shift_mind(ctx.session, ctx.rules, mortal.id, spec.beliefs, spec.facets)
    if is_notable(ctx.rules, mortal, await EntityRepository(ctx.session).flags(mortal.id)):
        reader = await ctx.session.get(EntityRow, row.reader_node_id) if row.reader_node_id is not None else None
        by = f" by {reader.name}" if reader is not None and reader.id != mortal.id else ""
        reading = row.reading.value.replace("_", " ")
        await note(ctx, f"A dream of {mortal.name} was read{by} as {reading}.", key="dream.reading", ids=[mortal.id, *([reader.id] if reader else [])])


async def visitations(ctx: TickContext) -> int:
    rows = await ctx.session.scalars(select(MessageRow).where(MessageRow.intent == MessageIntent.DREAM, MessageRow.epoch >= ctx.epoch - 1))
    made = 0
    for message in list(rows):
        if await ctx.session.scalar(select(DreamRow.id).where(DreamRow.message_id == message.id)) is not None:
            continue
        mortal = await thinker(ctx.session, message.recipient_node_id)
        if mortal is None:
            continue
        draft = DreamDraft(DreamKind.VISITATION, PERCENT * 3 // 4, (message.sender_node_id,), sender_id=message.sender_node_id, message_id=message.id)
        if await visit(ctx, mortal, draft) is not None:
            made += 1
    return made


async def visit(ctx: TickContext, mortal: EntityRow, draft: DreamDraft) -> DreamRow | None:
    row = await record_dream(ctx.session, mortal.id, draft, ctx.epoch)
    if row is None:
        return None
    await think(ctx.session, ctx.rules, mortal.id, ThoughtKind.RECEIVED_VISITATION, ctx.epoch, subject_id=draft.sender_id)
    await add_renown(ctx.session, mortal.id, ctx.rules.dreams.visitation_renown, ctx.epoch, rules=ctx.rules)
    await interpret(ctx, mortal, row)
    return row
