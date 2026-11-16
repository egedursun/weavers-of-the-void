from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass

from sqlalchemy import func, select

from aerona.core.total import total
from aerona.db.tables.collective import DesignRow
from aerona.db.tables.customs import MembershipRow
from aerona.db.tables.discovery import BlueprintRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.estates import CompanyProfileRow
from aerona.db.tables.law_depth import RegistryRow
from aerona.db.tables.living import LivingLineRow
from aerona.db.tables.minds import MindProfileRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.polity import PolityMemberRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.law_depth import RegistryKind
from aerona.domain.enums.minds import MindOrigin
from aerona.engine.context import TickContext
from aerona.engine.law.systems import written_code


@dataclass(frozen=True)
class Entry:
    place_id: int | None
    owner_id: int | None
    subject_id: int | None
    number: int = 0


Find = Callable[[TickContext], Awaitable[list[Entry]]]


async def where(ctx: TickContext, node_id: int | None) -> int | None:
    entity = await ctx.session.get(EntityRow, node_id) if node_id is not None else None
    return entity.location_id if entity is not None else None


async def births(ctx: TickContext) -> list[Entry]:
    rows = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.birth_epoch == ctx.epoch).order_by(EntityRow.id)
    )
    return [Entry(row.location_id, row.id, row.id) for row in rows]


async def deaths(ctx: TickContext) -> list[Entry]:
    rows = await ctx.session.scalars(
        select(MortalProfileRow)
        .where(MortalProfileRow.cause_of_death.is_not(None), MortalProfileRow.updated_epoch == ctx.epoch)
        .order_by(MortalProfileRow.entity_id)
    )
    return [Entry(row.death_place_id, row.entity_id, row.entity_id) for row in rows]


async def citizens(ctx: TickContext) -> list[Entry]:
    rows = await ctx.session.scalars(select(MembershipRow).where(MembershipRow.since_epoch == ctx.epoch).order_by(MembershipRow.mortal_entity_id))
    return [Entry(await where(ctx, row.mortal_entity_id), row.mortal_entity_id, row.polity_entity_id) for row in rows]


async def companies(ctx: TickContext) -> list[Entry]:
    rows = await ctx.session.scalars(
        select(CompanyProfileRow).where(CompanyProfileRow.chartered_epoch == ctx.epoch).order_by(CompanyProfileRow.faction_entity_id)
    )
    return [Entry(row.headquarters_entity_id, row.faction_entity_id, row.faction_entity_id) for row in rows]


async def patents(ctx: TickContext) -> list[Entry]:
    rows = await ctx.session.scalars(select(BlueprintRow).where(BlueprintRow.since_epoch == ctx.epoch).order_by(BlueprintRow.id))
    return [Entry(await where(ctx, row.holder_node_id), row.holder_node_id, row.book_entity_id, row.id) for row in rows]


async def patterns(ctx: TickContext) -> list[Entry]:
    rows = await ctx.session.scalars(select(DesignRow).where(DesignRow.entity_id.is_not(None)).order_by(DesignRow.id))
    return [Entry(await where(ctx, row.owner_entity_id), row.owner_entity_id, row.entity_id, row.id) for row in rows]


async def minds(ctx: TickContext) -> list[Entry]:
    rows = await ctx.session.scalars(select(MindProfileRow).where(MindProfileRow.origin == MindOrigin.COPIED).order_by(MindProfileRow.node_id))
    return [Entry(await where(ctx, row.node_id), row.node_id, row.node_id) for row in rows]


async def lines(ctx: TickContext) -> list[Entry]:
    rows = await ctx.session.scalars(select(LivingLineRow).where(LivingLineRow.owner_node_id.is_not(None)).order_by(LivingLineRow.id))
    return [Entry(await where(ctx, row.owner_node_id), row.owner_node_id, None, row.id) for row in rows]


async def none_kept(_ctx: TickContext) -> list[Entry]:
    return []


SOURCES: Mapping[RegistryKind, Find] = total(
    RegistryKind,
    {
        RegistryKind.LAND_TITLE: none_kept,
        RegistryKind.DEBT: none_kept,
        RegistryKind.SALE: none_kept,
        RegistryKind.DOWRY: none_kept,
        RegistryKind.INDENTURE: none_kept,
        RegistryKind.PATENT: patents,
        RegistryKind.PATTERN: patterns,
        RegistryKind.MIND_STATE: minds,
        RegistryKind.LINE: lines,
        RegistryKind.COMPANY: companies,
        RegistryKind.BIRTH: births,
        RegistryKind.DEATH: deaths,
        RegistryKind.CITIZENSHIP: citizens,
    },
)


async def entity_or_none(ctx: TickContext, node_id: int | None) -> int | None:
    return node_id if node_id is not None and await ctx.session.get(EntityRow, node_id) is not None else None


async def kept_already(ctx: TickContext, kind: RegistryKind, entry: Entry) -> bool:
    found = await ctx.session.scalar(
        select(RegistryRow.id)
        .where(
            RegistryRow.kind == kind,
            RegistryRow.owner_entity_id == entry.owner_id,
            RegistryRow.subject_entity_id == entry.subject_id,
            RegistryRow.amount == entry.number,
        )
        .limit(1)
    )
    return found is not None


async def record_events(ctx: TickContext) -> int:
    kept = 0
    for kind, find in SOURCES.items():
        for found in await find(ctx):
            polity = await ctx.session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == found.place_id).limit(1))
            if polity is None or held(polity) or not await written_code(ctx.session, [polity]):
                continue
            entry = Entry(found.place_id, await entity_or_none(ctx, found.owner_id), await entity_or_none(ctx, found.subject_id), found.number)
            if await kept_already(ctx, kind, entry):
                continue
            ctx.session.add(
                RegistryRow(
                    holder_entity_id=polity,
                    kind=kind,
                    owner_entity_id=entry.owner_id,
                    subject_entity_id=entry.subject_id,
                    amount=entry.number,
                    registered_epoch=ctx.epoch,
                    locked=[],
                )
            )
            kept += 1
    await ctx.session.flush()
    return kept


async def records_of(ctx: TickContext, polity_id: int) -> int:
    return int(await ctx.session.scalar(select(func.count(RegistryRow.id)).where(RegistryRow.holder_entity_id == polity_id)) or 0)
