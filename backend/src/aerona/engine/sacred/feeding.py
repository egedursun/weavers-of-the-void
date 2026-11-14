from collections import defaultdict

from sqlalchemy import select

from aerona.catalog.sacred import DOMAIN_FEEDINGS
from aerona.db.tables.mind import ThoughtRow
from aerona.db.tables.sacred import EmotionHarvestRow, GodFeedingRow
from aerona.db.write_guard import held
from aerona.domain.enums.mind import Emotion
from aerona.engine.context import TickContext
from aerona.engine.crafts.haunting import spirit_feelings
from aerona.engine.divine.book import DivineBook

PERCENT_SCALE = 100


async def feedings_of(ctx: TickContext, god_id: int) -> list[GodFeedingRow]:
    return list(await ctx.session.scalars(select(GodFeedingRow).where(GodFeedingRow.god_node_id == god_id).order_by(GodFeedingRow.emotion)))


async def seed_feedings(ctx: TickContext, book: DivineBook) -> int:
    fed = set(await ctx.session.scalars(select(GodFeedingRow.god_node_id).distinct()))
    seeded = 0
    for god_id, god in sorted(book.gods.items()):
        if god_id in fed or held(god_id):
            continue
        emotions = dict.fromkeys(emotion for domain in god.living_domains for emotion in DOMAIN_FEEDINGS[domain])
        for emotion in emotions:
            ctx.session.add(GodFeedingRow(god_node_id=god_id, emotion=emotion, weight=ctx.rules.emotion_feeding.weight, epoch=ctx.epoch, locked=[]))
            seeded += 1
    await ctx.session.flush()
    return seeded


def drawn(ctx: TickContext, felt: float) -> int:
    table = ctx.rules.emotion_feeding
    if felt <= 0:
        return 0
    return round(table.essence_max * felt / (felt + max(1, table.half)))


async def felt_by_god(ctx: TickContext, book: DivineBook) -> dict[int, dict[Emotion, float]]:
    felt: dict[int, dict[Emotion, float]] = defaultdict(lambda: defaultdict(float))
    rows = await ctx.session.execute(select(ThoughtRow.holder_node_id, ThoughtRow.emotion, ThoughtRow.intensity).where(ThoughtRow.epoch == ctx.epoch))
    for holder, emotion, intensity in rows:
        if emotion is None:
            continue
        gods, _ = await book.faithful_of(ctx.session, holder)
        for god_id in gods:
            felt[god_id][emotion] += float(intensity)
    for towns, feeling, amount in await spirit_feelings(ctx.session, ctx.rules):
        fed: set[int] = set()
        for town in towns:
            gods, _ = await book.faithful_of(ctx.session, town)
            fed |= set(gods)
        for god_id in fed:
            felt[god_id][feeling] += amount
    return felt


async def harvest_feelings(ctx: TickContext, book: DivineBook) -> dict[int, int]:
    await seed_feedings(ctx, book)
    felt = await felt_by_god(ctx, book)
    gained: dict[int, int] = {}
    for god_id in sorted(book.gods):
        if held(god_id):
            continue
        rows = await feedings_of(ctx, god_id)
        weighted = {row.emotion: felt.get(god_id, {}).get(row.emotion, 0.0) * row.weight / PERCENT_SCALE for row in rows}
        total = drawn(ctx, sum(weighted.values()) * book.gods[god_id].potency)
        whole = sum(weighted.values())
        for row in rows:
            share = round(total * weighted[row.emotion] / whole) if whole > 0 else 0
            row.harvested = share
            row.epoch = ctx.epoch
            if weighted[row.emotion] > 0:
                ctx.session.add(EmotionHarvestRow(god_node_id=god_id, epoch=ctx.epoch, emotion=row.emotion, count=round(weighted[row.emotion]), essence=share))
        if total:
            gained[god_id] = total
    await ctx.session.flush()
    return gained
