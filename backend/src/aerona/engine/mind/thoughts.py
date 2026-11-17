from collections.abc import Mapping

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.mind_split import FACETS
from aerona.catalog.thoughts import EMOTIONS, MOOD_ORDER, NEEDS, THOUGHTS
from aerona.constants.units import PERCENT
from aerona.db.key_index import index_spec, keyed_rows
from aerona.db.read_memo import memoized
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import ThoughtRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.write_guard import write_blocked
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import Emotion, Facet, MemoryKind, MoodState, NeedKind, ThoughtKind, ValueAxis, ValueHolder
from aerona.engine.mind.book import clamp_value, is_locked, locked_for, mind_of, stored_values, write_values
from aerona.engine.mind.memories import remember
from aerona.engine.mind.split import FACET_LOCK, clamp_facet, facet_weight, facets_of, write_facets
from aerona.engine.mind.values import VALUE_LOCK
from aerona.engine.mortal.profile import ensure_profile, is_held
from aerona.engine.primitives.numbers import clamp_int
from aerona.rules.registry import Rules

THOUGHT_LOCK = "thoughts"
THOUGHTS_KEY = "thoughts"
MOOD_FIELD = "mood"
IMPORTANCE_BASE = PERCENT
IMPORTANCE_MAX = 2 * PERCENT
FACET_SPAN = 50
VALUE_SPAN = 100


def amplified(rules: Rules, emotion: Emotion, intensity: float, facets: Mapping[Facet, int]) -> int:
    lean = facet_weight(facets, EMOTIONS[emotion].amplifiers)
    return clamp_int(intensity * max(0.0, 1 + lean * rules.thoughts.facet_amplify_pct / PERCENT), 0, PERCENT)


def strength_of(row: ThoughtRow, epoch: int) -> float:
    return float(row.intensity * ((PERCENT - row.decay_pct) / PERCENT) ** max(0, epoch - row.epoch))


def need_importance(rules: Rules, need: NeedKind, facets: Mapping[Facet, int], values: Mapping[ValueAxis, int]) -> int:
    spec = NEEDS[need]
    table = rules.needs_depth
    from_facets = sum(facets.get(facet, 0) / FACET_SPAN * weight for facet, weight in spec.facets.items()) * table.importance_facet_pct / PERCENT
    from_beliefs = sum(values.get(axis, 0) / VALUE_SPAN * weight for axis, weight in spec.beliefs.items()) * table.importance_belief_pct / PERCENT
    return clamp_int(IMPORTANCE_BASE + from_facets + from_beliefs, 0, IMPORTANCE_MAX)


async def thinker(session: AsyncSession, holder_id: int) -> EntityRow | None:
    found = await session.get(EntityRow, holder_id)
    if found is None or found.entity_type is not EntityType.MORTAL or found.status is not EntityStatus.CANON:
        return None
    return found


async def shift_mind(session: AsyncSession, rules: Rules, holder_id: int, beliefs: Mapping[ValueAxis, int], facets: Mapping[Facet, int]) -> None:
    mind = await mind_of(session, holder_id)
    scale = rules.thoughts.formative_shift_pct / PERCENT
    if beliefs and not is_locked(mind, VALUE_LOCK):
        values = await stored_values(session, ValueHolder.PERSONAL, holder_id)
        if values:
            for axis, shift in beliefs.items():
                values[axis] = clamp_value(values.get(axis, 0) + shift * scale)
            await write_values(session, ValueHolder.PERSONAL, holder_id, values)
    if facets and not is_locked(mind, FACET_LOCK):
        current = await facets_of(session, holder_id)
        if current:
            shifted = {facet: clamp_facet(current.get(facet, 0) + shift * scale) for facet, shift in facets.items() if facet in FACETS}
            await write_facets(session, holder_id, shifted)


EPOCH_THOUGHTS = index_spec(ThoughtRow, "holder_node_id", "kind", "subject_node_id", scope="epoch")


async def same_thought(session: AsyncSession, holder_id: int, kind: ThoughtKind, epoch: int, subject: int | None) -> ThoughtRow | None:
    current = await keyed_rows(session, EPOCH_THOUGHTS, epoch)
    if current is not None:
        found = current.rows.get((holder_id, kind, subject))
        return found[0] if found else None
    return await session.scalar(
        select(ThoughtRow)
        .where(
            ThoughtRow.holder_node_id == holder_id,
            ThoughtRow.kind == kind,
            ThoughtRow.epoch == epoch,
            ThoughtRow.subject_node_id.is_(None) if subject is None else ThoughtRow.subject_node_id == subject,
        )
        .limit(1)
    )


async def think(
    session: AsyncSession,
    rules: Rules,
    holder_id: int,
    kind: ThoughtKind,
    epoch: int,
    *,
    subject_id: int | None = None,
    intensity: float | None = None,
    emotion: Emotion | None = None,
    forced: bool = False,
) -> ThoughtRow | None:
    holder = await thinker(session, holder_id)
    if holder is None or write_blocked(holder_id, THOUGHTS_KEY) or (not forced and await locked_for(session, holder_id, THOUGHT_LOCK)):
        return None
    spec = THOUGHTS[kind]
    feeling = emotion or spec.emotion
    size = amplified(rules, feeling, spec.intensity if intensity is None else intensity, await facets_of(session, holder_id))
    if size <= 0:
        return None
    subject = subject_id if subject_id != holder_id else None
    same = await same_thought(session, holder_id, kind, epoch, subject)
    if same is not None:
        same.intensity = max(same.intensity, size)
        await session.flush()
        return same
    row = ThoughtRow(
        holder_node_id=holder_id, kind=kind, emotion=feeling, subject_node_id=subject, intensity=size, epoch=epoch, decay_pct=rules.thoughts.decay_pct
    )
    session.add(row)
    await session.flush()
    if size >= rules.thoughts.long_term_threshold:
        await take_to_heart(session, rules, holder, row)
    return row


async def take_to_heart(session: AsyncSession, rules: Rules, holder: EntityRow, row: ThoughtRow) -> None:
    spec = THOUGHTS[row.kind]
    about = row.subject_node_id or holder.location_id
    if about is not None:
        memory = await remember(
            session,
            rules,
            holder_id=holder.id,
            subject_id=about,
            kind=MemoryKind.FORMATIVE,
            magnitude=EMOTIONS[row.emotion].valence * row.intensity,
            epoch=row.epoch,
            note=spec.label,
            merge=False,
        )
        row.memory_id = memory.id if memory is not None else None
    await shift_mind(session, rules, holder.id, spec.beliefs, spec.facets)
    await session.flush()


@memoized(ThoughtRow)
async def thought_rows(session: AsyncSession, holder_id: int) -> tuple[ThoughtRow, ...]:
    return tuple(
        await session.scalars(select(ThoughtRow).where(ThoughtRow.holder_node_id == holder_id).order_by(ThoughtRow.epoch.desc(), ThoughtRow.id.desc()))
    )


async def thoughts_of(session: AsyncSession, holder_id: int) -> list[ThoughtRow]:
    return list(await thought_rows(session, holder_id))


def mood_score(rules: Rules, rows: list[ThoughtRow], epoch: int) -> int:
    weights = [(EMOTIONS[row.emotion].valence, strength_of(row, epoch)) for row in rows]
    total = sum(strength for _, strength in weights)
    signed = sum(valence * strength for valence, strength in weights)
    return clamp_int(PERCENT * signed / (total + rules.thoughts.mood_damping), -PERCENT, PERCENT)


def mood_state(rules: Rules, score: int) -> MoodState:
    table = rules.thoughts
    bounds = (table.elated_above, table.content_above, table.fine_above, table.uneasy_above, table.unhappy_above, table.miserable_above)
    for state, bound in zip(MOOD_ORDER, bounds, strict=False):
        if score > bound:
            return state
    return MoodState.BROKEN


async def settle_mood(session: AsyncSession, rules: Rules, mortal: EntityRow, epoch: int) -> MoodState | None:
    profile, _ = await ensure_profile(session, mortal.id, epoch)
    if is_held(profile, MOOD_FIELD):
        return None
    score = mood_score(rules, await thoughts_of(session, mortal.id), epoch)
    profile.mood_score = score
    profile.mood = mood_state(rules, score)
    return profile.mood


async def mood_of(session: AsyncSession, node_id: int | None) -> int:
    if node_id is None:
        return 0
    profile = await session.get(MortalProfileRow, node_id)
    return profile.mood_score if profile is not None else 0


def mood_factor(score: int, scale_pct: int) -> float:
    return max(0.0, 1 + score / PERCENT * scale_pct / PERCENT)


async def forget_faded(session: AsyncSession, rules: Rules, holder_id: int, epoch: int) -> int:
    gone = [row for row in await thoughts_of(session, holder_id) if strength_of(row, epoch) < rules.thoughts.forget_below]
    for row in gone:
        await session.delete(row)
    await session.flush()
    return len(gone)
