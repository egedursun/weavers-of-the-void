from dataclasses import dataclass

from sqlalchemy import select, update

from aerona.catalog.incident_kinds.onlookers import ONLOOKER_ROLES
from aerona.catalog.life.services import PRESENT_MODES
from aerona.db.tables.changes import StateChangeRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.node import NodeBirthRow
from aerona.db.tables.records import IncidentFactRow, IncidentStepRow
from aerona.db.write_guard import held
from aerona.domain.models.calendar import epoch_start_year
from aerona.domain.models.moment import Moment, latest
from aerona.engine.context import TickContext
from aerona.engine.recording.chains import followed, principals
from aerona.engine.recording.deaths import ended_floor, mortal_floor
from aerona.engine.recording.moments import incident_moment

DATED_KEY = "year"


def moment_of(row: IncidentRow) -> Moment | None:
    return Moment(row.year, row.season, row.day, row.hour) if row.year is not None else None


async def deeds_after(ctx: TickContext, mortal_id: int, death: Moment) -> list[IncidentRow]:
    taken = select(IncidentParticipantRow.incident_id).where(
        IncidentParticipantRow.node_id == mortal_id, IncidentParticipantRow.role.not_in(sorted(ONLOOKER_ROLES))
    )
    rows = await ctx.session.scalars(
        select(IncidentRow).where(IncidentRow.id.in_(taken), IncidentRow.epoch == ctx.epoch, IncidentRow.year.is_not(None)).order_by(IncidentRow.id)
    )
    return sorted(
        (row for row in rows if (own := moment_of(row)) is not None and death.before(own)),
        key=lambda row: ((moment_of(row) or death).key(), row.id),
        reverse=True,
    )


@dataclass(frozen=True)
class Bounds:
    floor: Moment | None
    carried: list[NodeBirthRow]


async def ended_before(ctx: TickContext, nodes: list[int], own: Moment) -> Moment | None:
    ends = [moment for moment in [await mortal_floor(ctx.session, [node]) for node in nodes] + [await ended_floor(ctx.session, [node]) for node in nodes]]
    return latest(*(moment for moment in ends if moment is not None and moment.before(own)))


async def bounds_of(ctx: TickContext, deed: IncidentRow, mortal_id: int) -> Bounds:
    own = moment_of(deed)
    dated = await ctx.session.scalar(select(IncidentFactRow.id).where(IncidentFactRow.incident_id == deed.id, IncidentFactRow.key == DATED_KEY).limit(1))
    if own is None or dated is not None:
        return Bounds(own, [])
    taking_part = list(
        await ctx.session.execute(
            select(IncidentParticipantRow.node_id, IncidentParticipantRow.role, IncidentParticipantRow.witness_mode).where(
                IncidentParticipantRow.incident_id == deed.id
            )
        )
    )
    roles = [(node, role) for node, role, _ in taking_part]
    there = sorted({node for node, role, mode in taking_part if role not in ONLOOKER_ROLES or mode in PRESENT_MODES})
    births = list(await ctx.session.scalars(select(NodeBirthRow).where(NodeBirthRow.node_id.in_(there)).order_by(NodeBirthRow.node_id)))
    carried = [row for row in births if Moment(row.year, row.season, row.day, row.hour) == own and not row.locked and not held(row.node_id)]
    held_back = [Moment(row.year, row.season, row.day, row.hour) for row in births if row not in carried]
    return Bounds(
        latest(
            await incident_moment(ctx.session, deed.cause_incident_id),
            await followed(ctx, deed.kind, principals([(node, role) for node, role in roles])),
            *held_back,
            await ended_before(ctx, [node for node in there if node != mortal_id], own),
        ),
        carried,
    )


async def move_deed(ctx: TickContext, deed: IncidentRow, year: int, carried: list[NodeBirthRow]) -> None:
    shift = year - (deed.year or year)
    if shift == 0:
        return
    deed.year = year
    for born in carried:
        born.year = year
    line = await ctx.session.get(ChronicleRow, deed.chronicle_id) if deed.chronicle_id is not None else None
    if line is not None:
        line.year = year
    for step in await ctx.session.scalars(select(IncidentStepRow).where(IncidentStepRow.incident_id == deed.id).order_by(IncidentStepRow.id)):
        if step.year is not None:
            step.year += shift
    await ctx.session.execute(
        update(StateChangeRow).where(StateChangeRow.incident_id == deed.id, StateChangeRow.year.is_not(None)).values(year=StateChangeRow.year + shift)
    )


async def keep_deeds_before(ctx: TickContext, mortal_id: int, death: Moment) -> Moment:
    start = epoch_start_year(ctx.epoch, ctx.rules.time.years_per_epoch)
    for deed in await deeds_after(ctx, mortal_id, death):
        own = moment_of(deed)
        if own is None or not death.before(own):
            continue
        bounds = await bounds_of(ctx, deed, mortal_id)
        low = max(start, bounds.floor.year + 1 if bounds.floor is not None else start)
        high = death.year - 1
        if high < low:
            death = own
            continue
        await move_deed(ctx, deed, ctx.rng(f"death.last_days.{mortal_id}.{deed.id}").integer(low, high), bounds.carried)
    return death
