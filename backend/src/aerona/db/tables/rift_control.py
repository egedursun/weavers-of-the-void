from sqlalchemy import JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.cosmography import RiftWork
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN

RIFT_CONTROL_FIELDS = ("claimant_entity_id", "work", "toll", "adapted")


class RiftControlRow(Base):
    __tablename__ = "rift_controls"
    __table_args__ = (between("adapted", PERCENT_MIN, PERCENT_MAX), at_least("toll", 0))

    rift_id: Mapped[int] = mapped_column(ForeignKey("rifts.id", ondelete="CASCADE"), primary_key=True)
    claimant_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    work: Mapped[RiftWork] = mapped_column(enum_type(RiftWork, "work"), default=RiftWork.NONE)
    toll: Mapped[int] = mapped_column(default=0)
    adapted: Mapped[int] = mapped_column(default=0)
    claimed_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
