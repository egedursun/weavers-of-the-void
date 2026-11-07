from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.renown import GLORIOUS, INFAMOUS
from aerona.constants.units import PERCENT
from aerona.db.read_memo import memoized
from aerona.db.tables.renown import ReputationRow
from aerona.db.write_guard import write_blocked
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.renown import ReputationAxis
from aerona.engine.primitives.numbers import clamp_int

REPUTATION_KEY = "reputations"


async def reputation_row(session: AsyncSession, subject_id: int, community_id: int, axis: ReputationAxis, skill: SkillKind | None) -> ReputationRow | None:
    query = select(ReputationRow).where(
        ReputationRow.subject_node_id == subject_id,
        ReputationRow.community_node_id == community_id,
        ReputationRow.axis == axis,
        ReputationRow.skill.is_(None) if skill is None else ReputationRow.skill == skill,
    )
    return await session.scalar(query.limit(1))


async def acclaim(
    session: AsyncSession, subject_id: int, community_id: int, axis: ReputationAxis, *, amount: float, epoch: int, skill: SkillKind | None = None
) -> ReputationRow | None:
    if not round(amount) or subject_id == community_id or write_blocked(subject_id, REPUTATION_KEY):
        return None
    row = await reputation_row(session, subject_id, community_id, axis, skill)
    if row is None:
        row = ReputationRow(subject_node_id=subject_id, community_node_id=community_id, axis=axis, skill=skill, value=0, heard_epoch=epoch, locked=[])
        session.add(row)
    if "value" not in row.locked:
        row.value = clamp_int(row.value + amount, 0, PERCENT)
        row.heard_epoch = epoch
    await session.flush()
    return row


async def reputations_of(session: AsyncSession, subject_id: int) -> list[ReputationRow]:
    query = select(ReputationRow).where(ReputationRow.subject_node_id == subject_id).order_by(ReputationRow.value.desc(), ReputationRow.id)
    return list(await session.scalars(query))


async def views_held_by(session: AsyncSession, community_id: int) -> list[ReputationRow]:
    query = select(ReputationRow).where(ReputationRow.community_node_id == community_id).order_by(ReputationRow.value.desc(), ReputationRow.id)
    return list(await session.scalars(query))


@memoized(ReputationRow)
async def views_of(session: AsyncSession, community_id: int) -> tuple[ReputationRow, ...]:
    return tuple(await session.scalars(select(ReputationRow).where(ReputationRow.community_node_id == community_id).order_by(ReputationRow.id)))


async def standing_with(session: AsyncSession, subject_id: int, community_id: int) -> tuple[int, int]:
    rows = [row for row in await views_of(session, community_id) if row.subject_node_id == subject_id]
    glory = infamy = 0
    for row in rows:
        if row.axis in GLORIOUS:
            glory = max(glory, row.value)
        elif row.axis in INFAMOUS:
            infamy = max(infamy, row.value)
    return glory, infamy


def aggregate(rows: list[ReputationRow]) -> tuple[int, int]:
    glory: dict[int, int] = defaultdict(int)
    infamy: dict[int, int] = defaultdict(int)
    for row in rows:
        if row.axis in GLORIOUS:
            glory[row.community_node_id] = max(glory[row.community_node_id], row.value)
        elif row.axis in INFAMOUS:
            infamy[row.community_node_id] = max(infamy[row.community_node_id], row.value)
    spread = max(len(glory), len(infamy), 1)
    return clamp_int(sum(glory.values()) / spread + len(glory), 0, PERCENT), clamp_int(sum(infamy.values()) / spread + len(infamy), 0, PERCENT)


async def among(session: AsyncSession, subject_id: int, communities: list[int], axes: frozenset[ReputationAxis]) -> int:
    if not communities:
        return 0
    rows = await session.scalars(
        select(ReputationRow).where(
            ReputationRow.subject_node_id == subject_id, ReputationRow.community_node_id.in_(communities), ReputationRow.axis.in_(list(axes))
        )
    )
    best: dict[int, int] = defaultdict(int)
    for row in rows:
        best[row.community_node_id] = max(best[row.community_node_id], row.value)
    return round(sum(best.values()) / len(communities))
