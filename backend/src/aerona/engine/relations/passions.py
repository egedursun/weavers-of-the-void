from collections.abc import Iterable
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import LifeDreamRow, MemoryRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.polity import OathRow
from aerona.db.tables.relations import PassionRow, RelationshipRow
from aerona.db.write_guard import write_blocked
from aerona.domain.enums.body import MADNESS_CONDITIONS, HarmCause
from aerona.domain.enums.mind import DreamState, LifeGoal, MemoryKind, ThoughtKind, ValueAxis, ValueHolder
from aerona.domain.enums.polity import OathKind, OathStatus
from aerona.domain.enums.relations import PassionKind, PassionSource, RelationType
from aerona.engine.body.conditions import gain_condition
from aerona.engine.context import TickContext
from aerona.engine.military.feuds import house_of
from aerona.engine.mind.book import is_locked, mind_of, stored_values
from aerona.engine.mind.grief import start_grief
from aerona.engine.mind.thoughts import think
from aerona.engine.mortal.life import adult
from aerona.engine.mortal.standing import add_stress
from aerona.engine.primitives.faith import living_patron
from aerona.engine.primitives.naming import seed_of

PASSIONS_KEY = "passions"
LOYAL_OATHS = frozenset({OathKind.FEALTY, OathKind.PROTECTION, OathKind.BLOOD_BROTHERHOOD})
TENDER = frozenset({PassionKind.LOVE, PassionKind.LOYALTY, PassionKind.DEVOTION})
Key = tuple[PassionKind, int]


@dataclass
class PassionTally:
    kindled: int = 0
    faded: int = 0
    stirred: int = 0
    broke: int = 0


async def passions_of(session: AsyncSession, holder_id: int) -> list[PassionRow]:
    return list(await session.scalars(select(PassionRow).where(PassionRow.holder_node_id == holder_id).order_by(PassionRow.strength.desc(), PassionRow.id)))


async def kindle(
    session: AsyncSession, holder_id: int, kind: PassionKind, object_id: int, *, strength: int, source: PassionSource, epoch: int
) -> PassionRow | None:
    if holder_id == object_id or write_blocked(holder_id, PASSIONS_KEY):
        return None
    row = await session.scalar(
        select(PassionRow).where(PassionRow.holder_node_id == holder_id, PassionRow.kind == kind, PassionRow.object_node_id == object_id)
    )
    if row is None:
        row = PassionRow(holder_node_id=holder_id, kind=kind, object_node_id=object_id, strength=0, source=source, since_epoch=epoch, locked=[])
        session.add(row)
    if "strength" not in row.locked:
        row.strength = max(row.strength, min(PERCENT, strength))
    await session.flush()
    return row


async def from_bonds(ctx: TickContext, holder_id: int, found: dict[Key, tuple[int, PassionSource]]) -> None:
    at = ctx.rules.passions.relation_at
    for row in await ctx.session.scalars(select(RelationshipRow).where(RelationshipRow.holder_node_id == holder_id)):
        kinds = set(row.kinds)
        if kinds & {RelationType.LOVER.value, RelationType.SPOUSE.value} and row.romance >= at:
            found[(PassionKind.LOVE, row.subject_node_id)] = (row.romance, PassionSource.RELATIONSHIP)
        elif RelationType.BEST_FRIEND.value in kinds and row.friendship >= at:
            found[(PassionKind.LOVE, row.subject_node_id)] = (row.friendship, PassionSource.RELATIONSHIP)
        if kinds & {RelationType.ENEMY.value, RelationType.NEMESIS.value} and -row.friendship >= at:
            found[(PassionKind.HATRED, row.subject_node_id)] = (-row.friendship, PassionSource.RELATIONSHIP)


async def from_oaths(ctx: TickContext, holder_id: int, found: dict[Key, tuple[int, PassionSource]]) -> None:
    sworn = select(OathRow).where(OathRow.swearer_entity_id == holder_id, OathRow.status == OathStatus.SWORN, OathRow.kind.in_(list(LOYAL_OATHS)))
    for oath in await ctx.session.scalars(sworn.order_by(OathRow.id)):
        if oath.recipient_node_id is not None:
            found[(PassionKind.LOYALTY, oath.recipient_node_id)] = (ctx.rules.passions.oath_strength, PassionSource.OATH)


async def from_memories(ctx: TickContext, holder_id: int, found: dict[Key, tuple[int, PassionSource]]) -> None:
    rows = await ctx.session.scalars(
        select(MemoryRow).where(
            MemoryRow.holder_node_id == holder_id, MemoryRow.kind == MemoryKind.KILLED_KIN, MemoryRow.magnitude <= -ctx.rules.passions.memory_at
        )
    )
    for row in rows:
        key = (PassionKind.HATRED, row.subject_node_id)
        found[key] = (max(found.get(key, (0, PassionSource.MEMORY))[0], -row.magnitude), PassionSource.MEMORY)


async def from_upbringing(ctx: TickContext, mortal: EntityRow, found: dict[Key, tuple[int, PassionSource]]) -> None:
    profile = await ctx.session.get(MortalProfileRow, mortal.id)
    if profile is None or not adult(profile.life_stage):
        return
    at = ctx.rules.passions.upbringing_at
    values = await stored_values(ctx.session, ValueHolder.PERSONAL, mortal.id)
    god = await living_patron(ctx.session, mortal)
    house = await house_of(ctx.session, mortal.id)
    objects = (
        (ValueAxis.PIETY, PassionKind.LOYALTY, god.id if god is not None else None),
        (ValueAxis.FAMILY, PassionKind.LOYALTY, house),
        (ValueAxis.LOYALTY, PassionKind.LOYALTY, profile.polity_id),
        (ValueAxis.TRADITION, PassionKind.DEVOTION, mortal.location_id),
    )
    for axis, kind, target in objects:
        value = values.get(axis, 0)
        if target is not None and value >= at:
            found.setdefault((kind, target), (value, PassionSource.UPBRINGING))


async def tend_passions(ctx: TickContext, mortal: EntityRow, tally: PassionTally) -> None:
    if write_blocked(mortal.id, PASSIONS_KEY) or is_locked(await mind_of(ctx.session, mortal.id), PASSIONS_KEY):
        return
    found: dict[Key, tuple[int, PassionSource]] = {}
    await from_bonds(ctx, mortal.id, found)
    await from_oaths(ctx, mortal.id, found)
    await from_memories(ctx, mortal.id, found)
    await from_upbringing(ctx, mortal, found)
    for (kind, target), (strength, source) in sorted(found.items(), key=lambda item: (item[0][0].value, item[0][1])):
        row = await kindle(ctx.session, mortal.id, kind, target, strength=strength, source=source, epoch=ctx.epoch)
        tally.kindled += row is not None and row.since_epoch == ctx.epoch
    for row in await passions_of(ctx.session, mortal.id):
        if (row.kind, row.object_node_id) in found or "strength" in row.locked or row.source is PassionSource.DIVINE:
            continue
        row.strength = max(0, row.strength - ctx.rules.passions.fade)
        if row.strength == 0:
            await ctx.session.delete(row)
        tally.faded += 1
    await ctx.session.flush()


async def invoke(ctx: TickContext, holder: EntityRow, objects: Iterable[int] | None) -> float:
    table = ctx.rules.passions
    if write_blocked(holder.id, PASSIONS_KEY):
        return 1.0
    wanted = set(objects) if objects is not None else None
    rows = [
        row
        for row in await passions_of(ctx.session, holder.id)
        if row.strength >= table.invoke_at and row.invoked_epoch != ctx.epoch and (wanted is None or row.object_node_id in wanted)
    ]
    if not rows:
        return 1.0
    row = rows[0]
    row.invoked_epoch = ctx.epoch
    rng = ctx.rng(seed_of("passion", holder.id, row.object_node_id, ctx.epoch))
    if rng.chance(row.strength):
        await think(ctx.session, ctx.rules, holder.id, ThoughtKind.PASSION_STIRRED, ctx.epoch, subject_id=row.object_node_id)
        return 1 + table.bonus_pct / PERCENT
    await add_stress(ctx.session, holder.id, table.break_stress, ctx.epoch)
    if rng.chance(table.break_madness_pct):
        await gain_condition(ctx, holder, rng.pick(list(MADNESS_CONDITIONS)), HarmCause.ACCIDENT, severity=2, source_node_id=row.object_node_id)
    else:
        await think(ctx.session, ctx.rules, holder.id, ThoughtKind.PASSION_BROKE, ctx.epoch, subject_id=row.object_node_id)
    return 1.0


async def avenge(ctx: TickContext, holder_id: int, killer_id: int) -> None:
    dream = await ctx.session.get(LifeDreamRow, holder_id)
    if dream is not None and ("progress" in (dream.locked or []) or (dream.state is DreamState.PURSUING and dream.goal is LifeGoal.AVENGE_KIN)):
        return
    if dream is None:
        dream = LifeDreamRow(
            holder_node_id=holder_id, goal=LifeGoal.AVENGE_KIN, milestones=[], progress=0, state=DreamState.PURSUING, started_epoch=ctx.epoch, locked=[]
        )
        ctx.session.add(dream)
    dream.goal, dream.target_node_id, dream.milestones, dream.progress = LifeGoal.AVENGE_KIN, killer_id, [], 0
    dream.state, dream.started_epoch, dream.ended_epoch = DreamState.PURSUING, ctx.epoch, None


async def bereaved(ctx: TickContext, deceased: EntityRow, killer_id: int | None) -> int:
    table = ctx.rules.passions
    rows = list(
        await ctx.session.scalars(select(PassionRow).where(PassionRow.object_node_id == deceased.id, PassionRow.kind.in_(list(TENDER))).order_by(PassionRow.id))
    )
    mourned = 0
    for row in rows:
        if write_blocked(row.holder_node_id, PASSIONS_KEY):
            continue
        if await start_grief(ctx.session, ctx.rules, row.holder_node_id, deceased.id, strength=table.grief_strength, epoch=ctx.epoch) is not None:
            mourned += 1
        rng = ctx.rng(seed_of("vengeance", row.holder_node_id, deceased.id))
        if killer_id is not None and killer_id != row.holder_node_id and row.kind is PassionKind.LOVE and rng.chance(table.vengeance_pct):
            await avenge(ctx, row.holder_node_id, killer_id)
            await kindle(ctx.session, row.holder_node_id, PassionKind.HATRED, killer_id, strength=row.strength, source=PassionSource.MEMORY, epoch=ctx.epoch)
    return mourned


async def betrayed(ctx: TickContext, holder_id: int, object_id: int) -> bool:
    if write_blocked(holder_id, PASSIONS_KEY):
        return False
    rows = list(
        await ctx.session.scalars(
            select(PassionRow).where(PassionRow.holder_node_id == holder_id, PassionRow.object_node_id == object_id, PassionRow.kind.in_(list(TENDER)))
        )
    )
    if not rows:
        return False
    strongest = max(row.strength for row in rows)
    await think(ctx.session, ctx.rules, holder_id, ThoughtKind.BETRAYED, ctx.epoch, subject_id=object_id, intensity=PERCENT)
    await think(ctx.session, ctx.rules, holder_id, ThoughtKind.HEARTBROKEN, ctx.epoch, subject_id=object_id, intensity=strongest)
    for row in rows:
        if "kind" not in row.locked:
            await ctx.session.delete(row)
    await ctx.session.flush()
    await kindle(ctx.session, holder_id, PassionKind.HATRED, object_id, strength=strongest, source=PassionSource.MEMORY, epoch=ctx.epoch)
    return True


async def strongest_against(session: AsyncSession, holder_id: int, foe_id: int) -> int:
    found = await session.scalar(
        select(PassionRow.strength).where(PassionRow.holder_node_id == holder_id, PassionRow.object_node_id == foe_id, PassionRow.kind == PassionKind.HATRED)
    )
    return int(found or 0)
