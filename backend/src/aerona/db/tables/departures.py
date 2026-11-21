from sqlalchemy import JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.departures import DepartureKind
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.polity import OfficeKind


class DepartureRow(Base):
    __tablename__ = "departures"
    __table_args__ = (
        between("standing", PERCENT_MIN, PERCENT_MAX),
        at_least("epoch", 0),
        at_least("years_held", 0),
        Index("ix_departures_holder", "holder_node_id"),
        Index("ix_departures_polity", "polity_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    holder_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    office_id: Mapped[int | None] = mapped_column(ForeignKey("offices.id", ondelete="SET NULL"))
    office_kind: Mapped[OfficeKind | None] = mapped_column(enum_type(OfficeKind, "office_kind"))
    polity_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    org_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    kind: Mapped[DepartureKind] = mapped_column(enum_type(DepartureKind, "kind"), default=DepartureKind.RETIREMENT)
    in_favour_of_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    conditions: Mapped[list[str]] = mapped_column(JSON, default=list)
    epoch: Mapped[int] = mapped_column(default=0)
    years_held: Mapped[int] = mapped_column(default=0)
    standing: Mapped[int] = mapped_column(default=30)
    returned_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
