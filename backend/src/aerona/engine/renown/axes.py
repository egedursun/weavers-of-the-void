from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.justice import CrimeCaseRow
from aerona.db.tables.law_depth import PardonRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus
from aerona.domain.enums.justice import Verdict as CaseVerdict
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.renown import ReputationAxis
from aerona.engine.context import TickContext
from aerona.engine.recording.record import record
from aerona.engine.renown.book import acclaim, among

POWERFUL = PERCENT // 2


async def communities_near(session: AsyncSession, place_id: int | None) -> list[int]:
    if place_id is None:
        return []
    found = await session.scalars(
        select(EntityRow.id)
        .where(EntityRow.location_id == place_id, EntityRow.status == EntityStatus.CANON, EntityRow.entity_type.in_(sorted(COMMUNITY_TYPES)))
        .order_by(EntityRow.id)
    )
    return [place_id, *found]


async def honour_axis(ctx: TickContext, subject_id: int, axis: ReputationAxis, gain: int, place_id: int | None) -> int:
    communities = [node for node in await communities_near(ctx.session, place_id) if node != subject_id]
    raised = 0
    for community in communities:
        row = await acclaim(ctx.session, subject_id, community, axis, amount=gain, epoch=ctx.epoch)
        if row is None:
            continue
        raised += 1
        await record(ctx, "renown.gained", roles={IncidentRole.SUBJECT: subject_id, IncidentRole.WITNESS: community}, facts={"axis": axis, "value": row.value})
    return raised


async def renown_share(session: AsyncSession, subject_id: int | None, communities: list[int], axis: ReputationAxis) -> float:
    if subject_id is None or not communities:
        return 0.0
    return await among(session, subject_id, communities, frozenset({axis})) / PERCENT


def powerful(entity: EntityRow | None) -> bool:
    return entity is not None and (entity.importance or 0) >= POWERFUL


AXES_FIXUP = "renown.w52"


async def backfill_axes(ctx: TickContext) -> int:
    if await ctx.session.get(AppliedFixupRow, AXES_FIXUP) is not None:
        return 0
    seeded = 0
    pardons = await ctx.session.scalars(select(PardonRow).where(PardonRow.corrupt.is_(False), PardonRow.granter_entity_id.is_not(None)).order_by(PardonRow.id))
    for pardon in list(pardons):
        granter = await ctx.session.get(EntityRow, pardon.granter_entity_id)
        if granter is not None and not held(granter.id):
            seeded += await honour_axis(ctx, granter.id, ReputationAxis.MERCY, ctx.rules.renown.mercy_gain, granter.location_id)
    cases = await ctx.session.scalars(
        select(CrimeCaseRow)
        .where(CrimeCaseRow.verdict == CaseVerdict.GUILTY, CrimeCaseRow.wrongful.is_(False), CrimeCaseRow.judge_entity_id.is_not(None))
        .order_by(CrimeCaseRow.id)
    )
    for case in list(cases):
        if case.judge_entity_id is not None and not held(case.judge_entity_id):
            seeded += await honour_axis(ctx, case.judge_entity_id, ReputationAxis.JUSTICE, ctx.rules.renown.justice_gain, case.settlement_entity_id)
    ctx.session.add(AppliedFixupRow(key=AXES_FIXUP, result={"reputations": seeded}))
    await ctx.session.flush()
    return seeded
