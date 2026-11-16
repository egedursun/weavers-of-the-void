from collections.abc import Mapping
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.grammar import several
from aerona.core.total import total
from aerona.db.tables.collective import DatingSystemRow
from aerona.db.tables.cosmos import CosmosRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import CalendarRow
from aerona.db.tables.polity import OfficeRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.collective import DatingSystemKind
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.polity import OfficeKind
from aerona.engine.context import TickContext
from aerona.engine.lore.research import has_technique
from aerona.engine.mind.ethics import church_of
from aerona.engine.notes import note
from aerona.engine.primitives.queries import active_bonds
from aerona.engine.services.community_relations import change_relation

D = DatingSystemKind
SINGLETON = 1
CYCLE_YEARS = 60
DISPUTE_HOSTILITY = -10
HOLDER_KINDS = {EntityType.POLITY: D.REGNAL, EntityType.CULT: D.RELIGIOUS, EntityType.PEOPLE: D.FOUNDING}
REFORMS: Mapping[DatingSystemKind, DatingSystemKind] = total(
    DatingSystemKind,
    {
        D.REGNAL: D.FOUNDING,
        D.FOUNDING: D.EVENT,
        D.RELIGIOUS: D.CREATION,
        D.CELESTIAL_CYCLE: D.CYCLE_COUNT,
        D.CREATION: D.FOUNDING,
        D.EVENT: D.CELESTIAL_CYCLE,
        D.CYCLE_COUNT: D.CREATION,
    },
)


@dataclass
class DatingTally:
    seeded: int = 0
    regnal: int = 0
    reforms: int = 0
    disputes: int = 0


CYCLED: Mapping[DatingSystemKind, str] = {
    D.CELESTIAL_CYCLE: "the {within} year of the {cycle} cycle",
    D.CYCLE_COUNT: "the {cycle} cycle",
}
COUNTED: Mapping[DatingSystemKind, str] = {
    D.REGNAL: "the {year} year of the reign of {label}",
    D.FOUNDING: "the {year} year since the founding of {label}",
    D.RELIGIOUS: "the {year} year of {label}",
    D.CREATION: "the {year} year since the making of the world",
    D.EVENT: "the {year} year since the great turning of {label}",
}


async def current_year(session: AsyncSession) -> int:
    cosmos = await session.get(CosmosRow, SINGLETON)
    return cosmos.epoch_start_year if cosmos is not None else 0


def ordinal(number: int) -> str:
    tail = "th" if 10 <= number % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{tail}"


async def render_date(session: AsyncSession, holder_id: int | None, year: int) -> str:
    row = await session.get(DatingSystemRow, holder_id) if holder_id is not None else None
    if row is None:
        return f"year {year}"
    label_row = await session.get(EntityRow, row.label_node_id) if row.label_node_id is not None else None
    label = label_row.name if label_row is not None else "the era"
    count = year - row.anchor_year + 1
    span = max(1, row.cycle_years)
    cycle, within = divmod(max(0, year - row.anchor_year), span)
    if row.kind in CYCLED:
        return CYCLED[row.kind].format(within=ordinal(within + 1), cycle=ordinal(cycle + 1))
    if count < 1:
        return f"{several(1 - count, 'year', 'years')} before {label}"
    return COUNTED[row.kind].format(year=ordinal(count), label=label)


async def ruler_since(ctx: TickContext, polity_id: int) -> OfficeRow | None:
    return await ctx.session.scalar(
        select(OfficeRow)
        .where(OfficeRow.polity_entity_id == polity_id, OfficeRow.kind == OfficeKind.RULER, OfficeRow.holder_entity_id.is_not(None))
        .order_by(OfficeRow.id)
        .limit(1)
    )


async def seed_dating(ctx: TickContext, holder: EntityRow, year: int, tally: DatingTally) -> DatingSystemRow:
    kind = HOLDER_KINDS[holder.entity_type]
    founded = year - (ctx.epoch - holder.birth_epoch) * ctx.rules.time.years_per_epoch
    row = DatingSystemRow(
        holder_entity_id=holder.id,
        kind=kind,
        anchor_year=max(0, founded),
        anchor_node_id=holder.id,
        label_node_id=holder.id,
        cycle_years=CYCLE_YEARS,
        since_epoch=ctx.epoch,
        locked=[],
    )
    if kind is D.REGNAL:
        office = await ruler_since(ctx, holder.id)
        if office is not None and office.holder_entity_id is not None:
            row.anchor_year = max(0, year - (ctx.epoch - office.since_epoch) * ctx.rules.time.years_per_epoch)
            row.anchor_node_id = row.label_node_id = office.holder_entity_id
    ctx.session.add(row)
    await ctx.session.flush()
    tally.seeded += 1
    return row


async def follow_reign(ctx: TickContext, row: DatingSystemRow, year: int, tally: DatingTally) -> None:
    if row.kind is not D.REGNAL or {"anchor_year", "label_node_id"} & set(row.locked):
        return
    office = await ruler_since(ctx, row.holder_entity_id)
    if office is None or office.holder_entity_id is None or office.holder_entity_id == row.label_node_id:
        return
    row.anchor_year, row.anchor_node_id, row.label_node_id = year, office.holder_entity_id, office.holder_entity_id
    tally.regnal += 1


async def known_calendar(ctx: TickContext, holder_id: int) -> CalendarRow | None:
    known = [bond.target_node_id for bond in await active_bonds(ctx.session, [BondKind.KNOWS], sources=[holder_id])]
    if not known:
        return None
    return await ctx.session.scalar(select(CalendarRow).where(CalendarRow.knowledge_entity_id.in_(known)).order_by(CalendarRow.adopted_epoch).limit(1))


async def reform(ctx: TickContext, holder: EntityRow, row: DatingSystemRow, year: int, tally: DatingTally) -> None:
    table = ctx.rules.dating
    calendar = await known_calendar(ctx, holder.id)
    if "kind" in row.locked or (calendar is None and not await has_technique(ctx.session, holder.id, Technique.CALENDAR)):
        return
    if not ctx.rng(f"calendar_reform.{holder.id}.{ctx.epoch}").chance(table.reform_pct):
        return
    old = row.kind
    row.kind, row.reformed_epoch = REFORMS[old], ctx.epoch
    if row.kind is D.CREATION:
        row.anchor_year = 0
    elif row.kind is D.EVENT:
        row.anchor_year = year
    if row.kind is D.FOUNDING:
        row.label_node_id = row.anchor_node_id = holder.id
        row.anchor_year = max(0, year - (ctx.epoch - holder.birth_epoch) * ctx.rules.time.years_per_epoch)
    elif row.kind is D.CELESTIAL_CYCLE:
        row.anchor_year = calendar.anchor_year if calendar is not None else year
        row.label_node_id = row.anchor_node_id = calendar.knowledge_entity_id if calendar is not None else holder.id
    tally.reforms += 1
    await note(
        ctx, f"{holder.name} reformed its calendar and now counts {await render_date(ctx.session, holder.id, year)}.", key="dating.reform", ids=[holder.id]
    )
    if holder.entity_type is EntityType.PEOPLE:
        for cult_id in await church_of(ctx.session, holder):
            if ctx.rng(f"calendar_dispute.{holder.id}.{cult_id}.{ctx.epoch}").chance(table.dispute_pct):
                await change_relation(ctx, holder.id, cult_id, DISPUTE_HOSTILITY, MemoryKind.ILL_WILL, note="a calendar reform broke the old festivals")
                tally.disputes += 1


async def keep_calendars(ctx: TickContext, tally: DatingTally) -> None:
    year = await current_year(ctx.session)
    known = {row.holder_entity_id: row for row in await ctx.session.scalars(select(DatingSystemRow))}
    holders = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type.in_(list(HOLDER_KINDS)), EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    for holder in list(holders):
        if held(holder.id):
            continue
        row = known.get(holder.id) or await seed_dating(ctx, holder, year, tally)
        await follow_reign(ctx, row, year, tally)
        await reform(ctx, holder, row, year, tally)
    await ctx.session.flush()
