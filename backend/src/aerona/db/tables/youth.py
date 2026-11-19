from sqlalchemy import JSON, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.youth import YouthPlace, YouthPurpose

AGE_MAX = 200


class YouthStandingRow(Base):
    __tablename__ = "youth_standing"
    __table_args__ = (
        between("youth_from", 0, AGE_MAX),
        between("youth_to", 0, AGE_MAX),
        between("freedom", PERCENT_MIN, PERCENT_MAX),
        between("duty", PERCENT_MIN, PERCENT_MAX),
    )

    people_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    youth_from: Mapped[int] = mapped_column(default=12)
    youth_to: Mapped[int] = mapped_column(default=20)
    place: Mapped[YouthPlace] = mapped_column(enum_type(YouthPlace, "place"), default=YouthPlace.HOUSEHOLD)
    freedom: Mapped[int] = mapped_column(default=50)
    duty: Mapped[int] = mapped_column(default=50)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class YouthGroupRow(Base):
    __tablename__ = "youth_groups"
    __table_args__ = (between("standing", PERCENT_MIN, PERCENT_MAX), at_least("founded_epoch", 0), Index("ix_youth_groups_settlement", "settlement_entity_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    settlement_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))
    purpose: Mapped[YouthPurpose] = mapped_column(enum_type(YouthPurpose, "purpose"), default=YouthPurpose.SPORT)
    leader_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    standing: Mapped[int] = mapped_column(default=50)
    age_set_id: Mapped[int | None] = mapped_column(ForeignKey("age_sets.id", ondelete="SET NULL"))
    founded_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class YouthGroupMemberRow(Base):
    __tablename__ = "youth_group_members"
    __table_args__ = (at_least("joined_epoch", 0), Index("ix_youth_group_members_member", "member_node_id"))

    group_id: Mapped[int] = mapped_column(ForeignKey("youth_groups.id", ondelete="CASCADE"), primary_key=True)
    member_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    joined_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
