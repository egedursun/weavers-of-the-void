from collections.abc import Mapping
from dataclasses import dataclass

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.economy import WorkshopDesignRow, WorkshopRow
from aerona.domain.enums.economy import WorkshopKind
from aerona.engine.context import TickContext
from aerona.engine.primitives.numbers import clamp_int, round_half_up

DESIGN_FIELDS = ("output_pct", "capacity_pct", "store_pct", "quality_bonus")
SCALE_MAX = 500


def capacity_scale(design: WorkshopDesignRow | None) -> float:
    return design.capacity_pct / PERCENT if design is not None else 1.0


def output_scale(design: WorkshopDesignRow | None) -> float:
    return design.output_pct / PERCENT if design is not None else 1.0


def quality_bonus(design: WorkshopDesignRow | None) -> int:
    return design.quality_bonus if design is not None else 0


def workshop_store_units(workshop: WorkshopRow | None, design: WorkshopDesignRow | None, per_level: int) -> int:
    if workshop is None:
        return 0
    return round_half_up(workshop.level * per_level * (design.store_pct / PERCENT if design is not None else 1.0))


async def designs_by_id(session: AsyncSession) -> dict[int, WorkshopDesignRow]:
    return {row.id: row for row in await session.scalars(select(WorkshopDesignRow).order_by(WorkshopDesignRow.id))}


@dataclass(frozen=True)
class NewDesign:
    world_id: int
    base_kind: WorkshopKind
    name: str
    values: Mapping[str, int]
    description: str | None = None


def checked(values: Mapping[str, int]) -> dict[str, int]:
    unknown = set(values) - set(DESIGN_FIELDS)
    if unknown:
        raise ValidationFailedError(f"Unknown workshop fields: {', '.join(sorted(unknown))}.")
    found: dict[str, int] = {}
    for key, value in values.items():
        high = PERCENT if key == "quality_bonus" else SCALE_MAX
        if not 0 <= value <= high:
            raise ValidationFailedError(f"{key.replace('_', ' ').capitalize()} runs from 0 to {high}.")
        found[key] = value
    return found


async def create_design(ctx: TickContext, design: NewDesign) -> WorkshopDesignRow:
    if not design.name.strip():
        raise ValidationFailedError("A workshop design needs a name.")
    values = {"output_pct": PERCENT, "capacity_pct": PERCENT, "store_pct": PERCENT, "quality_bonus": 0} | checked(design.values)
    row = WorkshopDesignRow(
        world_id=design.world_id,
        base_kind=design.base_kind,
        name=design.name.strip(),
        description=(design.description or "").strip() or None,
        created_epoch=ctx.epoch,
        **values,
    )
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def design_row(ctx: TickContext, design_id: int) -> WorkshopDesignRow:
    row = await ctx.session.get(WorkshopDesignRow, design_id)
    if row is None:
        raise NotFoundError("No such workshop design.")
    return row


async def edit_design(
    ctx: TickContext, design_id: int, values: Mapping[str, int], *, name: str | None, description: str | None, hold: bool | None
) -> WorkshopDesignRow:
    row = await design_row(ctx, design_id)
    for key, value in checked(values).items():
        setattr(row, key, value)
    if name is not None:
        if not name.strip():
            raise ValidationFailedError("A workshop design needs a name.")
        row.name = name.strip()
    if description is not None:
        row.description = description.strip() or None
    if hold is not None:
        row.held = hold
    await ctx.session.flush()
    return row


async def delete_design(ctx: TickContext, design_id: int) -> str:
    row = await design_row(ctx, design_id)
    name = row.name
    await ctx.session.execute(update(WorkshopRow).where(WorkshopRow.design_id == row.id).values(design_id=None))
    await ctx.session.delete(row)
    await ctx.session.flush()
    return name


async def assign_design(ctx: TickContext, workshop: WorkshopRow, design_id: int) -> None:
    if design_id <= 0:
        workshop.design_id = None
        return
    row = await design_row(ctx, design_id)
    if row.base_kind is not workshop.kind:
        raise ValidationFailedError("A design is built on the workshop kind it was drawn for.")
    workshop.design_id = row.id


def clamp_quality(value: int) -> int:
    return clamp_int(value, 0, PERCENT)
