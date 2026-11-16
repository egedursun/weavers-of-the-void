from collections import defaultdict
from collections.abc import Mapping

from sqlalchemy import or_, select

from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.folkways import LuckBeliefRow
from aerona.db.tables.fortune import FortuneLawRow, FortuneProfileRow, FortuneSourceRow
from aerona.db.write_guard import held
from aerona.domain.enums.fortune import FortuneLaw, FortuneSourceKind
from aerona.engine.context import TickContext
from aerona.engine.primitives.numbers import clamp_int

FORTUNE_CAP = 100
DIVINE_SOURCE: Mapping[FortuneSourceKind, bool] = total(
    FortuneSourceKind,
    {
        FortuneSourceKind.BLESSING: True,
        FortuneSourceKind.CURSE: True,
        FortuneSourceKind.CHARM: False,
        FortuneSourceKind.DIVINE_FAVOUR: True,
        FortuneSourceKind.DIVINE_DISFAVOUR: True,
        FortuneSourceKind.FATE_POWER: True,
        FortuneSourceKind.NATURAL_LAW: True,
        FortuneSourceKind.OATH_KEPT: False,
        FortuneSourceKind.OATH_BROKEN: False,
        FortuneSourceKind.PLACE: False,
        FortuneSourceKind.DAY: False,
        FortuneSourceKind.PRICE_PAID: False,
        FortuneSourceKind.CARE: False,
    },
)
STREAKS: Mapping[FortuneLaw, bool] = total(
    FortuneLaw,
    {FortuneLaw.CAUSES_ONLY: False, FortuneLaw.PERSONAL: True, FortuneLaw.DIVINE: False, FortuneLaw.BELIEF_SHAPED: True},
)
BELIEF_STEP = 5


async def law_of(ctx: TickContext, world_id: int | None) -> FortuneLaw:
    row = await ctx.session.get(FortuneLawRow, world_id) if world_id is not None else None
    return row.law if row is not None else FortuneLaw.PERSONAL


def streak_of(ctx: TickContext, node_id: int) -> int:
    table = ctx.rules.fortune
    walk = 0.0
    for back in range(table.streak_halflife * 2, -1, -1):
        epoch = ctx.epoch - back
        if epoch < 0:
            continue
        step = ctx.rng(f"fortune.streak.{node_id}.{epoch}").integer(-table.streak_step, table.streak_step)
        walk = walk / 2 ** (1 / max(1, table.streak_halflife)) + step
    return clamp_int(round(walk), -table.streak_cap, table.streak_cap)


async def shift_fortune(
    ctx: TickContext,
    node_id: int,
    amount: int,
    kind: FortuneSourceKind = FortuneSourceKind.PRICE_PAID,
    giver_id: int | None = None,
    *,
    epochs: int | None = None,
) -> None:
    if held(node_id) or not amount:
        return
    ctx.session.add(
        FortuneSourceRow(
            holder_node_id=node_id,
            kind=kind,
            strength=clamp_int(amount, -FORTUNE_CAP, FORTUNE_CAP),
            giver_node_id=giver_id,
            until_epoch=ctx.epoch + (epochs if epochs is not None else ctx.rules.fortune.source_epochs),
            since_epoch=ctx.epoch,
            locked=[],
        )
    )
    await ctx.session.flush()


async def fortune_of(ctx: TickContext, node_id: int) -> int:
    row = await ctx.session.get(FortuneProfileRow, node_id)
    if row is not None:
        return row.fortune
    entity = await ctx.session.get(EntityRow, node_id)
    law = await law_of(ctx, entity.world_id if entity is not None else None)
    return streak_of(ctx, node_id) if STREAKS[law] else 0


def draw_shift(ctx: TickContext, fortune: int) -> float:
    return 1 + fortune / FORTUNE_CAP * ctx.rules.fortune.draw_cap_pct / PERCENT


async def belief_luck(ctx: TickContext, entity: EntityRow) -> int:
    folk = entity.affiliated_entity_id
    if folk is None:
        return 0
    lucky = list(await ctx.session.scalars(select(LuckBeliefRow.lucky).where(LuckBeliefRow.people_entity_id == folk)))
    return sum(BELIEF_STEP if item else -BELIEF_STEP for item in lucky)


async def keep_fortune(ctx: TickContext) -> int:
    alive = or_(FortuneSourceRow.until_epoch.is_(None), FortuneSourceRow.until_epoch >= ctx.epoch)
    by_holder: dict[int, list[FortuneSourceRow]] = defaultdict(list)
    for row in await ctx.session.scalars(select(FortuneSourceRow).where(alive)):
        by_holder[row.holder_node_id].append(row)
    for row in list(await ctx.session.scalars(select(FortuneSourceRow).where(FortuneSourceRow.until_epoch < ctx.epoch))):
        if not row.locked and not held(row.holder_node_id):
            await ctx.session.delete(row)
    kept = 0
    holders = set(by_holder) | set(await ctx.session.scalars(select(FortuneProfileRow.node_id)))
    for node_id in sorted(holders):
        if held(node_id):
            continue
        entity = await ctx.session.get(EntityRow, node_id)
        law = await law_of(ctx, entity.world_id if entity is not None else None)
        sources = [row for row in by_holder.get(node_id, []) if law is not FortuneLaw.DIVINE or DIVINE_SOURCE[row.kind]]
        total_luck = sum(row.strength for row in sources) + (streak_of(ctx, node_id) if STREAKS[law] else 0)
        if law is FortuneLaw.BELIEF_SHAPED and entity is not None:
            total_luck += await belief_luck(ctx, entity)
        profile = await ctx.session.get(FortuneProfileRow, node_id)
        if profile is None:
            profile = FortuneProfileRow(node_id=node_id, fortune=0, streak=0, updated_epoch=ctx.epoch, locked=[])
            ctx.session.add(profile)
        if "fortune" not in profile.locked:
            profile.fortune = clamp_int(total_luck, -FORTUNE_CAP, FORTUNE_CAP)
        if "streak" not in profile.locked:
            profile.streak = streak_of(ctx, node_id) if STREAKS[law] else 0
        profile.updated_epoch = ctx.epoch
        kept += 1
    await ctx.session.flush()
    return kept


async def profile_of(ctx: TickContext, node_id: int) -> FortuneProfileRow:
    row = await ctx.session.get(FortuneProfileRow, node_id)
    if row is None:
        row = FortuneProfileRow(node_id=node_id, fortune=await fortune_of(ctx, node_id), streak=streak_of(ctx, node_id), updated_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
        await ctx.session.flush()
    return row
