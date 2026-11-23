from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.thoughts import COMPASSION_AXES, CONTEMPT_AXES, CURIOUS_STUDY, EMOTIONS, LOWERED, SUFFERING, UNEXPECTED
from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.mind import ThoughtRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import Emotion, MemoryKind, ThoughtKind, ValueAxis
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.mind.book import values_for
from aerona.engine.mind.memories import remember
from aerona.engine.mind.skills import practise_any
from aerona.engine.mind.thoughts import think
from aerona.engine.mortal.standing import add_wealth
from aerona.engine.primitives.folk import present_among
from aerona.engine.recording.record import record

DISCOVERY_KINDS = ("discovery.", "research.", "secret.", "relic.")


@dataclass
class EmotionTally:
    stirred: int = 0
    acted: int = 0


async def neighbours_feeling(ctx: TickContext, mortal: EntityRow, kinds: frozenset[ThoughtKind]) -> ThoughtRow | None:
    if mortal.location_id is None:
        return None
    here = select(EntityRow.id).where(
        await present_among(ctx.session, [mortal.location_id]), EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON
    )
    found: ThoughtRow | None = await ctx.session.scalar(
        select(ThoughtRow)
        .where(ThoughtRow.epoch == ctx.epoch, ThoughtRow.kind.in_(sorted(kinds)), ThoughtRow.holder_node_id.in_(here), ThoughtRow.holder_node_id != mortal.id)
        .order_by(ThoughtRow.intensity.desc(), ThoughtRow.id)
        .limit(1)
    )
    return found


async def stir_surprise(ctx: TickContext, mortal: EntityRow) -> bool:
    strongest = await ctx.session.scalar(
        select(ThoughtRow.intensity)
        .where(ThoughtRow.holder_node_id == mortal.id, ThoughtRow.epoch == ctx.epoch, ThoughtRow.kind.in_(sorted(UNEXPECTED)))
        .order_by(ThoughtRow.intensity.desc())
        .limit(1)
    )
    if strongest is None:
        return False
    size = strongest * ctx.rules.emotions.surprise_share_pct / PERCENT
    return await think(ctx.session, ctx.rules, mortal.id, ThoughtKind.WAS_SURPRISED, ctx.epoch, intensity=size) is not None


async def stir_curiosity(ctx: TickContext, mortal: EntityRow) -> bool:
    arrived = await ctx.session.scalar(
        select(BondRow.target_node_id).where(BondRow.source_node_id == mortal.id, BondRow.kind == BondKind.MIGRATED_TO, BondRow.epoch == ctx.epoch).limit(1)
    )
    found = None
    if arrived is None and mortal.location_id is not None:
        for prefix in DISCOVERY_KINDS:
            found = await ctx.session.scalar(
                select(IncidentRow.id)
                .where(IncidentRow.epoch == ctx.epoch, IncidentRow.place_entity_id == mortal.location_id, IncidentRow.kind.startswith(prefix))
                .limit(1)
            )
            if found is not None:
                break
    if arrived is None and found is None:
        return False
    return await think(ctx.session, ctx.rules, mortal.id, ThoughtKind.GREW_CURIOUS, ctx.epoch, subject_id=arrived) is not None


def lean_of(values: dict[ValueAxis, int], axes: tuple[ValueAxis, ValueAxis]) -> float:
    return max(0.0, sum(values.get(axis, 0) for axis in axes) / (2 * PERCENT))


async def stir_compassion(ctx: TickContext, mortal: EntityRow, values: dict[ValueAxis, int]) -> bool:
    lean = lean_of(values, COMPASSION_AXES)
    sufferer = await neighbours_feeling(ctx, mortal, SUFFERING) if lean > 0 else None
    if sufferer is None:
        return False
    size = sufferer.intensity * lean
    found = await think(ctx.session, ctx.rules, mortal.id, ThoughtKind.FELT_COMPASSION, ctx.epoch, subject_id=sufferer.holder_node_id, intensity=size)
    return found is not None


async def stir_contempt(ctx: TickContext, mortal: EntityRow, values: dict[ValueAxis, int]) -> bool:
    lean = lean_of(values, CONTEMPT_AXES)
    lowered = await neighbours_feeling(ctx, mortal, LOWERED) if lean > 0 else None
    if lowered is None:
        return False
    size = lowered.intensity * lean
    found = await think(ctx.session, ctx.rules, mortal.id, ThoughtKind.FELT_CONTEMPT, ctx.epoch, subject_id=lowered.holder_node_id, intensity=size)
    return found is not None


async def act_on(ctx: TickContext, mortal: EntityRow, row: ThoughtRow) -> bool:
    table = ctx.rules.emotions
    weight = EMOTIONS[row.emotion].act_weight
    if weight is None or row.intensity < table.felt_intensity or not ctx.rng(f"emotion.act.{mortal.id}.{row.id}").chance(weight(ctx.rules)):
        return False
    other = row.subject_node_id
    if row.emotion is Emotion.CURIOSITY:
        await practise_any(ctx.session, ctx.rules, mortal.id, CURIOUS_STUDY, table.curiosity_xp, epoch=ctx.epoch)
    elif row.emotion is Emotion.COMPASSION and other is not None:
        await add_wealth(ctx.session, mortal.id, -table.compassion_gift, ctx.epoch)
        await add_wealth(ctx.session, other, table.compassion_gift, ctx.epoch)
        await remember(
            ctx.session, ctx.rules, holder_id=other, subject_id=mortal.id, kind=MemoryKind.GIFTED_ME, magnitude=table.compassion_gift, epoch=ctx.epoch
        )
    elif row.emotion is Emotion.CONTEMPT and other is not None:
        await remember(
            ctx.session, ctx.rules, holder_id=other, subject_id=mortal.id, kind=MemoryKind.HUMILIATED_ME, magnitude=-table.contempt_insult, epoch=ctx.epoch
        )
    else:
        return False
    await record(ctx, "mind.emotion_felt", roles={IncidentRole.SUBJECT: mortal.id, IncidentRole.TARGET: other}, facts={"emotion": row.emotion})
    return True


async def stir_and_act(ctx: TickContext, mortal: EntityRow) -> EmotionTally:
    tally = EmotionTally()
    values = await values_for(ctx.session, mortal.id)
    for stirred in (
        await stir_surprise(ctx, mortal),
        await stir_curiosity(ctx, mortal),
        await stir_compassion(ctx, mortal, values),
        await stir_contempt(ctx, mortal, values),
    ):
        tally.stirred += 1 if stirred else 0
    moving = [emotion for emotion, spec in EMOTIONS.items() if spec.act_weight is not None]
    rows = await ctx.session.scalars(
        select(ThoughtRow).where(ThoughtRow.holder_node_id == mortal.id, ThoughtRow.epoch == ctx.epoch, ThoughtRow.emotion.in_(moving)).order_by(ThoughtRow.id)
    )
    for row in list(rows):
        tally.acted += 1 if await act_on(ctx, mortal, row) else 0
    return tally
