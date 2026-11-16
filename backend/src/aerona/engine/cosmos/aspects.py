from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.dimension_aspects import ELEMENT_PULLS, FORM_PULLS, KIND_FORMS, PERCENT_FIELDS, Pull
from aerona.constants.units import PERCENT
from aerona.db.tables.cosmography import DimensionRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.dimension_aspects import DimensionAspectRow
from aerona.db.write_guard import held
from aerona.domain.enums.arcana import SpellForm
from aerona.domain.enums.cosmography import DimensionElement, DimensionKind
from aerona.engine.context import TickContext
from aerona.engine.primitives.numbers import clamp_percent
from aerona.rules.registry import Rules

TIME_FLOOR = 0.01
ASPECTS_FIXUP = "cosmography.dimension_aspects"


def aspect_row(dimension_id: int, *, strength: int, form: SpellForm | None = None, element: DimensionElement | None = None) -> DimensionAspectRow:
    row = DimensionAspectRow(dimension_id=dimension_id, form=form, element=element, strength=strength)
    row.locked = []
    return row


def first_aspects(rules: Rules, dimension_id: int, kind: DimensionKind, element: DimensionElement | None, form: SpellForm | None) -> list[DimensionAspectRow]:
    strength = rules.dimensions.aspect_strength
    forms = [form] if form is not None else list(KIND_FORMS[kind])
    rows = [aspect_row(dimension_id, strength=strength, form=item) for item in forms]
    if element is not None:
        rows.append(aspect_row(dimension_id, strength=strength, element=element))
    return rows


def pull_of(row: DimensionAspectRow) -> Pull:
    if row.element is not None:
        return ELEMENT_PULLS[row.element]
    return FORM_PULLS[row.form or SpellForm.SPACE]


def apply_pull(rules: Rules, dimension: DimensionRow, pull: Pull, strength: int) -> None:
    if pull.field in dimension.locked:
        return
    if pull.field == "time_factor":
        step = 1 + pull.sign * rules.dimensions.aspect_time_pct * strength / PERCENT / PERCENT
        dimension.time_factor = max(TIME_FLOOR, dimension.time_factor * step)
        return
    moved = getattr(dimension, pull.field) + round(pull.sign * rules.dimensions.aspect_step * strength / PERCENT)
    setattr(dimension, pull.field, clamp_percent(moved) if pull.field in PERCENT_FIELDS else max(0, moved))


async def aspects_of(session: AsyncSession, dimension_id: int) -> list[DimensionAspectRow]:
    return list(await session.scalars(select(DimensionAspectRow).where(DimensionAspectRow.dimension_id == dimension_id).order_by(DimensionAspectRow.id)))


async def keep_aspects(ctx: TickContext, dimension: DimensionRow) -> int:
    if held(dimension.id):
        return 0
    rows = await aspects_of(ctx.session, dimension.id)
    for row in rows:
        apply_pull(ctx.rules, dimension, pull_of(row), row.strength)
    return len(rows)


async def seed_aspects_once(session: AsyncSession, rules: Rules) -> int:
    if await session.get(AppliedFixupRow, ASPECTS_FIXUP) is not None:
        return 0
    given = set(await session.scalars(select(DimensionAspectRow.dimension_id)))
    seeded = 0
    for dimension in list(await session.scalars(select(DimensionRow).order_by(DimensionRow.id))):
        if dimension.id in given or held(dimension.id):
            continue
        for row in first_aspects(rules, dimension.id, dimension.dimension_kind, None, None):
            session.add(row)
            seeded += 1
    session.add(AppliedFixupRow(key=ASPECTS_FIXUP, result={"seeded": seeded}))
    await session.flush()
    return seeded
