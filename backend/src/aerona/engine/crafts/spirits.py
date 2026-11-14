from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import delete, or_, select

from aerona.constants.units import PERCENT
from aerona.db.tables.crafts import EmotionSpiritRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import ThoughtRow
from aerona.db.write_guard import held
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.entity import EntityFlag, EntityType
from aerona.domain.enums.mind import Emotion
from aerona.engine.context import TickContext
from aerona.engine.economy.stocks import goods_of
from aerona.engine.notes import note
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import add_flag
from aerona.engine.primitives.stats import stat


@dataclass
class SpiritTally:
    born: int = 0
    amplified: int = 0
    faded: int = 0
    reagents: int = 0


async def felt_by_region(ctx: TickContext, atlas: RegionAtlas) -> dict[int, dict[Emotion, float]]:
    felt: dict[int, dict[Emotion, float]] = defaultdict(lambda: defaultdict(float))
    rows = await ctx.session.execute(select(ThoughtRow.holder_node_id, ThoughtRow.emotion, ThoughtRow.intensity).where(ThoughtRow.epoch == ctx.epoch))
    for holder, emotion, intensity in rows:
        region = atlas.top_region(holder)
        if region is not None and emotion is not None:
            felt[region][emotion] += float(intensity)
    return felt


async def birth(ctx: TickContext, atlas: RegionAtlas, tally: SpiritTally) -> None:
    table = ctx.rules.emotion_spirits
    living = {(row.region_entity_id, row.emotion) for row in await ctx.session.scalars(select(EmotionSpiritRow))}
    for region_id, feelings in sorted((await felt_by_region(ctx, atlas)).items()):
        region = await ctx.session.get(EntityRow, region_id)
        if region is None or held(region_id) or (stat(region, "magic") or 0) < table.spawn_density:
            continue
        for emotion, amount in sorted(feelings.items(), key=lambda item: item[0].value):
            if amount < table.spawn_from or (region_id, emotion) in living:
                continue
            strength = clamp_int(round(amount * PERCENT / max(1, table.spawn_from * 4)), 1, PERCENT)
            ctx.session.add(
                EmotionSpiritRow(region_entity_id=region_id, emotion=emotion, strength=strength, born_epoch=ctx.epoch, lifetime=table.lifetime, locked=[])
            )
            await add_flag(ctx.session, region_id, EntityFlag.OMEN, ctx.epoch)
            tally.born += 1
            await note(
                ctx,
                f"So much {emotion.value} gathered in {region.name} that it took the shape of spirits, and folk read it as an omen.",
                key="spirits.born",
                ids=[region_id],
            )


async def amplify(ctx: TickContext, row: EmotionSpiritRow, tally: SpiritTally) -> None:
    table = ctx.rules.emotion_spirits
    towns = select(EntityRow.id).where(EntityRow.location_id == row.region_entity_id, EntityRow.entity_type == EntityType.SETTLEMENT)
    present = select(EntityRow.id).where(or_(EntityRow.location_id == row.region_entity_id, EntityRow.location_id.in_(towns)))
    thoughts = await ctx.session.scalars(
        select(ThoughtRow).where(ThoughtRow.epoch == ctx.epoch, ThoughtRow.emotion == row.emotion, ThoughtRow.holder_node_id.in_(present))
    )
    for thought in list(thoughts):
        if held(thought.holder_node_id):
            continue
        thought.intensity = clamp_int(thought.intensity + table.amplify * row.strength / PERCENT, 0, PERCENT)
        tally.amplified += 1


async def yield_reagents(ctx: TickContext, row: EmotionSpiritRow, tally: SpiritTally) -> None:
    binder = await ctx.session.get(EntityRow, row.bound_by_node_id) if row.bound_by_node_id is not None else None
    home = binder.location_id if binder is not None else None
    if home is None or held(home):
        return
    amount = ctx.rules.emotion_spirits.reagent_yield
    await goods_of(ctx.session, ctx.epoch).add(home, CommodityKind.MAGICAL_REAGENTS, amount, GoodsFlow.PRODUCTION)
    tally.reagents += amount


async def keep_spirits(ctx: TickContext, tally: SpiritTally) -> None:
    atlas = await RegionAtlas.load(ctx.session)
    await birth(ctx, atlas, tally)
    await ctx.session.flush()
    for row in list(await ctx.session.scalars(select(EmotionSpiritRow).order_by(EmotionSpiritRow.id))):
        if held(row.region_entity_id):
            continue
        await amplify(ctx, row, tally)
        if row.bound_by_node_id is not None:
            await yield_reagents(ctx, row, tally)
            continue
        if "lifetime" in row.locked:
            continue
        row.lifetime -= 1
        if row.lifetime <= 0:
            await ctx.session.execute(delete(EmotionSpiritRow).where(EmotionSpiritRow.id == row.id))
            tally.faded += 1
    await ctx.session.flush()
