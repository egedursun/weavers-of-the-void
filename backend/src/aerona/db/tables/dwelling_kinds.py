from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import KEY_MAX_LENGTH
from aerona.db.columns import at_least, between, enum_type
from aerona.db.tables.kinds import KindRow
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.urban import HousingLevel


class DwellingKindRow(KindRow):
    __tablename__ = "dwelling_kinds"
    __table_args__ = (
        at_least("rooms", 1),
        between("quality", PERCENT_MIN, PERCENT_MAX),
        at_least("upkeep", 0),
        between("mobile", 0, 1),
        at_least("created_epoch", 0),
        UniqueConstraint("built_in_key", name="uq_dwelling_kinds_built_in_key"),
    )

    derived_from_id: Mapped[int | None] = mapped_column(ForeignKey("dwelling_kinds.id", ondelete="SET NULL"))
    category: Mapped[HousingLevel] = mapped_column(enum_type(HousingLevel, "category"))
    rooms: Mapped[int] = mapped_column(default=1)
    quality: Mapped[int] = mapped_column(default=40)
    upkeep: Mapped[int] = mapped_column(default=1)
    mobile: Mapped[int] = mapped_column(default=0)
    built_in_key: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))
