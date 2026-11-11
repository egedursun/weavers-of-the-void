from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import OfficeRow, PolityMemberRow, PolityProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.polity import OfficeKind
from aerona.engine.context import TickContext
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import stat, stat_or


def shift(row: object, field: str, delta: float, *, low: int = 0, high: int = PERCENT) -> int:
    current = getattr(row, field)
    if field in (getattr(row, "locked", None) or []):
        return int(current)
    value = clamp_int(current + delta, low, high)
    setattr(row, field, value)
    return value


async def towns(ctx: TickContext) -> list[tuple[EntityRow, SettlementProfileRow]]:
    rows = await ctx.session.execute(
        select(EntityRow, SettlementProfileRow)
        .join(SettlementProfileRow, SettlementProfileRow.settlement_entity_id == EntityRow.id)
        .where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    return [(entity, profile) for entity, profile in rows]


async def soldiers_of(ctx: TickContext, profile: SettlementProfileRow) -> int:
    garrison = await living_entity(ctx.session, profile.garrison_entity_id) if profile.garrison_entity_id is not None else None
    return profile.militia + ((stat(garrison, "size") or 0) if garrison is not None else 0)


def population_of(town: EntityRow) -> int:
    return stat_or(town, "population", 0)


async def realm_of_town(ctx: TickContext, town_id: int) -> PolityProfileRow | None:
    if (own := await ctx.session.get(PolityProfileRow, town_id)) is not None:
        return own
    polity_id = await ctx.session.scalar(
        select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == town_id).order_by(PolityMemberRow.polity_entity_id).limit(1)
    )
    return await ctx.session.get(PolityProfileRow, polity_id) if polity_id is not None else None


async def ruler_id(ctx: TickContext, polity_id: int) -> int | None:
    return await ctx.session.scalar(
        select(OfficeRow.holder_entity_id)
        .where(OfficeRow.polity_entity_id == polity_id, OfficeRow.kind == OfficeKind.RULER, OfficeRow.holder_entity_id.is_not(None))
        .order_by(OfficeRow.id)
        .limit(1)
    )
