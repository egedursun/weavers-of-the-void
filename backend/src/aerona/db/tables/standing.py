from sqlalchemy import JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.mind import ValueAxis


class ProfessionOfValueRow(Base):
    __tablename__ = "professions_of_value"
    __table_args__ = (
        UniqueConstraint("holder_node_id", "axis", name="uq_professions_of_value_holder_axis"),
        between("strength", 0, 100),
        between("gap", 0, 100),
        at_least("acts_against", 0),
        at_least("knowers", 0),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    holder_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), index=True)
    axis: Mapped[ValueAxis] = mapped_column(enum_type(ValueAxis, "axis"))
    strength: Mapped[int] = mapped_column(default=50)
    acts_against: Mapped[int] = mapped_column(default=0)
    gap: Mapped[int] = mapped_column(default=0)
    knowers: Mapped[int] = mapped_column(default=0)
    exposed: Mapped[bool] = mapped_column(default=False)
    last_act_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
