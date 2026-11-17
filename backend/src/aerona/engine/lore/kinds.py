from collections.abc import Mapping
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.core.grammar import an, spoken
from aerona.db.read_memo import memoized
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.culture import CustomKindRow, HolderCustomTechniqueRow
from aerona.domain.enums.body import DamageType
from aerona.domain.enums.culture import (
    CustomCatalog,
    IdeologyTenet,
    ItemClass,
    LegendArchetype,
    RiteEffectKind,
    SummonForm,
    Technique,
    TraditionEffectKind,
    TraditionFunction,
)
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.society import Commodity, KnowledgeBranch, SocialClass
from aerona.engine.context import TickContext

PERCENT = 100
MAX_LEVEL = 10
MAX_SCALE = 500


class KindParams(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)


class TechniqueParams(KindParams):
    branch: KnowledgeBranch | None = None
    level: int | None = Field(default=None, ge=1, le=MAX_LEVEL)


class TenetParams(KindParams):
    values: dict[ValueAxis, int] = Field(default_factory=dict)
    appeal: dict[SocialClass, int] = Field(default_factory=dict)


class TraditionKindParams(KindParams):
    cost: dict[Commodity, int] = Field(default_factory=dict)
    effects: dict[TraditionEffectKind, int] = Field(default_factory=dict)
    values: dict[ValueAxis, int] = Field(default_factory=dict)


class ArchetypeParams(KindParams):
    moral: dict[ValueAxis, int] = Field(default_factory=dict)


class ItemClassParams(KindParams):
    damage_type: DamageType | None = None
    reach: int | None = Field(default=None, ge=0, le=PERCENT)
    coverage: int | None = Field(default=None, ge=0, le=PERCENT)
    weight: int | None = Field(default=None, ge=0, le=PERCENT)


class RiteEffectParams(KindParams):
    magnitude_pct: int = Field(default=PERCENT, ge=0, le=MAX_SCALE)
    damage_type: DamageType | None = None
    summon_form: SummonForm | None = None


PARAMS: dict[CustomCatalog, type[KindParams]] = {
    CustomCatalog.TECHNIQUE: TechniqueParams,
    CustomCatalog.TENET: TenetParams,
    CustomCatalog.TRADITION_KIND: TraditionKindParams,
    CustomCatalog.ARCHETYPE: ArchetypeParams,
    CustomCatalog.ITEM_CLASS: ItemClassParams,
    CustomCatalog.RITE_EFFECT: RiteEffectParams,
}
BASES: dict[CustomCatalog, type[StrEnum]] = {
    CustomCatalog.TECHNIQUE: Technique,
    CustomCatalog.TENET: IdeologyTenet,
    CustomCatalog.TRADITION_KIND: TraditionFunction,
    CustomCatalog.ARCHETYPE: LegendArchetype,
    CustomCatalog.ITEM_CLASS: ItemClass,
    CustomCatalog.RITE_EFFECT: RiteEffectKind,
}
EDITABLE = frozenset({"name", "description", "base", "params", "world_id"})


def params_of[M: KindParams](row: CustomKindRow, model: type[M]) -> M:
    return model.model_validate(row.params or {})


def checked_params(catalog: CustomCatalog, params: Mapping[str, Any]) -> dict[str, Any]:
    try:
        return PARAMS[catalog].model_validate(dict(params)).model_dump(mode="json", exclude_none=True)
    except ValidationError as error:
        raise ValidationFailedError(f"Those are not the parameters of {an(spoken(catalog))}: {error.errors()[0]['msg']}.") from error


def checked_base(catalog: CustomCatalog, base: str) -> str:
    try:
        return BASES[catalog](base).value
    except ValueError as error:
        raise ValidationFailedError(f"{base} is not a known {spoken(catalog)} to build on.") from error


def checked_name(name: str) -> str:
    text = name.strip()
    if not text:
        raise ValidationFailedError("A new kind needs a name.")
    return text


async def kind_of(session: AsyncSession, kind_id: int | None, catalog: CustomCatalog) -> CustomKindRow | None:
    if kind_id is None:
        return None
    row = await session.get(CustomKindRow, kind_id)
    return row if row is not None and row.catalog is catalog else None


async def kinds_in(session: AsyncSession, catalog: CustomCatalog, world_id: int | None = None) -> list[CustomKindRow]:
    statement = select(CustomKindRow).where(CustomKindRow.catalog == catalog)
    if world_id is not None:
        statement = statement.where((CustomKindRow.world_id == world_id) | CustomKindRow.world_id.is_(None))
    return list(await session.scalars(statement.order_by(CustomKindRow.id)))


@memoized(HolderCustomTechniqueRow)
async def custom_holders(session: AsyncSession) -> frozenset[int]:
    return frozenset(await session.scalars(select(HolderCustomTechniqueRow.holder_entity_id).distinct()))


@memoized(CustomKindRow, HolderCustomTechniqueRow)
async def custom_bases(session: AsyncSession, holder_id: int | None) -> frozenset[Technique]:
    if holder_id is None or holder_id not in await custom_holders(session):
        return frozenset()
    rows = await session.scalars(
        select(CustomKindRow.base)
        .join(HolderCustomTechniqueRow, HolderCustomTechniqueRow.kind_id == CustomKindRow.id)
        .where(HolderCustomTechniqueRow.holder_entity_id == holder_id, CustomKindRow.catalog == CustomCatalog.TECHNIQUE)
    )
    return frozenset(Technique(base) for base in rows)


async def world_of(ctx: TickContext, world_id: int | None) -> int | None:
    if world_id is None:
        return None
    if await ctx.session.get(WorldRow, world_id) is None:
        raise NotFoundError("No such world.")
    return world_id


async def create_kind(
    ctx: TickContext, catalog: CustomCatalog, base: str, name: str, *, description: str = "", params: Mapping[str, Any], world_id: int | None = None
) -> CustomKindRow:
    row = CustomKindRow(
        world_id=await world_of(ctx, world_id),
        catalog=catalog,
        base=checked_base(catalog, base),
        name=checked_name(name),
        description=description.strip(),
        params=checked_params(catalog, params),
        created_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def edit_kind(ctx: TickContext, kind_id: int, values: Mapping[str, Any]) -> CustomKindRow:
    row = await ctx.session.get(CustomKindRow, kind_id)
    if row is None:
        raise NotFoundError("No such kind.")
    unknown = sorted(set(values) - EDITABLE)
    if unknown:
        raise ValidationFailedError(f"{unknown[0].replace('_', ' ').capitalize()} cannot be set on a kind.")
    if "name" in values:
        row.name = checked_name(str(values["name"]))
    if "description" in values:
        row.description = str(values["description"] or "").strip()
    if "base" in values:
        row.base = checked_base(row.catalog, str(values["base"]))
    if "params" in values:
        params = values["params"]
        if not isinstance(params, Mapping):
            raise ValidationFailedError("Parameters are a table of values.")
        row.params = checked_params(row.catalog, params)
    if "world_id" in values:
        row.world_id = await world_of(ctx, values["world_id"])
    await ctx.session.flush()
    return row


async def delete_kind(ctx: TickContext, kind_id: int) -> CustomKindRow:
    row = await ctx.session.get(CustomKindRow, kind_id)
    if row is None:
        raise NotFoundError("No such kind.")
    await ctx.session.delete(row)
    await ctx.session.flush()
    return row
