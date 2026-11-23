from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.core.errors import ValidationFailedError
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.kin import WillHeirRow, WillRow
from aerona.domain.enums.demography import InheritanceCustom
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.mortal.kin import children_of, parents_of
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import stat_or
from aerona.engine.recording.record import record

HEIRS_LOCK = "heirs"


async def will_of(session: AsyncSession, testator_id: int) -> WillRow | None:
    return await session.scalar(select(WillRow).where(WillRow.testator_node_id == testator_id))


async def heirs_of_will(session: AsyncSession, will_id: int) -> list[WillHeirRow]:
    return list(await session.scalars(select(WillHeirRow).where(WillHeirRow.will_id == will_id).order_by(WillHeirRow.heir_node_id)))


async def make_will(
    ctx: TickContext, testator: EntityRow, heirs: Sequence[tuple[int, int]], *, witnesses: Sequence[int] = (), forged: bool = False, hold: bool | None = None
) -> WillRow:
    if not heirs:
        raise ValidationFailedError("A will names at least one heir.")
    if sum(share for _heir, share in heirs) != PERCENT or any(share <= 0 for _heir, share in heirs):
        raise ValidationFailedError(f"The shares of a will add up to {PERCENT}, each above nothing.")
    if len({heir for heir, _share in heirs}) != len(heirs) or any(heir == testator.id for heir, _share in heirs):
        raise ValidationFailedError("Each heir is named once, and never the one who makes the will.")
    for heir, _share in heirs:
        if await living_entity(ctx.session, heir) is None:
            raise ValidationFailedError("Every heir of a will is alive.")
    will = await will_of(ctx.session, testator.id)
    if will is None:
        will = WillRow(testator_node_id=testator.id, witnesses=list(witnesses), made_epoch=ctx.epoch, forged=forged, locked=[])
        ctx.session.add(will)
        await ctx.session.flush()
    elif HEIRS_LOCK in (will.locked or []):
        raise ValidationFailedError("This will is held as it stands.")
    will.witnesses, will.made_epoch, will.forged, will.read_epoch, will.contested, will.set_aside = list(witnesses), ctx.epoch, forged, None, False, False
    for row in await heirs_of_will(ctx.session, will.id):
        await ctx.session.delete(row)
    await ctx.session.flush()
    ctx.session.add_all(WillHeirRow(will_id=will.id, heir_node_id=heir, share=share, locked=[]) for heir, share in heirs)
    if hold is not None:
        will.locked = [HEIRS_LOCK] if hold else []
    await ctx.session.flush()
    return will


async def remove_will(ctx: TickContext, testator_id: int) -> bool:
    will = await will_of(ctx.session, testator_id)
    if will is None:
        return False
    await ctx.session.delete(will)
    await ctx.session.flush()
    return True


async def siblings_of(session: AsyncSession, mortal_id: int) -> list[int]:
    found: set[int] = set()
    for parent in await parents_of(session, mortal_id):
        found.update(child for child in await children_of(session, parent) if child != mortal_id)
    return sorted(found)


def eldest_first(rows: Sequence[EntityRow]) -> list[EntityRow]:
    return sorted(rows, key=lambda row: (-stat_or(row, "age", 0), row.id))


async def senior_heirs(ctx: TickContext, mortal: EntityRow, children: Sequence[EntityRow]) -> list[EntityRow]:
    siblings = [row for sibling in await siblings_of(ctx.session, mortal.id) if (row := await living_entity(ctx.session, sibling)) is not None]
    if not siblings:
        return eldest_first(children)[:1]
    heir = eldest_first(siblings)[0]
    if children and ctx.rng(seed_of("seniority", mortal.id, ctx.epoch)).chance(ctx.rules.inheritance.seniority_dispute_pct):
        claimant = eldest_first(children)[0]
        await record(
            ctx,
            "inheritance.disputed",
            roles={IncidentRole.PREDECESSOR: mortal.id, IncidentRole.HEIR: heir.id, IncidentRole.ACCUSER: claimant.id},
            facts={"custom": InheritanceCustom.SENIORITY},
        )
    return [heir]


async def read_will(ctx: TickContext, mortal: EntityRow, children: Sequence[EntityRow], custom: InheritanceCustom) -> list[tuple[EntityRow, int]] | None:
    will = await will_of(ctx.session, mortal.id)
    if will is None or will.set_aside:
        return None
    named = [
        (row, line.share) for line in await heirs_of_will(ctx.session, will.id) if (row := await living_entity(ctx.session, line.heir_node_id)) is not None
    ]
    will.read_epoch = ctx.epoch
    await record(
        ctx,
        "inheritance.will_read",
        roles={IncidentRole.PREDECESSOR: mortal.id, IncidentRole.HEIR: [row.id for row, _share in named]},
        facts={"heirs": len(named)},
    )
    chance = ctx.rules.inheritance.will_contest_pct * (1 if custom is InheritanceCustom.DESIGNATED else 2)
    left_out = [child for child in eldest_first(children) if child.id not in {row.id for row, _share in named}]
    for child in left_out:
        if not ctx.rng(seed_of("will.contest", will.id, child.id)).chance(chance):
            continue
        will.contested = True
        will.set_aside = will.forged or custom is not InheritanceCustom.DESIGNATED
        await record(
            ctx,
            "inheritance.will_contested",
            roles={IncidentRole.PREDECESSOR: mortal.id, IncidentRole.ACCUSER: child.id},
            facts={"set_aside": int(will.set_aside), "forged": int(will.forged)},
        )
        break
    total = sum(share for _row, share in named)
    if will.set_aside or not named or total <= 0:
        return None
    return [(row, round(share * PERCENT / total)) for row, share in named]


def allot(count: int, shares: Sequence[int]) -> list[int]:
    given = [0] * len(shares)
    order: list[int] = []
    for _ in range(count):
        index = max(range(len(shares)), key=lambda at: (shares[at] * (len(order) + 1) / PERCENT - given[at], -at))
        given[index] += 1
        order.append(index)
    return order
