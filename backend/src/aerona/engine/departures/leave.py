from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.changes import StateChangeRow
from aerona.db.tables.departures import DepartureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.governance import OrgGovernanceRow
from aerona.db.tables.polity import OfficeRow, PolityMemberRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.departures import DepartureCondition, DepartureKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.models.calendar import epoch_start_year
from aerona.engine.context import TickContext
from aerona.engine.departures.book import Seat, seat_name
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.formation import set_ruler
from aerona.engine.polity.laws import LawBook
from aerona.engine.polity.offices import succession_line
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import stat_or
from aerona.engine.recording.record import record
from aerona.engine.recording.scope import phase_moment

KIND_RECORDS = {
    DepartureKind.ABDICATION: "office.abdicated",
    DepartureKind.RETIREMENT: "office.retired",
    DepartureKind.RESIGNATION: "office.resigned",
    DepartureKind.WITHDRAWAL_TO_RELIGION: "office.withdrew",
    DepartureKind.EXILE_BY_CHOICE: "office.withdrew",
}
CONDITION_STANDING = 10
HOLDER_LOCK = "holder_entity_id"
HEAD_LOCK = "head_node_id"


async def hand_rule(ctx: TickContext, seat: Seat, heir: int | None, why: str) -> int | None:
    office = seat.office
    if office is None:
        return None
    if office.kind is OfficeKind.RULER:
        book = await RealmBook.load(ctx.session)
        realm = book.realms.get(office.polity_entity_id)
        if realm is None:
            return None
        if heir is None:
            line = await succession_line(ctx, realm, await LawBook.load(ctx.session))
            heir = next((candidate.id for candidate in line if candidate.id != seat.holder.id), None)
        set_ruler(ctx, realm, heir, why)
        return heir
    if HOLDER_LOCK not in (office.locked or []):
        office.holder_entity_id, office.since_epoch = heir, ctx.epoch
    return heir


async def hand_headship(seat: Seat, heir: int | None, epoch: int) -> int | None:
    if seat.org is None or HEAD_LOCK in (seat.org.locked or []):
        return None
    seat.org.head_node_id = heir
    seat.org.since_epoch = epoch
    return heir


async def exile(ctx: TickContext, holder: EntityRow, realm_id: int | None) -> int | None:
    inside = set(await ctx.session.scalars(select(PolityMemberRow.member_entity_id).where(PolityMemberRow.polity_entity_id == realm_id))) if realm_id else set()
    query = select(EntityRow.id).where(
        EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON, EntityRow.world_id == holder.world_id
    )
    for town in await ctx.session.scalars(query.order_by(EntityRow.id)):
        if town not in inside and town != holder.location_id and not held(town):
            holder.location_id = town
            return int(town)
    return None


async def relieve(ctx: TickContext, holder: EntityRow) -> None:
    town = await ctx.session.get(SettlementProfileRow, holder.location_id) if holder.location_id is not None else None
    if town is not None and "unrest" not in (town.locked or []):
        town.unrest = clamp_int(town.unrest - ctx.rules.departures.scandal_unrest_relief, 0, PERCENT)


def seat_key(seat: Seat) -> tuple[str, str, str] | None:
    if seat.office is not None and seat.office.id is not None:
        return OfficeRow.__tablename__, f'{{"id": {seat.office.id}}}', "holder_entity_id"
    if seat.org is not None:
        return OrgGovernanceRow.__tablename__, f'{{"org_node_id": {seat.org.org_node_id}}}', "head_node_id"
    return None


async def tenure_years(ctx: TickContext, seat: Seat) -> int:
    years = ctx.rules.time.years_per_epoch
    now = phase_moment(ctx.environment).year or epoch_start_year(ctx.epoch, years)
    key = seat_key(seat)
    taken = (
        await ctx.session.scalar(
            select(StateChangeRow.year)
            .where(
                StateChangeRow.table_name == key[0],
                StateChangeRow.row_key == key[1],
                StateChangeRow.field == key[2],
                StateChangeRow.after_node_id == seat.holder.id,
                StateChangeRow.year.is_not(None),
            )
            .order_by(StateChangeRow.id.desc())
            .limit(1)
        )
        if key is not None
        else None
    )
    held_for = now - taken if taken is not None else max(0, ctx.epoch - seat.since) * years
    return max(0, min(held_for, stat_or(seat.holder, "age", held_for)))


async def leave(ctx: TickContext, seat: Seat, kind: DepartureKind, *, heir: int | None, conditions: list[DepartureCondition], why: str) -> DepartureRow:
    holder = seat.holder
    living_heir = await living_entity(ctx.session, heir) if heir is not None else None
    chosen = living_heir.id if living_heir is not None and living_heir.id != holder.id else None
    years = await tenure_years(ctx, seat)
    successor = await hand_rule(ctx, seat, chosen, why) if seat.office is not None else await hand_headship(seat, chosen, ctx.epoch)
    row = DepartureRow(
        holder_node_id=holder.id,
        office_id=seat.office.id if seat.office is not None else None,
        office_kind=seat.office.kind if seat.office is not None else None,
        polity_entity_id=seat.polity_id,
        org_node_id=seat.org.org_node_id if seat.org is not None else None,
        kind=kind,
        in_favour_of_node_id=successor,
        conditions=sorted({condition.value for condition in conditions}),
        epoch=ctx.epoch,
        years_held=years,
        standing=clamp_int(years * ctx.rules.departures.standing_per_year + CONDITION_STANDING * len(set(conditions)), 0, PERCENT),
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    if kind is DepartureKind.RESIGNATION:
        await relieve(ctx, holder)
    elif kind is DepartureKind.EXILE_BY_CHOICE and DepartureCondition.SAFE_CONDUCT in conditions:
        await exile(ctx, holder, seat.polity_id)
    await record(
        ctx,
        KIND_RECORDS[kind],
        roles={
            IncidentRole.ACTOR: holder.id,
            IncidentRole.SUCCESSOR: successor,
            IncidentRole.SUBJECT: seat.polity_id or (seat.org.org_node_id if seat.org else None),
        },
        facts={"kind": kind, "seat": seat_name(seat.office.kind if seat.office is not None else None), "why": why},
    )
    return row
