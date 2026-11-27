from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.repositories.bonds import BondRepository
from aerona.db.tables.body import InjuryRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.governance import OrgGovernanceRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.justice import CrimeCaseRow
from aerona.db.tables.polity import OfficeRow, PolityProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.departures import DepartureCondition, DepartureKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import OfficeKind
from aerona.engine.body.marks import marked
from aerona.engine.context import TickContext
from aerona.engine.departures.book import DepartureTally, Seat
from aerona.engine.departures.leave import leave
from aerona.engine.primitives.maturity import office_age_share
from aerona.engine.primitives.numbers import clamp_int

FAILING_STABILITY = 30
SCANDAL_ROLES = (IncidentRole.ACCUSED, IncidentRole.SUBJECT)
SCANDAL_MARKS = ("%exposed%", "%scandal%")
TROUBLE_PERCENT = PERCENT


async def scandalous(ctx: TickContext, holder_id: int) -> bool:
    case = select(CrimeCaseRow.id).where(CrimeCaseRow.accused_entity_id == holder_id, CrimeCaseRow.opened_epoch >= ctx.epoch - 1).limit(1)
    if await ctx.session.scalar(case) is not None:
        return True
    told = (
        select(IncidentRow.id)
        .join(IncidentParticipantRow, IncidentParticipantRow.incident_id == IncidentRow.id)
        .where(
            IncidentRow.epoch >= ctx.epoch - 1,
            IncidentParticipantRow.node_id == holder_id,
            IncidentParticipantRow.role.in_(SCANDAL_ROLES),
            IncidentRow.kind.like(SCANDAL_MARKS[0]) | IncidentRow.kind.like(SCANDAL_MARKS[1]),
        )
        .limit(1)
    )
    return await ctx.session.scalar(told) is not None


async def wounded(ctx: TickContext, holder_id: int) -> bool:
    return await ctx.session.scalar(select(InjuryRow.id).where(InjuryRow.bearer_node_id == holder_id, marked()).limit(1)) is not None


async def failing(ctx: TickContext, seat: Seat) -> bool:
    if seat.office is None or seat.office.kind is not OfficeKind.RULER:
        return False
    realm = await ctx.session.get(PolityProfileRow, seat.office.polity_entity_id)
    return realm is not None and realm.stability < FAILING_STABILITY


async def devout(ctx: TickContext, holder: EntityRow) -> bool:
    return bool(await BondRepository(ctx.session).outgoing(holder.id, BondKind.WORSHIPS))


async def weigh(ctx: TickContext, seat: Seat) -> tuple[int, DepartureKind, bool]:
    table = ctx.rules.departures
    share = office_age_share(ctx.rules, seat.holder)
    scandal = await scandalous(ctx, seat.holder.id)
    hurt = await wounded(ctx, seat.holder.id)
    failed = await failing(ctx, seat)
    weight = (
        share * table.age_weight // PERCENT
        + (table.scandal_weight if scandal else 0)
        + (table.health_weight if hurt else 0)
        + (table.failure_weight if failed else 0)
    )
    ruler = seat.office is not None and seat.office.kind is OfficeKind.RULER
    customary = not ruler and share >= table.retirement_age_share_pct
    if scandal:
        kind = DepartureKind.RESIGNATION
    elif failed:
        kind = DepartureKind.EXILE_BY_CHOICE
    elif ruler and await devout(ctx, seat.holder):
        kind = DepartureKind.WITHDRAWAL_TO_RELIGION
    elif ruler:
        kind = DepartureKind.ABDICATION
    else:
        kind = DepartureKind.RETIREMENT
    return clamp_int(weight, 0, TROUBLE_PERCENT), kind, customary


async def trouble_of(ctx: TickContext, seat: Seat) -> str:
    if await scandalous(ctx, seat.holder.id):
        return "a scandal"
    if await failing(ctx, seat):
        return "a failing realm"
    if await wounded(ctx, seat.holder.id):
        return "failing health"
    return "advancing age"


def terms_for(kind: DepartureKind) -> list[DepartureCondition]:
    if kind is DepartureKind.ABDICATION:
        return [DepartureCondition.KEEP_TITLE, DepartureCondition.KEEP_LANDS]
    if kind is DepartureKind.RETIREMENT:
        return [DepartureCondition.PENSION]
    if kind is DepartureKind.EXILE_BY_CHOICE:
        return [DepartureCondition.SAFE_CONDUCT]
    return []


async def seats(ctx: TickContext) -> list[Seat]:
    found: list[Seat] = []
    for office in await ctx.session.scalars(select(OfficeRow).where(OfficeRow.holder_entity_id.is_not(None)).order_by(OfficeRow.id)):
        holder = await ctx.session.get(EntityRow, office.holder_entity_id)
        if holder is not None and holder.entity_type is EntityType.MORTAL and holder.status is EntityStatus.CANON:
            found.append(Seat(holder, office, None))
    for org in await ctx.session.scalars(select(OrgGovernanceRow).where(OrgGovernanceRow.head_node_id.is_not(None)).order_by(OrgGovernanceRow.org_node_id)):
        holder = await ctx.session.get(EntityRow, org.head_node_id)
        if holder is not None and holder.entity_type is EntityType.MORTAL and holder.status is EntityStatus.CANON:
            found.append(Seat(holder, None, org))
    return found


async def weigh_seats(ctx: TickContext, tally: DepartureTally) -> None:
    table = ctx.rules.departures
    for seat in await seats(ctx):
        locked = (seat.office.locked if seat.office is not None else seat.org.locked if seat.org is not None else []) or []
        if held(seat.holder.id) or "holder_entity_id" in locked or "head_node_id" in locked:
            continue
        if seat.office is not None and held(seat.office.polity_entity_id):
            continue
        weight, kind, customary = await weigh(ctx, seat)
        key = f"departures.leave.{seat.holder.id}.{seat.office.id if seat.office else seat.org.org_node_id if seat.org else 0}.{ctx.epoch}"
        if not customary and not ctx.rng(key).chance(weight * table.leave_chance_pct // PERCENT):
            continue
        reason = "custom retires those of that age" if customary else await trouble_of(ctx, seat)
        await leave(ctx, seat, kind, heir=None, conditions=terms_for(kind), why=reason)
        tally.left += 1
