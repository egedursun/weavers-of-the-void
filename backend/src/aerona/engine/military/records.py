from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any

from sqlalchemy import JSON, Boolean, Float, Integer, String, select
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapper, class_mapper

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.grammar import an
from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.db.tables.economy import WorldMaterialRow
from aerona.db.tables.military import (
    ArmyOfficerRow,
    ArmyProfileRow,
    ArmyTemplateRow,
    ArmyUnitRow,
    CaptiveCohortRow,
    FeudRow,
    MercenaryContractRow,
    OccupationRow,
    PeaceTermRow,
    SpyAgentRow,
    SpyNetworkRow,
    UnitDesignRow,
    WarAimRow,
)
from aerona.db.tables.warfare import BattleRow, CaptiveRow, CasusBelliRow, SiegeRow, WarProductionRow, WarRow
from aerona.domain.enums.economy import MaterialSlot
from aerona.domain.enums.military import UnitKind
from aerona.engine.context import TickContext
from aerona.engine.economy.materials import key_parts, set_node_material
from aerona.engine.military.units import stacks_of, sync
from aerona.engine.polity.control import lock
from aerona.engine.primitives.queries import living_entity

UNIT_KINDS = frozenset(kind.value for kind in UnitKind)
INTEGER, NUMBER, FLAG, CHOICE, TEXT, IDS, WORDS = "integer", "number", "flag", "choice", "text", "ids", "words"
Scalar = int | float | str | bool | None
Values = Mapping[str, Any]


@dataclass(frozen=True)
class RecordKind:
    key: str
    model: type[Any]
    label: str
    scope: str | None
    required: tuple[str, ...]
    creatable: bool = True
    deletable: bool = True
    hidden: tuple[str, ...] = ()


KINDS: dict[str, RecordKind] = {
    kind.key: kind
    for kind in (
        RecordKind("unit_design", UnitDesignRow, "Unit design", "owner_entity_id", ("name", "base_kind")),
        RecordKind("stack", ArmyUnitRow, "Unit stack", "army_entity_id", ("army_entity_id", "kind", "count")),
        RecordKind("army_profile", ArmyProfileRow, "Army orders", "army_entity_id", ("army_entity_id",), creatable=False, deletable=False),
        RecordKind("officer", ArmyOfficerRow, "Army officer", "army_entity_id", ("army_entity_id", "mortal_entity_id", "role")),
        RecordKind("contract", MercenaryContractRow, "Mercenary contract", "employer_entity_id", ("employer_entity_id", "soldiers", "pay_per_season")),
        RecordKind("war", WarRow, "War", "id", (), creatable=False, deletable=False, hidden=("event_entity_id", "world_id")),
        RecordKind("siege", SiegeRow, "Siege", "war_id", ("war_id", "besieged_entity_id", "besieger_entity_id")),
        RecordKind("war_aim", WarAimRow, "War aim", "war_id", ("war_id", "side_entity_id", "kind")),
        RecordKind("occupation", OccupationRow, "Occupation", "occupier_entity_id", ("region_entity_id", "occupier_entity_id")),
        RecordKind("battle", BattleRow, "Battle", "war_id", (), creatable=False),
        RecordKind("captive_cohort", CaptiveCohortRow, "Captive cohort", "captor_entity_id", ("captor_entity_id", "count")),
        RecordKind("captive", CaptiveRow, "Captive", "captor_entity_id", (), creatable=False),
        RecordKind("peace_term", PeaceTermRow, "Peace term", "war_id", ("war_id", "kind")),
        RecordKind("spy_network", SpyNetworkRow, "Spy network", "owner_entity_id", ("owner_entity_id", "target_entity_id")),
        RecordKind("spy_agent", SpyAgentRow, "Spy agent", "network_id", ("network_id",)),
        RecordKind("feud", FeudRow, "Feud", "first_entity_id", ("first_entity_id", "second_entity_id")),
        RecordKind("army_template", ArmyTemplateRow, "Army template", "polity_entity_id", ("polity_entity_id", "name")),
        RecordKind("casus_belli", CasusBelliRow, "Casus belli", "holder_entity_id", ("holder_entity_id", "target_entity_id", "kind")),
        RecordKind("war_production", WarProductionRow, "War production line", "community_entity_id", ("community_entity_id", "commodity")),
        RecordKind("vessel", VesselProfileRow, "Vessel", "entity_id", (), creatable=False, deletable=False),
    )
}
SKIPPED = frozenset({"locked", "created_at"})


@dataclass(frozen=True)
class Column:
    name: str
    kind: str
    options: tuple[str, ...]
    nullable: bool
    required: bool


def kind_of(key: str) -> RecordKind:
    found = KINDS.get(key)
    if found is None:
        raise NotFoundError(f"{key.replace('_', ' ')} is not a military record.")
    return found


def mapper_of(kind: RecordKind) -> Mapper[Any]:
    return class_mapper(kind.model)


def primary(kind: RecordKind) -> str:
    keys = list(mapper_of(kind).primary_key)
    return mapper_of(kind).get_property_by_column(keys[0]).key


SQL_KINDS: tuple[tuple[type[Any], str], ...] = ((Boolean, FLAG), (Integer, INTEGER), (Float, NUMBER), (String, TEXT), (JSON, WORDS))


def column_type(mapper: Mapper[Any], name: str) -> tuple[str, tuple[str, ...]]:
    sql = mapper.columns[name].type
    if isinstance(sql, SqlEnum):
        return CHOICE, tuple(str(item) for item in sql.enums)
    return next((sort for sql_type, sort in SQL_KINDS if isinstance(sql, sql_type)), TEXT), ()


def columns(kind: RecordKind) -> list[Column]:
    mapper = mapper_of(kind)
    key = primary(kind)
    found: list[Column] = []
    for attribute in mapper.column_attrs:
        name = attribute.key
        if name in SKIPPED or name in kind.hidden or (name == key and name == "id"):
            continue
        sort, options = column_type(mapper, name)
        found.append(Column(name, sort, options, bool(mapper.columns[name].nullable), name in kind.required))
    return found


def choice(kind: RecordKind, column: Column, value: object) -> Any:
    if str(value) not in column.options:
        raise ValidationFailedError(f"{column.name.replace('_', ' ').capitalize()} must be one of {', '.join(column.options)}.")
    enum_class = getattr(mapper_of(kind).columns[column.name].type, "enum_class", None)
    return enum_class(str(value)) if enum_class is not None else str(value)


def flag(kind: RecordKind, column: Column, value: object) -> Any:
    if not isinstance(value, bool):
        raise ValidationFailedError(f"{column.name.replace('_', ' ').capitalize()} is yes or no.")
    return value


def whole(kind: RecordKind, column: Column, value: object) -> Any:
    if isinstance(value, bool) or not isinstance(value, int | float) or int(value) != value:
        raise ValidationFailedError(f"{column.name.replace('_', ' ').capitalize()} must be a whole number.")
    return int(value)


def number(kind: RecordKind, column: Column, value: object) -> Any:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValidationFailedError(f"{column.name.replace('_', ' ').capitalize()} must be a number.")
    return float(value)


def words(kind: RecordKind, column: Column, value: object) -> Any:
    if not isinstance(value, list | dict):
        raise ValidationFailedError(f"{column.name.replace('_', ' ').capitalize()} must be a list.")
    return value


def text(kind: RecordKind, column: Column, value: object) -> Any:
    return str(value)


COERCERS = {CHOICE: choice, FLAG: flag, INTEGER: whole, NUMBER: number, WORDS: words, TEXT: text}


def coerce(kind: RecordKind, column: Column, value: object) -> Any:
    if value is None:
        if not column.nullable:
            raise ValidationFailedError(f"{column.name.replace('_', ' ').capitalize()} cannot be left empty.")
        return None
    return COERCERS.get(column.kind, text)(kind, column, value)


def assign(kind: RecordKind, row: Any, values: Values) -> list[str]:
    known = {column.name: column for column in columns(kind)}
    changed: list[str] = []
    for name, value in values.items():
        column = known.get(name)
        if column is None:
            raise ValidationFailedError(f"{kind.label} has no {name.replace('_', ' ')}.")
        setattr(row, name, coerce(kind, column, value))
        changed.append(name)
    return changed


def scalar(value: object) -> Scalar | list[Any] | dict[str, Any]:
    if isinstance(value, Enum):
        return str(value.value)
    if isinstance(value, list | dict):
        return value
    return value if isinstance(value, int | float | str | bool) or value is None else str(value)


def as_dict(kind: RecordKind, row: Any) -> dict[str, Any]:
    return {column.name: scalar(getattr(row, column.name)) for column in columns(kind)} | {"id": scalar(getattr(row, primary(kind)))}


async def fetch(session: AsyncSession, kind: RecordKind, key: int) -> Any:
    row = await session.get(kind.model, key)
    if row is None:
        raise NotFoundError(f"No such {kind.label.lower()}.")
    return row


async def rows_of(session: AsyncSession, kind: RecordKind, scope_id: int | None) -> list[Any]:
    statement = select(kind.model)
    if scope_id is not None and kind.scope is not None:
        statement = statement.where(getattr(kind.model, kind.scope) == scope_id)
    return list(await session.scalars(statement.order_by(getattr(kind.model, primary(kind)))))


async def after_change(ctx: TickContext, kind: RecordKind, row: Any) -> None:
    if kind.key == "stack":
        army = await living_entity(ctx.session, row.army_entity_id)
        if army is not None:
            await ctx.session.flush()
            sync(army, await stacks_of(ctx.session, army.id), ctx.rules)
    if kind.key == "siege" and row.status.value != "ongoing" and row.ended_epoch is None:
        row.ended_epoch = ctx.epoch
    if kind.key == "army_template":
        row.composition = mix_of(row.composition)


def mix_of(value: object) -> dict[str, int]:
    if not isinstance(value, dict):
        raise ValidationFailedError("A template's composition maps each kind of soldier to its share.")
    unknown = sorted(str(key) for key in value if str(key) not in UNIT_KINDS)
    if unknown:
        raise ValidationFailedError(f"{', '.join(unknown)} is not a kind of soldier.")
    shares = {str(key): share for key, share in value.items()}
    if any(isinstance(share, bool) or not isinstance(share, int) or share < 0 for share in shares.values()):
        raise ValidationFailedError("Each share of a template is a whole number of at least 0.")
    return {key: share for key, share in sorted(shares.items()) if share > 0}


async def create_record(ctx: TickContext, key: str, values: Values) -> Any:
    kind = kind_of(key)
    if not kind.creatable:
        raise ValidationFailedError(f"{an(kind.label.lower(), capital=True)} is created from its own action.")
    missing = [name for name in kind.required if values.get(name) is None]
    if missing:
        raise ValidationFailedError(f"{kind.label} needs {', '.join(item.replace('_', ' ') for item in missing)}.")
    row = kind.model()
    for column in columns(kind):
        default = mapper_of(kind).columns[column.name].default
        argument = getattr(default, "arg", None)
        if default is not None and getattr(default, "is_scalar", False):
            setattr(row, column.name, argument)
        elif default is not None and getattr(default, "is_callable", False) and callable(argument):
            setattr(row, column.name, argument(None))
    for epoch_column in ("since_epoch", "started_epoch", "taken_epoch", "created_epoch", "epoch"):
        if epoch_column in {column.name for column in columns(kind)} and epoch_column not in values:
            setattr(row, epoch_column, ctx.epoch)
    assign(kind, row, values)
    if hasattr(row, "locked"):
        row.locked = []
    ctx.session.add(row)
    await ctx.session.flush()
    await after_change(ctx, kind, row)
    await ctx.session.flush()
    return row


async def rig_slots(ctx: TickContext, row: VesselProfileRow, changed: list[str]) -> None:
    for name, slot in (("hull_material", MaterialSlot.HULL), ("fabric_material", MaterialSlot.FABRIC)):
        if name in changed:
            material, world_material_id = key_parts(getattr(row, name))
            if world_material_id is not None and await ctx.session.get(WorldMaterialRow, world_material_id) is None:
                raise ValidationFailedError("No such substance in this world.")
            await set_node_material(ctx.session, row.entity_id, slot, material, world_material_id, force=True)


async def edit_record(ctx: TickContext, key: str, record_id: int, values: Values, *, hold: bool = True) -> Any:
    kind = kind_of(key)
    row = await fetch(ctx.session, kind, record_id)
    changed = assign(kind, row, values)
    if kind.key == "vessel":
        await rig_slots(ctx, row, changed)
    if hold and hasattr(row, "locked"):
        for name in changed:
            row.locked = lock(list(row.locked or []), name)
    await after_change(ctx, kind, row)
    await ctx.session.flush()
    return row


async def release_record(ctx: TickContext, key: str, record_id: int, names: list[str]) -> Any:
    kind = kind_of(key)
    row = await fetch(ctx.session, kind, record_id)
    if not hasattr(row, "locked"):
        raise ValidationFailedError(f"{an(kind.label.lower(), capital=True)} keeps no holds.")
    row.locked = [item for item in (row.locked or []) if item not in set(names)] if names else []
    await ctx.session.flush()
    return row


async def delete_record(ctx: TickContext, key: str, record_id: int) -> int | None:
    kind = kind_of(key)
    if not kind.deletable:
        raise ValidationFailedError(f"{an(kind.label.lower(), capital=True)} cannot be struck out; retire it instead.")
    row = await fetch(ctx.session, kind, record_id)
    scope = getattr(row, kind.scope) if kind.scope is not None else None
    await ctx.session.delete(row)
    await ctx.session.flush()
    if kind.key == "stack" and scope is not None:
        army = await living_entity(ctx.session, scope)
        if army is not None:
            sync(army, await stacks_of(ctx.session, army.id), ctx.rules)
    return scope if isinstance(scope, int) else None


def battle_field(battle: BattleRow, names: dict[int, str]) -> str:
    notes: list[str] = []
    if battle.width:
        notes.append(f"front of {battle.width:,}")
    if battle.reserves_committed:
        notes.append(f"{battle.reserves_committed:,} reserves committed")
    if battle.planned_entity_id is not None:
        notes.append(f"planned by {names.get(battle.planned_entity_id, '?')}")
    if battle.trap_entity_id is not None:
        notes.append(f"trap sprung by {names.get(battle.trap_entity_id, '?')}")
    if battle.feint:
        notes.append("a feint pinned the reserves")
    if battle.command_collapsed_entity_id is not None:
        notes.append(f"{names.get(battle.command_collapsed_entity_id, '?')} lost its commander")
    if battle.salvaged:
        notes.append(f"{battle.salvaged:,} arms salvaged")
    if battle.standard_entity_id is not None:
        notes.append(f"standard {names.get(battle.standard_entity_id, '?')} taken")
    return "; ".join(notes)
