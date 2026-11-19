from sqlalchemy import JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.death_work import DeathRole, DeathStanding
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN


class DeathWorkRow(Base):
    __tablename__ = "death_work"
    __table_args__ = (
        UniqueConstraint("people_entity_id", "role", name="uq_death_work_people_role"),
        between("purity", PERCENT_MIN, PERCENT_MAX),
        at_least("fee", 0),
        at_least("workers", 0),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    people_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    role: Mapped[DeathRole] = mapped_column(enum_type(DeathRole, "role"))
    standing: Mapped[DeathStanding] = mapped_column(enum_type(DeathStanding, "standing"), default=DeathStanding.PLAIN)
    purity: Mapped[int] = mapped_column(default=50)
    fee: Mapped[int] = mapped_column(default=1)
    workers: Mapped[int] = mapped_column(default=2)
    guild_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
