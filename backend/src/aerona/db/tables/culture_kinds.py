from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import KEY_MAX_LENGTH
from aerona.db.columns import at_least, between, enum_type
from aerona.db.tables.kinds import KindRow
from aerona.domain.enums.culture_kinds import TenetScope
from aerona.domain.enums.mind import DreamReading, Facet, FearKind, LifeGoal, NeedKind, ValueAxis


class TenetKindRow(KindRow):
    __tablename__ = "tenet_kinds"
    __table_args__ = (
        between("value_delta", -50, 50),
        between("second_delta", -50, 50),
        at_least("created_epoch", 0),
        UniqueConstraint("built_in_key", name="uq_tenet_kinds_built_in_key"),
    )

    derived_from_id: Mapped[int | None] = mapped_column(ForeignKey("tenet_kinds.id", ondelete="SET NULL"))
    category: Mapped[TenetScope] = mapped_column(enum_type(TenetScope, "category"))
    value_axis: Mapped[ValueAxis | None] = mapped_column(enum_type(ValueAxis, "value_axis"))
    value_delta: Mapped[int] = mapped_column(default=0)
    second_axis: Mapped[ValueAxis | None] = mapped_column(enum_type(ValueAxis, "second_axis"))
    second_delta: Mapped[int] = mapped_column(default=0)
    built_in_key: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))


class FearKindRow(KindRow):
    __tablename__ = "fear_kinds"
    __table_args__ = (
        between("grip", 0, 100),
        between("facet_weight", 0, 100),
        at_least("created_epoch", 0),
        UniqueConstraint("built_in_key", name="uq_fear_kinds_built_in_key"),
    )

    derived_from_id: Mapped[int | None] = mapped_column(ForeignKey("fear_kinds.id", ondelete="SET NULL"))
    category: Mapped[FearKind] = mapped_column(enum_type(FearKind, "category"))
    grip: Mapped[int] = mapped_column(default=50)
    facet: Mapped[Facet | None] = mapped_column(enum_type(Facet, "facet"))
    facet_weight: Mapped[int] = mapped_column(default=30)
    built_in_key: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))


class ReadingKindRow(KindRow):
    __tablename__ = "reading_kinds"
    __table_args__ = (
        between("valence", -100, 100),
        between("lean", -20, 20),
        at_least("created_epoch", 0),
        UniqueConstraint("built_in_key", name="uq_reading_kinds_built_in_key"),
    )

    derived_from_id: Mapped[int | None] = mapped_column(ForeignKey("reading_kinds.id", ondelete="SET NULL"))
    category: Mapped[DreamReading] = mapped_column(enum_type(DreamReading, "category"))
    valence: Mapped[int] = mapped_column(default=0)
    value_axis: Mapped[ValueAxis | None] = mapped_column(enum_type(ValueAxis, "value_axis"))
    lean: Mapped[int] = mapped_column(default=0)
    built_in_key: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))


class AimKindRow(KindRow):
    __tablename__ = "aim_kinds"
    __table_args__ = (
        between("pull", 0, 100),
        between("value_weight", -100, 100),
        at_least("created_epoch", 0),
        UniqueConstraint("built_in_key", name="uq_aim_kinds_built_in_key"),
    )

    derived_from_id: Mapped[int | None] = mapped_column(ForeignKey("aim_kinds.id", ondelete="SET NULL"))
    category: Mapped[LifeGoal] = mapped_column(enum_type(LifeGoal, "category"))
    need: Mapped[NeedKind | None] = mapped_column(enum_type(NeedKind, "need"))
    pull: Mapped[int] = mapped_column(default=30)
    value_axis: Mapped[ValueAxis | None] = mapped_column(enum_type(ValueAxis, "value_axis"))
    value_weight: Mapped[int] = mapped_column(default=0)
    built_in_key: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))
