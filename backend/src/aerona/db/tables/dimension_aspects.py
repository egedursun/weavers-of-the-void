from sqlalchemy import JSON, CheckConstraint, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import between, enum_type
from aerona.domain.enums.arcana import SpellForm
from aerona.domain.enums.cosmography import DimensionElement
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN

ASPECT_FIELDS = ("form", "element", "strength")


class DimensionAspectRow(Base):
    __tablename__ = "dimension_aspects"
    __table_args__ = (
        Index("ix_dimension_aspects_dimension", "dimension_id"),
        CheckConstraint("(form IS NULL) <> (element IS NULL)", name="form_or_element"),
        between("strength", PERCENT_MIN, PERCENT_MAX),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    dimension_id: Mapped[int] = mapped_column(ForeignKey("dimensions.id", ondelete="CASCADE"))
    form: Mapped[SpellForm | None] = mapped_column(enum_type(SpellForm, "form"))
    element: Mapped[DimensionElement | None] = mapped_column(enum_type(DimensionElement, "element"))
    strength: Mapped[int] = mapped_column(default=50)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
