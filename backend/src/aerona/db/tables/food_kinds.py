from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.columns import at_least, between, enum_type
from aerona.db.tables.cuisine import FLAVOURS
from aerona.db.tables.kinds import KindRow
from aerona.domain.enums.cuisine import CookingMethod
from aerona.domain.enums.kinds import DrinkCategory, DrinkRole, GoodCategory, GoodLegality
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN


class DrinkKindRow(KindRow):
    __tablename__ = "drink_kinds"
    __table_args__ = (
        *(between(column, PERCENT_MIN, PERCENT_MAX) for column in ("strength", "stimulation", "nourishment", "water_safety", "prestige", "dependence")),
        at_least("keeps", 0),
        at_least("created_epoch", 0),
    )

    derived_from_id: Mapped[int | None] = mapped_column(ForeignKey("drink_kinds.id", ondelete="SET NULL"))
    category: Mapped[DrinkCategory] = mapped_column(enum_type(DrinkCategory, "category"))
    role: Mapped[DrinkRole] = mapped_column(enum_type(DrinkRole, "role"), default=DrinkRole.DAILY)
    strength: Mapped[int] = mapped_column(default=0)
    stimulation: Mapped[int] = mapped_column(default=0)
    nourishment: Mapped[int] = mapped_column(default=10)
    water_safety: Mapped[int] = mapped_column(default=0)
    keeps: Mapped[int] = mapped_column(default=1)
    prestige: Mapped[int] = mapped_column(default=10)
    dependence: Mapped[int] = mapped_column(default=0)
    legality: Mapped[GoodLegality] = mapped_column(enum_type(GoodLegality, "legality"), default=GoodLegality.FREE)


class CuisineRow(KindRow):
    __tablename__ = "cuisines"
    __table_args__ = (
        *(between(column, PERCENT_MIN, PERCENT_MAX) for column in ("etiquette", "feasting", *FLAVOURS)),
        between("meals_per_day", 1, 8),
        at_least("created_epoch", 0),
    )

    derived_from_id: Mapped[int | None] = mapped_column(ForeignKey("cuisines.id", ondelete="SET NULL"))
    category: Mapped[GoodCategory] = mapped_column(enum_type(GoodCategory, "category"))
    signature_method: Mapped[CookingMethod] = mapped_column(enum_type(CookingMethod, "signature_method"), default=CookingMethod.BOILED)
    taboo_category: Mapped[GoodCategory | None] = mapped_column(enum_type(GoodCategory, "taboo_category"))
    etiquette: Mapped[int] = mapped_column(default=30)
    meals_per_day: Mapped[int] = mapped_column(default=2)
    feasting: Mapped[int] = mapped_column(default=20)
    sweet: Mapped[int] = mapped_column(default=0)
    sour: Mapped[int] = mapped_column(default=0)
    saline: Mapped[int] = mapped_column(default=0)
    bitter: Mapped[int] = mapped_column(default=0)
    savoury: Mapped[int] = mapped_column(default=0)
    pungent: Mapped[int] = mapped_column(default=0)
    cooling: Mapped[int] = mapped_column(default=0)
    numbing: Mapped[int] = mapped_column(default=0)
    smoky: Mapped[int] = mapped_column(default=0)
    fermented: Mapped[int] = mapped_column(default=0)
    astringent: Mapped[int] = mapped_column(default=0, server_default="0")
    rich: Mapped[int] = mapped_column(default=0, server_default="0")
