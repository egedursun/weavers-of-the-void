from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.core.grammar import spoken
from aerona.db.tables.departures import DepartureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.governance import OrgGovernanceRow
from aerona.db.tables.polity import OfficeRow
from aerona.domain.enums.departures import DepartureCondition, DepartureKind
from aerona.domain.enums.polity import OfficeKind
from aerona.engine.context import TickContext


@dataclass
class DepartureTally:
    left: int = 0
    returned: int = 0
    pensions: int = 0
    rallies: int = 0
    marked: int = 0


@dataclass(frozen=True)
class Seat:
    holder: EntityRow
    office: OfficeRow | None
    org: OrgGovernanceRow | None

    @property
    def polity_id(self) -> int | None:
        return self.office.polity_entity_id if self.office is not None else None

    @property
    def since(self) -> int:
        if self.office is not None:
            return self.office.since_epoch
        return self.org.since_epoch if self.org is not None else 0


def conditions_of(row: DepartureRow) -> frozenset[DepartureCondition]:
    known = {item.value: item for item in DepartureCondition}
    return frozenset(known[value] for value in row.conditions or [] if value in known)


def seat_name(kind: OfficeKind | None) -> str:
    return spoken(kind) if kind is not None else "head"


def lifespan(ctx: TickContext) -> int:
    table = ctx.rules.peoples
    return table.maturity_years + table.adult_years + table.elder_years


async def open_departures(session: AsyncSession) -> list[DepartureRow]:
    return list(await session.scalars(select(DepartureRow).where(DepartureRow.returned_epoch.is_(None)).order_by(DepartureRow.id)))


def note_resignation(ctx: TickContext, holder: EntityRow, office: OfficeRow) -> DepartureRow:
    row = DepartureRow(
        holder_node_id=holder.id,
        office_id=office.id,
        office_kind=office.kind,
        polity_entity_id=office.polity_entity_id,
        kind=DepartureKind.RESIGNATION,
        conditions=[],
        epoch=ctx.epoch,
        years_held=max(0, ctx.epoch - office.since_epoch) * ctx.rules.time.years_per_epoch,
        standing=0,
        locked=[],
    )
    ctx.session.add(row)
    return row
