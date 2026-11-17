from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import KEY_MAX_LENGTH
from aerona.db.columns import at_least, between, enum_type
from aerona.db.tables.kinds import KindRow
from aerona.domain.enums.industry import MethodKind, ProcessKind
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.nature_kinds import OfficeDuty, RealmFunction, TraitFunction


class ProductionMethodKindRow(KindRow):
    __tablename__ = "production_method_kinds"
    __table_args__ = (
        between("output_pct", 0, 500),
        between("quality_bonus", -50, 50),
        between("labour_pct", 0, 500),
        between("energy_need", 0, 100),
        between("tool_wear", 0, 20),
        at_least("created_epoch", 0),
        UniqueConstraint("built_in_key", name="uq_production_method_kinds_built_in_key"),
    )

    derived_from_id: Mapped[int | None] = mapped_column(ForeignKey("production_method_kinds.id", ondelete="SET NULL"))
    category: Mapped[ProcessKind] = mapped_column(enum_type(ProcessKind, "category"))
    base: Mapped[MethodKind | None] = mapped_column(enum_type(MethodKind, "base"))
    output_pct: Mapped[int] = mapped_column(default=100)
    quality_bonus: Mapped[int] = mapped_column(default=0)
    labour_pct: Mapped[int] = mapped_column(default=100)
    energy_need: Mapped[int] = mapped_column(default=1)
    tool_wear: Mapped[int] = mapped_column(default=1)
    built_in_key: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))


class DivineOfficeKindRow(KindRow):
    __tablename__ = "divine_office_kinds"
    __table_args__ = (
        between("income_pct", 0, 500),
        at_least("created_epoch", 0),
        UniqueConstraint("built_in_key", name="uq_divine_office_kinds_built_in_key"),
    )

    derived_from_id: Mapped[int | None] = mapped_column(ForeignKey("divine_office_kinds.id", ondelete="SET NULL"))
    category: Mapped[OfficeDuty] = mapped_column(enum_type(OfficeDuty, "category"))
    income_pct: Mapped[int] = mapped_column(default=100)
    built_in_key: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))


class RealmKindRow(KindRow):
    __tablename__ = "realm_kinds"
    __table_args__ = (
        between("steps", 0, 10),
        between("danger", PERCENT_MIN, PERCENT_MAX),
        at_least("created_epoch", 0),
        UniqueConstraint("built_in_key", name="uq_realm_kinds_built_in_key"),
    )

    derived_from_id: Mapped[int | None] = mapped_column(ForeignKey("realm_kinds.id", ondelete="SET NULL"))
    category: Mapped[RealmFunction] = mapped_column(enum_type(RealmFunction, "category"))
    steps: Mapped[int] = mapped_column(default=0)
    danger: Mapped[int] = mapped_column(default=20)
    built_in_key: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))


class TraitKindRow(KindRow):
    __tablename__ = "trait_kinds"
    __table_args__ = (
        between("strength", -PERCENT_MAX, PERCENT_MAX),
        at_least("created_epoch", 0),
        UniqueConstraint("built_in_key", name="uq_trait_kinds_built_in_key"),
    )

    derived_from_id: Mapped[int | None] = mapped_column(ForeignKey("trait_kinds.id", ondelete="SET NULL"))
    category: Mapped[TraitFunction] = mapped_column(enum_type(TraitFunction, "category"))
    strength: Mapped[int] = mapped_column(default=20)
    built_in_key: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))
