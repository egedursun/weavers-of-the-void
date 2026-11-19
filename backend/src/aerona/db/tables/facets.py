from sqlalchemy import JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.facets import FacetKind
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN


class FacetPracticeRow(Base):
    __tablename__ = "facet_practices"
    __table_args__ = (
        UniqueConstraint("community_entity_id", "facet", name="uq_facet_practices_community_facet"),
        between("level", PERCENT_MIN, PERCENT_MAX),
        at_least("since_epoch", 0),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    community_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    facet: Mapped[FacetKind] = mapped_column(enum_type(FacetKind, "facet"))
    level: Mapped[int] = mapped_column(default=0)
    since_epoch: Mapped[int] = mapped_column(default=0)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
