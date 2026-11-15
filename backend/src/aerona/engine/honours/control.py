from collections.abc import Mapping
from dataclasses import dataclass, field

from sqlalchemy import select

from aerona.core.errors import ValidationFailedError
from aerona.db.base import Base
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.honours import (
    NAMED_UNIT_FIELDS,
    UNIT_HONOUR_FIELDS,
    VETERAN_GRANT_FIELDS,
    NamedUnitRow,
    UnitHonourRow,
    VeteranGrantRow,
)
from aerona.db.tables.military import ArmyUnitRow
from aerona.domain.enums.entity import EntityType
from aerona.engine.collective.control import saved
from aerona.engine.context import TickContext
from aerona.engine.cycles.control import node_exists
from aerona.engine.divine.control import apply
from aerona.engine.gatherings.control import Values, allowed, found
from aerona.engine.honours.veterans import VeteranTally, keep_veterans


@dataclass(frozen=True)
class Kind:
    table: type[Base]
    fields: tuple[str, ...]
    label: str


KINDS: Mapping[str, Kind] = {
    "named_unit": Kind(NamedUnitRow, NAMED_UNIT_FIELDS, "named unit"),
    "unit_honour": Kind(UnitHonourRow, UNIT_HONOUR_FIELDS, "honour on a standard"),
    "veteran_grant": Kind(VeteranGrantRow, VETERAN_GRANT_FIELDS, "grant to veterans"),
}
STAMPS = {"named_unit": "formed_epoch", "unit_honour": "epoch", "veteran_grant": "epoch"}


async def checked(ctx: TickContext, values: Values) -> None:
    for name, value in values.items():
        if isinstance(value, int) and name.endswith(("_node_id", "_entity_id")):
            await node_exists(ctx, value, name.removesuffix("_id").replace("_", " "))
    unit = values.get("unit_id")
    if isinstance(unit, int) and await ctx.session.get(ArmyUnitRow, unit) is None:
        raise ValidationFailedError("No such unit of an army.")
    named = values.get("named_unit_id")
    if isinstance(named, int) and await ctx.session.get(NamedUnitRow, named) is None:
        raise ValidationFailedError("No such named unit.")
    polity = values.get("polity_entity_id")
    entity = await ctx.session.get(EntityRow, polity) if isinstance(polity, int) else None
    if isinstance(polity, int) and (entity is None or entity.entity_type is not EntityType.POLITY):
        raise ValidationFailedError("Veterans are granted land or pensions by a realm.")


async def create_record(ctx: TickContext, name: str, values: Values) -> Base:
    kind = KINDS[name]
    await checked(ctx, values)
    unit = values.get("unit_id")
    standing = (
        await ctx.session.scalar(select(NamedUnitRow).where(NamedUnitRow.unit_id == unit).limit(1)) if name == "named_unit" and unit is not None else None
    )
    if standing is not None:
        apply(standing, allowed({key: value for key, value in values.items() if key != "unit_id"}, kind.fields, kind.label), [])
        await ctx.session.flush()
        return standing
    return await saved(ctx, kind.table(**values, **{STAMPS[name]: ctx.epoch}, locked=[]))


async def edit_record(ctx: TickContext, name: str, key: int, values: Values, release: list[str]) -> Base:
    kind = KINDS[name]
    await checked(ctx, values)
    row = apply(await found(ctx, kind.table, key, kind.label), allowed(values, kind.fields, kind.label), release)
    await ctx.session.flush()
    return row


async def delete_record(ctx: TickContext, name: str, key: int) -> None:
    kind = KINDS[name]
    await ctx.session.delete(await found(ctx, kind.table, key, kind.label))
    await ctx.session.flush()


@dataclass
class HonoursRun:
    veterans: VeteranTally = field(default_factory=VeteranTally)


async def run_honours(ctx: TickContext) -> HonoursRun:
    tally = HonoursRun()
    await keep_veterans(ctx, tally.veterans)
    return tally
