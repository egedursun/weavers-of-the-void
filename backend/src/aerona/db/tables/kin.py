from sqlalchemy import JSON, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.kin import KinDuty, KinGroupForm, KinMembership, KinRole
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN


class KinRoleDutyRow(Base):
    __tablename__ = "kin_role_duties"
    __table_args__ = (between("strength", PERCENT_MIN, PERCENT_MAX),)

    people_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[KinRole] = mapped_column(enum_type(KinRole, "role"), primary_key=True)
    duty: Mapped[KinDuty] = mapped_column(enum_type(KinDuty, "duty"), primary_key=True)
    strength: Mapped[int] = mapped_column(default=50)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class KinGroupRow(Base):
    __tablename__ = "kin_groups"
    __table_args__ = (
        between("exogamy", PERCENT_MIN, PERCENT_MAX),
        at_least("council_size", 0),
        at_least("founded_epoch", 0),
        Index("ix_kin_groups_people", "people_entity_id"),
        Index("ix_kin_groups_head", "head_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    people_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))
    form: Mapped[KinGroupForm] = mapped_column(enum_type(KinGroupForm, "form"), default=KinGroupForm.LINEAGE)
    membership: Mapped[KinMembership] = mapped_column(enum_type(KinMembership, "membership"), default=KinMembership.DESCENT)
    exogamy: Mapped[int] = mapped_column(default=0)
    head_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    land_region_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    shrine_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    council_size: Mapped[int] = mapped_column(default=0)
    house_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    founded_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class KinGroupMemberRow(Base):
    __tablename__ = "kin_group_members"
    __table_args__ = (at_least("joined_epoch", 0), Index("ix_kin_group_members_member", "member_node_id"))

    group_id: Mapped[int] = mapped_column(ForeignKey("kin_groups.id", ondelete="CASCADE"), primary_key=True)
    member_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    adopted: Mapped[bool] = mapped_column(default=False)
    joined_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class WillRow(Base):
    __tablename__ = "wills"
    __table_args__ = (at_least("made_epoch", 0), Index("ix_wills_testator", "testator_node_id", unique=True))

    id: Mapped[int] = mapped_column(primary_key=True)
    testator_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    witnesses: Mapped[list[int]] = mapped_column(JSON, default=list)
    made_epoch: Mapped[int] = mapped_column(default=0)
    forged: Mapped[bool] = mapped_column(default=False)
    read_epoch: Mapped[int | None]
    contested: Mapped[bool] = mapped_column(default=False)
    set_aside: Mapped[bool] = mapped_column(default=False)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class WillHeirRow(Base):
    __tablename__ = "will_heirs"
    __table_args__ = (between("share", 1, PERCENT_MAX), Index("ix_will_heirs_heir", "heir_node_id"))

    will_id: Mapped[int] = mapped_column(ForeignKey("wills.id", ondelete="CASCADE"), primary_key=True)
    heir_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    share: Mapped[int] = mapped_column(default=50)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
