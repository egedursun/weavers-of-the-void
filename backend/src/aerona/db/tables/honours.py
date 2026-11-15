from sqlalchemy import JSON, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.honours import UnitHonourKind, VeteranGrant
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN

NAMED_UNIT_FIELDS = ("name", "nickname", "esprit", "battles", "unit_id", "owner_entity_id", "raised_from_entity_id", "disbanded_epoch")
UNIT_HONOUR_FIELDS = ("kind", "note")
VETERAN_GRANT_FIELDS = ("kind", "veterans", "settlement_entity_id")


class NamedUnitRow(Base):
    __tablename__ = "named_units"
    __table_args__ = (
        between("esprit", PERCENT_MIN, PERCENT_MAX),
        at_least("formed_epoch", 0),
        at_least("battles", 0),
        Index("ix_named_units_owner", "owner_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    unit_id: Mapped[int | None] = mapped_column(ForeignKey("army_units.id", ondelete="SET NULL"), unique=True)
    owner_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))
    nickname: Mapped[str | None] = mapped_column(String(NAME_MAX_LENGTH))
    raised_from_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    esprit: Mapped[int] = mapped_column(default=40)
    battles: Mapped[int] = mapped_column(default=0)
    formed_epoch: Mapped[int] = mapped_column(default=0)
    disbanded_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class UnitHonourRow(Base):
    __tablename__ = "unit_honours"
    __table_args__ = (at_least("epoch", 0), Index("ix_unit_honours_unit", "named_unit_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    named_unit_id: Mapped[int] = mapped_column(ForeignKey("named_units.id", ondelete="CASCADE"))
    kind: Mapped[UnitHonourKind] = mapped_column(enum_type(UnitHonourKind, "kind"))
    note: Mapped[str] = mapped_column(default="")
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class VeteranGrantRow(Base):
    __tablename__ = "veteran_grants"
    __table_args__ = (at_least("veterans", 0), at_least("epoch", 0), Index("ix_veteran_grants_polity", "polity_entity_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    polity_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    kind: Mapped[VeteranGrant] = mapped_column(enum_type(VeteranGrant, "kind"))
    veterans: Mapped[int] = mapped_column(default=0)
    settlement_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    war_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
