from sqlalchemy import JSON, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.population import PopulationAim, PopulationInstrument


class PopulationPolicyRow(Base):
    __tablename__ = "population_policies"
    __table_args__ = (
        between("strength", PERCENT_MIN, PERCENT_MAX),
        between("enforcement", PERCENT_MIN, PERCENT_MAX),
        at_least("since_epoch", 0),
        at_least("baseline", 0),
        Index("ix_population_policies_holder", "holder_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    holder_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    target_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    aim: Mapped[PopulationAim] = mapped_column(enum_type(PopulationAim, "aim"), default=PopulationAim.HOLD)
    strength: Mapped[int] = mapped_column(default=50)
    enforcement: Mapped[int] = mapped_column(default=50)
    baseline: Mapped[int] = mapped_column(default=0)
    reason: Mapped[str | None] = mapped_column(Text)
    since_epoch: Mapped[int] = mapped_column(default=0)
    reviewed_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class PopulationInstrumentRow(Base):
    __tablename__ = "population_instruments"
    __table_args__ = (between("strength", PERCENT_MIN, PERCENT_MAX), Index("ix_population_instruments_holder", "holder_node_id"))

    policy_id: Mapped[int] = mapped_column(ForeignKey("population_policies.id", ondelete="CASCADE"), primary_key=True)
    instrument: Mapped[PopulationInstrument] = mapped_column(enum_type(PopulationInstrument, "instrument"), primary_key=True)
    holder_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    strength: Mapped[int] = mapped_column(default=50)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
