from sqlalchemy import JSON, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.daily_life import (
    DistanceNorm,
    HouseDuty,
    LeisureKind,
    PostureForm,
    ServiceTerms,
    TouchNorm,
    WashFrequency,
    WashPlace,
    WasteHandling,
)
from aerona.domain.enums.genetics import HouseholdRole
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN


class CareCustomRow(Base):
    __tablename__ = "care_customs"
    __table_args__ = (between("grooming", PERCENT_MIN, PERCENT_MAX), between("cleanliness", PERCENT_MIN, PERCENT_MAX))

    people_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    wash_frequency: Mapped[WashFrequency] = mapped_column(enum_type(WashFrequency, "wash_frequency"), default=WashFrequency.WEEKLY)
    wash_place: Mapped[WashPlace] = mapped_column(enum_type(WashPlace, "wash_place"), default=WashPlace.HOME)
    grooming: Mapped[int] = mapped_column(default=40)
    cleanliness: Mapped[int] = mapped_column(default=40)
    waste_handling: Mapped[WasteHandling] = mapped_column(enum_type(WasteHandling, "waste_handling"), default=WasteHandling.PITS)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class HouseworkRow(Base):
    __tablename__ = "housework"
    __table_args__ = (
        between("load", PERCENT_MIN, PERCENT_MAX),
        UniqueConstraint("household_id", "duty", "doer_node_id", name="uq_housework_household_duty_doer"),
        Index("ix_housework_household", "household_id"),
        Index("ix_housework_doer", "doer_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int] = mapped_column(ForeignKey("households.id", ondelete="CASCADE"))
    duty: Mapped[HouseDuty] = mapped_column(enum_type(HouseDuty, "duty"))
    doer_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    doer_role: Mapped[HouseholdRole | None] = mapped_column(enum_type(HouseholdRole, "doer_role"))
    load: Mapped[int] = mapped_column(default=20)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class DomesticServiceRow(Base):
    __tablename__ = "domestic_service"
    __table_args__ = (at_least("wage", 0), at_least("since_epoch", 0), Index("ix_domestic_service_household", "household_id"))

    servant_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    household_id: Mapped[int] = mapped_column(ForeignKey("households.id", ondelete="CASCADE"))
    terms: Mapped[ServiceTerms] = mapped_column(enum_type(ServiceTerms, "terms"), default=ServiceTerms.WAGE)
    wage: Mapped[int] = mapped_column(default=0)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class LeisurePursuitRow(Base):
    __tablename__ = "leisure_pursuits"
    __table_args__ = (
        between("share", PERCENT_MIN, PERCENT_MAX),
        UniqueConstraint("holder_node_id", "kind", name="uq_leisure_pursuits_holder_kind"),
        Index("ix_leisure_pursuits_holder", "holder_node_id"),
        Index("ix_leisure_pursuits_venue", "venue_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    holder_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    kind: Mapped[LeisureKind] = mapped_column(enum_type(LeisureKind, "kind"))
    share: Mapped[int] = mapped_column(default=20)
    venue_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class SpaceNormRow(Base):
    __tablename__ = "space_norms"

    people_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    distance: Mapped[DistanceNorm] = mapped_column(enum_type(DistanceNorm, "distance"), default=DistanceNorm.ARM)
    touch: Mapped[TouchNorm] = mapped_column(enum_type(TouchNorm, "touch"), default=TouchNorm.SPARING)
    posture: Mapped[PostureForm] = mapped_column(enum_type(PostureForm, "posture"), default=PostureForm.STAND)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
