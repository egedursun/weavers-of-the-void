from collections import defaultdict
from collections.abc import Mapping

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.culture import IdeologyAdherentRow, IdeologyProfileRow
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.society_depth import DriftCauseRow, DriftImpositionRow
from aerona.domain.enums.entity import EntityStatus, EntityType, MortalRole
from aerona.domain.enums.mind import PressureKind, ValueAxis
from aerona.domain.enums.society_depth import DriftCause
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.mind.book import pressures_of
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.numbers import round_half_up
from aerona.rules.registry import Rules

SCHOLAR_ROLES = (MortalRole.SAGE, MortalRole.SCRIBE)
Shift = dict[ValueAxis, float]
Causes = dict[DriftCause, Shift]


def empty() -> Causes:
    return defaultdict(lambda: defaultdict(float))


def add_shift(causes: Causes, cause: DriftCause, axis: ValueAxis, amount: float) -> None:
    causes[cause][axis] += amount


def pull_shift(current: Mapping[ValueAxis, int], source: Mapping[ValueAxis, int] | None, share_pct: float) -> Shift:
    if not source:
        return {}
    return {axis: (source.get(axis, 0) - current.get(axis, 0)) * share_pct / PERCENT for axis in ValueAxis}


async def cohesion_of(session: AsyncSession, rules: Rules, community: EntityRow) -> int:
    people = await people_of(session, community)
    culture = await session.get(PeopleCultureRow, people.id) if people is not None else None
    return culture.cohesion if culture is not None else rules.peoples.cohesion_base


def lost_war_sign(rules: Rules, cohesion: int) -> int:
    return 1 if cohesion >= rules.culture_drift.lost_war_cohesion else -1


async def famine_shift(session: AsyncSession, rules: Rules, community_id: int) -> float:
    hunger = (await pressures_of(session, community_id)).get(PressureKind.HUNGER, 0)
    return float(rules.culture_drift.famine_kinship) if hunger >= rules.culture_drift.famine_hunger else 0.0


async def scholars_of(session: AsyncSession, community_id: int) -> list[int]:
    statement = select(EntityRow.id).where(
        EntityRow.entity_type == EntityType.MORTAL,
        EntityRow.status == EntityStatus.CANON,
        EntityRow.mortal_role.in_(SCHOLAR_ROLES),
        or_(await present_among(session, [community_id]), EntityRow.affiliated_entity_id == community_id),
    )
    return list(await session.scalars(statement.order_by(EntityRow.id)))


async def ideology_shift(session: AsyncSession, rules: Rules, community_id: int) -> Shift:
    holders = [community_id, *await scholars_of(session, community_id)]
    rows = list(await session.scalars(select(IdeologyAdherentRow).where(IdeologyAdherentRow.adherent_entity_id.in_(holders))))
    if not rows:
        return {}
    raw: Shift = defaultdict(float)
    for row in rows:
        profile = await session.get(IdeologyProfileRow, row.ideology_entity_id)
        if profile is None:
            continue
        for key, delta in profile.value_delta.items():
            try:
                axis = ValueAxis(key)
            except ValueError:
                continue
            raw[axis] += delta * row.strength / PERCENT
    return {axis: value / len(rows) * rules.culture_drift.ideology_pull_pct / PERCENT for axis, value in raw.items()}


async def impositions_of(session: AsyncSession, community_id: int) -> list[DriftImpositionRow]:
    statement = select(DriftImpositionRow).where(DriftImpositionRow.community_entity_id == community_id).order_by(DriftImpositionRow.id)
    return list(await session.scalars(statement))


async def spend_impositions(session: AsyncSession, rows: list[DriftImpositionRow]) -> None:
    for row in rows:
        if row.epochs_left <= 1:
            await session.delete(row)
        else:
            row.epochs_left -= 1


async def record_causes(ctx: TickContext, community_id: int, causes: Causes, rate: float) -> None:
    statement = select(DriftCauseRow).where(DriftCauseRow.community_entity_id == community_id)
    found = {(row.cause, row.axis): row for row in await ctx.session.scalars(statement)}
    for stale in found.values():
        stale.amount = 0
    for cause, shift in causes.items():
        for axis, value in shift.items():
            applied = round_half_up(value * rate / PERCENT)
            if applied == 0:
                continue
            row = found.get((cause, axis))
            if row is None:
                row = DriftCauseRow(community_entity_id=community_id, cause=cause, axis=axis, amount=0, total=0, epoch=ctx.epoch)
                ctx.session.add(row)
                found[(cause, axis)] = row
            row.amount = applied
            row.total += applied
            row.epoch = ctx.epoch
